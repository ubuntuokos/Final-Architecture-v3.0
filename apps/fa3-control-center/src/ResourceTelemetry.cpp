#include "ResourceTelemetry.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QStringList>
#include <QtGlobal>

#include <algorithm>

#ifdef Q_OS_WIN
#define NOMINMAX
#include <windows.h>
#endif

namespace {
constexpr double KiBPerGiB = 1024.0 * 1024.0;
constexpr double BytesPerGiB = 1024.0 * 1024.0 * 1024.0;

bool readDoubleFile(const QString &path, double &value)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return false;
    }
    bool ok = false;
    const double parsed = QString::fromUtf8(file.readAll()).trimmed().toDouble(&ok);
    if (ok) {
        value = parsed;
    }
    return ok;
}

QString readTextFile(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return {};
    }
    return QString::fromUtf8(file.readAll()).trimmed();
}

QString vendorLabel(const QString &vendor)
{
    const QString normalized = vendor.trimmed().toLower();
    if (normalized == QStringLiteral("0x10de")) return QStringLiteral("NVIDIA GPU");
    if (normalized == QStringLiteral("0x1002")) return QStringLiteral("AMD GPU");
    if (normalized == QStringLiteral("0x8086")) return QStringLiteral("Intel GPU");
    return QStringLiteral("GPU");
}

#ifdef Q_OS_WIN
quint64 fileTimeToUInt64(const FILETIME &fileTime)
{
    ULARGE_INTEGER value;
    value.LowPart = fileTime.dwLowDateTime;
    value.HighPart = fileTime.dwHighDateTime;
    return value.QuadPart;
}
#endif
} // namespace

ResourceTelemetry::ResourceTelemetry(QObject *parent)
    : QObject(parent)
{
    m_fastTimer.setInterval(1000);
    m_acceleratorTimer.setInterval(5000);

    connect(&m_fastTimer, &QTimer::timeout, this, &ResourceTelemetry::sampleFast);
    connect(&m_acceleratorTimer, &QTimer::timeout, this, &ResourceTelemetry::sampleAccelerators);
    connect(&m_gpuProbe, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, &ResourceTelemetry::handleGpuProbeFinished);
    connect(&m_gpuProbe, &QProcess::errorOccurred,
            this, &ResourceTelemetry::handleGpuProbeError);

    sampleFast();
    sampleAccelerators();
    m_fastTimer.start();
    m_acceleratorTimer.start();
}

void ResourceTelemetry::refreshNow()
{
    m_nvidiaProbeDisabled = false;
    sampleFast();
    sampleAccelerators();
}

void ResourceTelemetry::sampleFast()
{
    sampleCpu();
    sampleMemory();
    updatePressure();
    emit telemetryChanged();
}

void ResourceTelemetry::sampleAccelerators()
{
#ifdef Q_OS_LINUX
    sampleLinuxNpu();
#endif

    if (!m_nvidiaProbeDisabled && m_gpuProbe.state() == QProcess::NotRunning) {
#ifdef Q_OS_WIN
        const QString program = QStringLiteral("nvidia-smi.exe");
#else
        const QString program = QStringLiteral("nvidia-smi");
#endif
        const QStringList arguments = {
            QStringLiteral("--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu"),
            QStringLiteral("--format=csv,noheader,nounits")
        };
        m_gpuProbe.start(program, arguments, QIODevice::ReadOnly);
    } else if (m_nvidiaProbeDisabled) {
#ifdef Q_OS_LINUX
        sampleLinuxGpuFallback();
#endif
        updatePressure();
        emit telemetryChanged();
    }
}

void ResourceTelemetry::sampleCpu()
{
#ifdef Q_OS_WIN
    FILETIME idleTime{};
    FILETIME kernelTime{};
    FILETIME userTime{};
    if (!GetSystemTimes(&idleTime, &kernelTime, &userTime)) {
        m_cpuPercent = -1.0;
        return;
    }

    const quint64 idle = fileTimeToUInt64(idleTime);
    const quint64 total = fileTimeToUInt64(kernelTime) + fileTimeToUInt64(userTime);
#else
    QFile file(QStringLiteral("/proc/stat"));
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        m_cpuPercent = -1.0;
        return;
    }
    const QList<QByteArray> parts = file.readLine().simplified().split(' ');
    if (parts.size() < 5 || parts.first() != "cpu") {
        m_cpuPercent = -1.0;
        return;
    }

    quint64 total = 0;
    QList<quint64> values;
    for (qsizetype i = 1; i < parts.size(); ++i) {
        bool ok = false;
        const quint64 value = parts.at(i).toULongLong(&ok);
        if (!ok) continue;
        values.append(value);
        total += value;
    }
    if (values.size() < 4) {
        m_cpuPercent = -1.0;
        return;
    }
    const quint64 idle = values.at(3) + (values.size() > 4 ? values.at(4) : 0);
#endif

    if (m_previousCpuTotal > 0 && total > m_previousCpuTotal) {
        const quint64 totalDelta = total - m_previousCpuTotal;
        const quint64 idleDelta = idle >= m_previousCpuIdle ? idle - m_previousCpuIdle : 0;
        const double busy = 100.0 * static_cast<double>(totalDelta - std::min(totalDelta, idleDelta))
                            / static_cast<double>(totalDelta);
        m_cpuPercent = std::clamp(busy, 0.0, 100.0);
    }
    m_previousCpuTotal = total;
    m_previousCpuIdle = idle;
}

void ResourceTelemetry::sampleMemory()
{
#ifdef Q_OS_WIN
    MEMORYSTATUSEX state{};
    state.dwLength = sizeof(state);
    if (!GlobalMemoryStatusEx(&state)) {
        m_ramPercent = -1.0;
        m_ramUsedGiB = -1.0;
        m_ramTotalGiB = -1.0;
        return;
    }
    m_ramTotalGiB = static_cast<double>(state.ullTotalPhys) / BytesPerGiB;
    m_ramUsedGiB = static_cast<double>(state.ullTotalPhys - state.ullAvailPhys) / BytesPerGiB;
    m_ramPercent = static_cast<double>(state.dwMemoryLoad);
#else
    QFile file(QStringLiteral("/proc/meminfo"));
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        m_ramPercent = -1.0;
        m_ramUsedGiB = -1.0;
        m_ramTotalGiB = -1.0;
        return;
    }

    quint64 totalKiB = 0;
    quint64 availableKiB = 0;
    quint64 freeKiB = 0;
    quint64 buffersKiB = 0;
    quint64 cachedKiB = 0;
    while (!file.atEnd()) {
        const QList<QByteArray> fields = file.readLine().simplified().split(' ');
        if (fields.size() < 2) continue;
        const QByteArray key = fields.at(0);
        bool ok = false;
        const quint64 value = fields.at(1).toULongLong(&ok);
        if (!ok) continue;
        if (key == "MemTotal:") totalKiB = value;
        else if (key == "MemAvailable:") availableKiB = value;
        else if (key == "MemFree:") freeKiB = value;
        else if (key == "Buffers:") buffersKiB = value;
        else if (key == "Cached:") cachedKiB = value;
    }
    if (totalKiB == 0) {
        m_ramPercent = -1.0;
        m_ramUsedGiB = -1.0;
        m_ramTotalGiB = -1.0;
        return;
    }
    if (availableKiB == 0) {
        availableKiB = freeKiB + buffersKiB + cachedKiB;
    }
    availableKiB = std::min(availableKiB, totalKiB);
    const quint64 usedKiB = totalKiB - availableKiB;
    m_ramTotalGiB = static_cast<double>(totalKiB) / KiBPerGiB;
    m_ramUsedGiB = static_cast<double>(usedKiB) / KiBPerGiB;
    m_ramPercent = 100.0 * static_cast<double>(usedKiB) / static_cast<double>(totalKiB);
#endif
}

void ResourceTelemetry::handleGpuProbeFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    if (exitStatus != QProcess::NormalExit || exitCode != 0) {
        m_nvidiaProbeDisabled = true;
#ifdef Q_OS_LINUX
        sampleLinuxGpuFallback();
#else
        clearGpu();
#endif
        updatePressure();
        emit telemetryChanged();
        return;
    }

    const QString output = QString::fromUtf8(m_gpuProbe.readAllStandardOutput()).trimmed();
    const QStringList lines = output.split('\n', Qt::SkipEmptyParts);
    if (lines.isEmpty()) {
        m_nvidiaProbeDisabled = true;
#ifdef Q_OS_LINUX
        sampleLinuxGpuFallback();
#else
        clearGpu();
#endif
        updatePressure();
        emit telemetryChanged();
        return;
    }

    double maxLoad = -1.0;
    double totalMemoryMiB = 0.0;
    double usedMemoryMiB = 0.0;
    double maxTemperature = -1.0;
    QString firstName;
    int parsedCount = 0;

    for (const QString &line : lines) {
        const QStringList fields = line.split(',');
        if (fields.size() < 5) continue;
        bool loadOk = false;
        bool usedOk = false;
        bool totalOk = false;
        bool tempOk = false;
        const double load = fields.at(1).trimmed().toDouble(&loadOk);
        const double used = fields.at(2).trimmed().toDouble(&usedOk);
        const double total = fields.at(3).trimmed().toDouble(&totalOk);
        const double temp = fields.at(4).trimmed().toDouble(&tempOk);
        if (firstName.isEmpty()) firstName = fields.at(0).trimmed();
        if (loadOk) maxLoad = std::max(maxLoad, load);
        if (usedOk) usedMemoryMiB += used;
        if (totalOk) totalMemoryMiB += total;
        if (tempOk) maxTemperature = std::max(maxTemperature, temp);
        ++parsedCount;
    }

    if (parsedCount == 0) {
        m_nvidiaProbeDisabled = true;
#ifdef Q_OS_LINUX
        sampleLinuxGpuFallback();
#else
        clearGpu();
#endif
    } else {
        m_gpuAvailable = true;
        m_gpuLabel = parsedCount > 1
            ? QStringLiteral("%1 (+%2)").arg(firstName).arg(parsedCount - 1)
            : firstName;
        m_gpuPercent = maxLoad;
        m_gpuMemoryUsedGiB = usedMemoryMiB >= 0.0 ? usedMemoryMiB / 1024.0 : -1.0;
        m_gpuMemoryTotalGiB = totalMemoryMiB > 0.0 ? totalMemoryMiB / 1024.0 : -1.0;
        m_gpuTemperatureC = maxTemperature;
    }
    updatePressure();
    emit telemetryChanged();
}

void ResourceTelemetry::handleGpuProbeError(QProcess::ProcessError error)
{
    if (error != QProcess::FailedToStart) {
        return;
    }
    m_nvidiaProbeDisabled = true;
#ifdef Q_OS_LINUX
    sampleLinuxGpuFallback();
#else
    clearGpu();
#endif
    updatePressure();
    emit telemetryChanged();
}

void ResourceTelemetry::sampleLinuxGpuFallback()
{
#ifdef Q_OS_LINUX
    QDir drm(QStringLiteral("/sys/class/drm"));
    const QStringList entries = drm.entryList(QStringList() << QStringLiteral("card*"), QDir::Dirs | QDir::NoDotAndDotDot);

    bool found = false;
    double maxLoad = -1.0;
    double totalVramBytes = 0.0;
    double usedVramBytes = 0.0;
    double maxTemperature = -1.0;
    QString firstLabel;
    int count = 0;

    for (const QString &entry : entries) {
        if (entry.contains('-')) continue;
        const QString deviceRoot = drm.filePath(entry + QStringLiteral("/device"));
        if (!QFileInfo::exists(deviceRoot)) continue;

        const QString vendor = readTextFile(deviceRoot + QStringLiteral("/vendor"));
        const QString label = vendorLabel(vendor);
        if (vendor.isEmpty() && !QFileInfo::exists(deviceRoot + QStringLiteral("/gpu_busy_percent"))) continue;

        found = true;
        ++count;
        if (firstLabel.isEmpty()) firstLabel = label;

        double value = -1.0;
        if (readDoubleFile(deviceRoot + QStringLiteral("/gpu_busy_percent"), value)
            || readDoubleFile(deviceRoot + QStringLiteral("/busy_percent"), value)
            || readDoubleFile(deviceRoot + QStringLiteral("/utilization"), value)) {
            maxLoad = std::max(maxLoad, value);
        }

        double used = 0.0;
        double total = 0.0;
        if (readDoubleFile(deviceRoot + QStringLiteral("/mem_info_vram_used"), used)) usedVramBytes += used;
        if (readDoubleFile(deviceRoot + QStringLiteral("/mem_info_vram_total"), total)) totalVramBytes += total;

        QDir hwmon(deviceRoot + QStringLiteral("/hwmon"));
        const QStringList hwmonDirs = hwmon.entryList(QStringList() << QStringLiteral("hwmon*"), QDir::Dirs | QDir::NoDotAndDotDot);
        for (const QString &hwmonDir : hwmonDirs) {
            double milliC = 0.0;
            if (readDoubleFile(hwmon.filePath(hwmonDir + QStringLiteral("/temp1_input")), milliC)) {
                maxTemperature = std::max(maxTemperature, milliC / 1000.0);
                break;
            }
        }
    }

    if (!found) {
        clearGpu();
        return;
    }

    m_gpuAvailable = true;
    m_gpuLabel = count > 1 ? QStringLiteral("%1 (+%2)").arg(firstLabel).arg(count - 1) : firstLabel;
    m_gpuPercent = maxLoad;
    m_gpuMemoryUsedGiB = usedVramBytes > 0.0 ? usedVramBytes / BytesPerGiB : -1.0;
    m_gpuMemoryTotalGiB = totalVramBytes > 0.0 ? totalVramBytes / BytesPerGiB : -1.0;
    m_gpuTemperatureC = maxTemperature;
#endif
}

void ResourceTelemetry::sampleLinuxNpu()
{
#ifdef Q_OS_LINUX
    QDir accelClass(QStringLiteral("/sys/class/accel"));
    QStringList entries;
    if (accelClass.exists()) {
        entries = accelClass.entryList(QStringList() << QStringLiteral("accel*"), QDir::Dirs | QDir::NoDotAndDotDot);
    }
    if (entries.isEmpty()) {
        QDir accelDev(QStringLiteral("/dev/accel"));
        if (accelDev.exists()) {
            entries = accelDev.entryList(QStringList() << QStringLiteral("accel*"), QDir::System | QDir::Files | QDir::NoDotAndDotDot);
        }
    }

    if (entries.isEmpty()) {
        m_npuAvailable = false;
        m_npuLabel = QStringLiteral("NPU");
        m_npuPercent = -1.0;
        return;
    }

    m_npuAvailable = true;
    m_npuLabel = entries.size() > 1 ? QStringLiteral("NPU (+%1)").arg(entries.size() - 1) : QStringLiteral("NPU");
    m_npuPercent = -1.0;

    for (const QString &entry : entries) {
        const QString deviceRoot = accelClass.filePath(entry + QStringLiteral("/device"));
        double value = -1.0;
        if (readDoubleFile(deviceRoot + QStringLiteral("/busy_percent"), value)
            || readDoubleFile(deviceRoot + QStringLiteral("/npu_busy_percent"), value)
            || readDoubleFile(deviceRoot + QStringLiteral("/utilization"), value)) {
            m_npuPercent = std::max(m_npuPercent, value);
        }
    }
#endif
}

void ResourceTelemetry::updatePressure()
{
    int severity = 0;
    QStringList reasons;
    const auto assess = [&](const QString &name, double value, double warning, double critical) {
        if (value < 0.0) return;
        if (value >= critical) {
            severity = std::max(severity, 2);
            reasons.append(QStringLiteral("%1 %2%").arg(name).arg(qRound(value)));
        } else if (value >= warning) {
            severity = std::max(severity, 1);
            reasons.append(QStringLiteral("%1 %2%").arg(name).arg(qRound(value)));
        }
    };

    assess(QStringLiteral("CPU"), m_cpuPercent, 90.0, 98.0);
    assess(QStringLiteral("RAM"), m_ramPercent, 85.0, 95.0);
    assess(QStringLiteral("GPU"), m_gpuPercent, 92.0, 98.0);
    assess(QStringLiteral("NPU"), m_npuPercent, 92.0, 98.0);

    if (severity >= 2) {
        m_pressureState = QStringLiteral("CRITICAL");
    } else if (severity == 1) {
        m_pressureState = QStringLiteral("WARN");
    } else {
        m_pressureState = QStringLiteral("NORMAL");
    }
    m_pressureSummary = reasons.isEmpty()
        ? QStringLiteral("No measured resource pressure")
        : reasons.join(QStringLiteral(" · "));
}

void ResourceTelemetry::clearGpu()
{
    m_gpuAvailable = false;
    m_gpuLabel = QStringLiteral("GPU");
    m_gpuPercent = -1.0;
    m_gpuMemoryUsedGiB = -1.0;
    m_gpuMemoryTotalGiB = -1.0;
    m_gpuTemperatureC = -1.0;
}
