#include "ResourceTelemetry.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QStringList>
#include <algorithm>

namespace {
constexpr double KiBPerGiB = 1024.0 * 1024.0;
constexpr double BytesPerGiB = 1024.0 * 1024.0 * 1024.0;

bool readDoubleFile(const QString &path, double &value)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) return false;
    bool ok = false;
    const double parsed = QString::fromUtf8(f.readAll()).trimmed().toDouble(&ok);
    if (ok) value = parsed;
    return ok;
}

QString readTextFile(const QString &path)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) return {};
    return QString::fromUtf8(f.readAll()).trimmed();
}
}

ResourceTelemetry::ResourceTelemetry(QObject *parent) : QObject(parent)
{
    m_fastTimer.setInterval(1000);
    m_acceleratorTimer.setInterval(5000);
    connect(&m_fastTimer, &QTimer::timeout, this, &ResourceTelemetry::sampleFast);
    connect(&m_acceleratorTimer, &QTimer::timeout, this, &ResourceTelemetry::sampleAccelerators);
    connect(&m_gpuProbe, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this, &ResourceTelemetry::handleGpuProbeFinished);
    connect(&m_gpuProbe, &QProcess::errorOccurred, this, &ResourceTelemetry::handleGpuProbeError);
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
    sampleLinuxNpu();
    if (!m_nvidiaProbeDisabled && m_gpuProbe.state() == QProcess::NotRunning) {
        const QStringList args = {
            QStringLiteral("--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu"),
            QStringLiteral("--format=csv,noheader,nounits")
        };
        m_gpuProbe.start(QStringLiteral("nvidia-smi"), args, QIODevice::ReadOnly);
    } else if (m_nvidiaProbeDisabled) {
        sampleLinuxGpuFallback();
        updatePressure();
        emit telemetryChanged();
    }
}

void ResourceTelemetry::sampleCpu()
{
    QFile file(QStringLiteral("/proc/stat"));
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) { m_cpuPercent = -1.0; return; }
    const auto parts = file.readLine().simplified().split(' ');
    if (parts.size() < 5 || parts.first() != "cpu") { m_cpuPercent = -1.0; return; }
    quint64 total = 0;
    QList<quint64> values;
    for (qsizetype i = 1; i < parts.size(); ++i) {
        bool ok = false;
        const quint64 v = parts.at(i).toULongLong(&ok);
        if (ok) { values.append(v); total += v; }
    }
    if (values.size() < 4) { m_cpuPercent = -1.0; return; }
    const quint64 idle = values.at(3) + (values.size() > 4 ? values.at(4) : 0);
    if (m_previousCpuTotal > 0 && total > m_previousCpuTotal) {
        const quint64 td = total - m_previousCpuTotal;
        const quint64 id = idle >= m_previousCpuIdle ? idle - m_previousCpuIdle : 0;
        m_cpuPercent = std::clamp(100.0 * double(td - std::min(td, id)) / double(td), 0.0, 100.0);
    }
    m_previousCpuTotal = total;
    m_previousCpuIdle = idle;
}

void ResourceTelemetry::sampleMemory()
{
    QFile file(QStringLiteral("/proc/meminfo"));
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) { m_ramPercent = m_ramUsedGiB = m_ramTotalGiB = -1.0; return; }
    quint64 total = 0, available = 0;
    while (!file.atEnd()) {
        const auto p = file.readLine().simplified().split(' ');
        if (p.size() < 2) continue;
        bool ok = false;
        const quint64 v = p.at(1).toULongLong(&ok);
        if (!ok) continue;
        if (p.at(0) == "MemTotal:") total = v;
        else if (p.at(0) == "MemAvailable:") available = v;
    }
    if (!total) { m_ramPercent = m_ramUsedGiB = m_ramTotalGiB = -1.0; return; }
    available = std::min(available, total);
    const quint64 used = total - available;
    m_ramTotalGiB = double(total) / KiBPerGiB;
    m_ramUsedGiB = double(used) / KiBPerGiB;
    m_ramPercent = 100.0 * double(used) / double(total);
}

void ResourceTelemetry::handleGpuProbeFinished(int exitCode, QProcess::ExitStatus status)
{
    if (status != QProcess::NormalExit || exitCode != 0) {
        m_nvidiaProbeDisabled = true;
        sampleLinuxGpuFallback();
        updatePressure(); emit telemetryChanged(); return;
    }
    const auto lines = QString::fromUtf8(m_gpuProbe.readAllStandardOutput()).trimmed().split('\n', Qt::SkipEmptyParts);
    double maxLoad = -1.0, used = 0.0, total = 0.0, maxTemp = -1.0;
    QString firstName; int count = 0;
    for (const auto &line : lines) {
        const auto f = line.split(',');
        if (f.size() < 5) continue;
        bool ok1=false, ok2=false, ok3=false, ok4=false;
        const double load=f.at(1).trimmed().toDouble(&ok1), u=f.at(2).trimmed().toDouble(&ok2), t=f.at(3).trimmed().toDouble(&ok3), temp=f.at(4).trimmed().toDouble(&ok4);
        if (firstName.isEmpty()) firstName=f.at(0).trimmed();
        if (ok1) maxLoad=std::max(maxLoad,load); if(ok2) used+=u; if(ok3) total+=t; if(ok4) maxTemp=std::max(maxTemp,temp); ++count;
    }
    if (!count) { m_nvidiaProbeDisabled = true; sampleLinuxGpuFallback(); }
    else {
        m_gpuAvailable=true; m_gpuLabel=count>1 ? QStringLiteral("%1 (+%2)").arg(firstName).arg(count-1) : firstName;
        m_gpuPercent=maxLoad; m_gpuMemoryUsedGiB=used/1024.0; m_gpuMemoryTotalGiB=total>0?total/1024.0:-1.0; m_gpuTemperatureC=maxTemp;
    }
    updatePressure(); emit telemetryChanged();
}

void ResourceTelemetry::handleGpuProbeError(QProcess::ProcessError error)
{
    if (error != QProcess::FailedToStart) return;
    m_nvidiaProbeDisabled = true;
    sampleLinuxGpuFallback(); updatePressure(); emit telemetryChanged();
}

void ResourceTelemetry::sampleLinuxGpuFallback()
{
    QDir drm(QStringLiteral("/sys/class/drm"));
    const auto entries = drm.entryList({QStringLiteral("card*")}, QDir::Dirs | QDir::NoDotAndDotDot);
    bool found=false; double maxLoad=-1.0, usedBytes=0.0, totalBytes=0.0, maxTemp=-1.0; int count=0;
    for (const auto &entry : entries) {
        if (entry.contains('-')) continue;
        const QString root=drm.filePath(entry+QStringLiteral("/device"));
        if (!QFileInfo::exists(root)) continue;
        const QString vendor=readTextFile(root+QStringLiteral("/vendor"));
        if (vendor.isEmpty()) continue;
        found=true; ++count; double v=-1.0;
        if (readDoubleFile(root+QStringLiteral("/gpu_busy_percent"),v) || readDoubleFile(root+QStringLiteral("/busy_percent"),v)) maxLoad=std::max(maxLoad,v);
        double x=0.0; if(readDoubleFile(root+QStringLiteral("/mem_info_vram_used"),x)) usedBytes+=x; if(readDoubleFile(root+QStringLiteral("/mem_info_vram_total"),x)) totalBytes+=x;
        QDir hw(root+QStringLiteral("/hwmon"));
        for (const auto &d : hw.entryList({QStringLiteral("hwmon*")},QDir::Dirs|QDir::NoDotAndDotDot)) { double mc=0; if(readDoubleFile(hw.filePath(d+QStringLiteral("/temp1_input")),mc)){maxTemp=std::max(maxTemp,mc/1000.0);break;} }
    }
    if (!found) { clearGpu(); return; }
    m_gpuAvailable=true; m_gpuLabel=count>1?QStringLiteral("GPU (+%1)").arg(count-1):QStringLiteral("GPU"); m_gpuPercent=maxLoad;
    m_gpuMemoryUsedGiB=usedBytes>0?usedBytes/BytesPerGiB:-1.0; m_gpuMemoryTotalGiB=totalBytes>0?totalBytes/BytesPerGiB:-1.0; m_gpuTemperatureC=maxTemp;
}

void ResourceTelemetry::sampleLinuxNpu()
{
    QDir accel(QStringLiteral("/sys/class/accel"));
    const auto entries=accel.exists()?accel.entryList({QStringLiteral("accel*")},QDir::Dirs|QDir::NoDotAndDotDot):QStringList{};
    m_npuAvailable=!entries.isEmpty(); m_npuLabel=entries.size()>1?QStringLiteral("NPU (+%1)").arg(entries.size()-1):QStringLiteral("NPU"); m_npuPercent=-1.0;
    for(const auto &e:entries){ double v=-1.0; const QString root=accel.filePath(e+QStringLiteral("/device")); if(readDoubleFile(root+QStringLiteral("/busy_percent"),v)||readDoubleFile(root+QStringLiteral("/utilization"),v)){m_npuPercent=std::max(m_npuPercent,v);} }
}

void ResourceTelemetry::updatePressure()
{
    const double maxMeasured=std::max({m_cpuPercent,m_ramPercent,m_gpuPercent});
    if (maxMeasured >= 95.0 || m_gpuTemperatureC >= 88.0) { m_pressureState="CRITICAL"; m_pressureSummary="Measured host pressure is critical"; }
    else if (maxMeasured >= 80.0 || m_gpuTemperatureC >= 80.0) { m_pressureState="WARN"; m_pressureSummary="Measured host pressure is elevated"; }
    else { m_pressureState="NORMAL"; m_pressureSummary="No measured resource pressure"; }
}

void ResourceTelemetry::clearGpu()
{
    m_gpuAvailable=false; m_gpuLabel="GPU"; m_gpuPercent=m_gpuMemoryUsedGiB=m_gpuMemoryTotalGiB=m_gpuTemperatureC=-1.0;
}
