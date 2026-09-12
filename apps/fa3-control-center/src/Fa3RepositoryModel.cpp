#include "Fa3RepositoryModel.h"

#include <QCoreApplication>
#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QSet>
#include <QStandardPaths>
#include <QStorageInfo>
#include <QSysInfo>
#include <QThread>
#include <QUrl>

namespace {
QString readTrimmed(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return {};
    return QString::fromUtf8(file.readAll()).trimmed();
}

QVariantMap parseColonFile(const QString &path)
{
    QVariantMap result;
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return result;
    while (!file.atEnd()) {
        const QString line = QString::fromUtf8(file.readLine()).trimmed();
        const qsizetype sep = line.indexOf(':');
        if (sep <= 0) continue;
        result.insert(line.left(sep).trimmed(), line.mid(sep + 1).trimmed());
    }
    return result;
}

double memInfoGiB(const QString &key)
{
    QFile file("/proc/meminfo");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return 0.0;
    while (!file.atEnd()) {
        const QString line = QString::fromUtf8(file.readLine());
        if (!line.startsWith(key + ':')) continue;
        const QStringList parts = line.simplified().split(' ');
        if (parts.size() < 2) return 0.0;
        bool ok = false;
        const double kib = parts.at(1).toDouble(&ok);
        return ok ? kib / 1024.0 / 1024.0 : 0.0;
    }
    return 0.0;
}
}

Fa3RepositoryModel::Fa3RepositoryModel(QObject *parent)
    : QObject(parent), m_repoRoot(discoverRepositoryRoot())
{
    refresh();
}

QString Fa3RepositoryModel::discoverRepositoryRoot() const
{
    const auto envRoot = qEnvironmentVariable("FA3_REPO_ROOT");
    if (!envRoot.isEmpty() && QFileInfo::exists(envRoot + "/canonical")) return QDir(envRoot).absolutePath();

    const QStringList candidates = {QDir::currentPath(), QCoreApplication::applicationDirPath()};
    for (const auto &candidate : candidates) {
        QDir dir(candidate);
        for (int depth = 0; depth < 8; ++depth) {
            if (dir.exists("canonical") && dir.exists("tests") && QFileInfo::exists(dir.filePath("README.md"))) return dir.absolutePath();
            if (!dir.cdUp()) break;
        }
    }
    return QDir::currentPath();
}

QVariantMap Fa3RepositoryModel::recordFromJson(const QString &absolutePath, const QString &relativePath) const
{
    QVariantMap out;
    QFile file(absolutePath);
    if (!file.open(QIODevice::ReadOnly)) return out;

    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) return out;

    const auto object = document.object();
    const auto id = object.value("id").toString(QFileInfo(relativePath).baseName());
    QString title = object.value("name").toString();
    if (title.isEmpty()) title = object.value("subject").toString();
    if (title.isEmpty()) title = id;

    QString category = "canonical";
    if (relativePath.startsWith("profiles/")) category = "profile";
    else if (relativePath.startsWith("providers/")) category = "provider";
    else if (relativePath.startsWith("decisions/")) category = "decision";
    else if (relativePath.startsWith("contracts/")) category = "contract";
    else if (id.contains("GATE")) category = "gate";
    else if (id.contains("RUNTIME-CONFORMANCE")) category = "runtime";

    out.insert("id", id);
    out.insert("title", title);
    out.insert("status", object.value("status").toString("UNKNOWN"));
    out.insert("schema", object.value("schema").toString());
    out.insert("category", category);
    out.insert("path", QString("canonical/%1").arg(relativePath));
    return out;
}

void Fa3RepositoryModel::scanCanonical()
{
    m_records.clear();
    m_canonicalRecordCount = m_profileCount = m_providerCount = m_decisionCount = m_pendingCount = 0;
    const QDir canonicalDir(m_repoRoot + "/canonical");
    if (!canonicalDir.exists()) return;

    QDirIterator it(canonicalDir.absolutePath(), {"*.json"}, QDir::Files, QDirIterator::Subdirectories);
    while (it.hasNext()) {
        const auto path = it.next();
        const auto rel = canonicalDir.relativeFilePath(path);
        const auto record = recordFromJson(path, rel);
        if (record.isEmpty()) continue;
        ++m_canonicalRecordCount;
        const auto category = record.value("category").toString();
        if (category == "profile") ++m_profileCount;
        if (category == "provider") ++m_providerCount;
        if (category == "decision") ++m_decisionCount;
        if (record.value("status").toString().contains("PENDING", Qt::CaseInsensitive)) ++m_pendingCount;
        m_records.append(record);
    }
}

void Fa3RepositoryModel::scanEvidence()
{
    m_evidenceCount = 0;
    const QDir evidenceDir(m_repoRoot + "/evidence");
    if (!evidenceDir.exists()) return;
    QDirIterator it(evidenceDir.absolutePath(), {"*.json"}, QDir::Files, QDirIterator::Subdirectories);
    while (it.hasNext()) { it.next(); ++m_evidenceCount; }
}

void Fa3RepositoryModel::refresh()
{
    const auto discovered = discoverRepositoryRoot();
    if (discovered != m_repoRoot) { m_repoRoot = discovered; emit repoRootChanged(); }
    scanCanonical();
    scanEvidence();
    m_lastRefresh = QDateTime::currentDateTime().toString(Qt::ISODate);
    emit recordsChanged();
    emit statisticsChanged();
    emit hardwareChanged();
}

QVariantList Fa3RepositoryModel::searchRecords(const QString &query) const
{
    const auto needle = query.trimmed();
    QVariantList result;
    for (const auto &value : m_records) {
        const auto map = value.toMap();
        const auto haystack = QString("%1 %2 %3 %4 %5").arg(map.value("id").toString(), map.value("title").toString(), map.value("status").toString(), map.value("category").toString(), map.value("path").toString());
        if (needle.isEmpty() || haystack.contains(needle, Qt::CaseInsensitive)) {
            result.append(map);
            if (result.size() >= 300) break;
        }
    }
    return result;
}

QVariantList Fa3RepositoryModel::recordsByCategory(const QString &category) const
{
    QVariantList result;
    for (const auto &value : m_records) {
        const auto map = value.toMap();
        if (map.value("category").toString().compare(category, Qt::CaseInsensitive) == 0) result.append(map);
    }
    return result;
}

QString Fa3RepositoryModel::createDraftChangeSet(const QString &scope, const QString &action, const QString &target, const QString &rationale)
{
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    QDir dir(base);
    if (!dir.mkpath("changesets")) return {};
    dir.cd("changesets");

    const auto stamp = QDateTime::currentDateTimeUtc().toString("yyyyMMddTHHmmsszzzZ");
    const auto id = QString("FA3-GUI-DRAFT-%1").arg(stamp);
    const auto filePath = dir.filePath(id + ".json");

    QJsonObject object{{"schema", "fa3.changeset-draft.v1"}, {"id", id}, {"status", "DRAFT_NOT_SUBMITTED"},
        {"created_at", QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)}, {"created_by", "FA3 Control Center"},
        {"scope", scope.trimmed()}, {"action", action.trimmed()}, {"target", target.trimmed()}, {"rationale", rationale.trimmed()},
        {"direct_execution_allowed", false}, {"canonical_write_allowed", false}, {"privileged_execution_allowed", false}, {"submission_required", true}};

    QSaveFile file(filePath);
    if (!file.open(QIODevice::WriteOnly)) return {};
    file.write(QJsonDocument(object).toJson(QJsonDocument::Indented));
    if (!file.commit()) return {};
    return filePath;
}

bool Fa3RepositoryModel::openLocalPath(const QString &relativePath) const
{
    const auto clean = QDir::cleanPath(relativePath);
    if (clean.startsWith("..") || QDir::isAbsolutePath(clean)) return false;
    const auto absolute = QDir(m_repoRoot).absoluteFilePath(clean);
    if (!QFileInfo::exists(absolute)) return false;
    return QDesktopServices::openUrl(QUrl::fromLocalFile(absolute));
}

QString Fa3RepositoryModel::hostName() const { return QSysInfo::machineHostName(); }
QString Fa3RepositoryModel::osName() const { return QSysInfo::prettyProductName(); }
QString Fa3RepositoryModel::architecture() const { return QSysInfo::currentCpuArchitecture(); }
QString Fa3RepositoryModel::kernelVersion() const { return QSysInfo::kernelVersion(); }
int Fa3RepositoryModel::cpuThreads() const { return QThread::idealThreadCount(); }
double Fa3RepositoryModel::memoryGiB() const { return memInfoGiB("MemTotal"); }
double Fa3RepositoryModel::memoryAvailableGiB() const { return memInfoGiB("MemAvailable"); }

QString Fa3RepositoryModel::uptime() const
{
    const QString raw = readTrimmed("/proc/uptime").section(' ', 0, 0);
    bool ok = false;
    qint64 seconds = static_cast<qint64>(raw.toDouble(&ok));
    if (!ok) return {};
    const qint64 days = seconds / 86400;
    seconds %= 86400;
    const qint64 hours = seconds / 3600;
    const qint64 minutes = (seconds % 3600) / 60;
    return QString("%1d %2h %3m").arg(days).arg(hours).arg(minutes);
}

QString Fa3RepositoryModel::cpuModel() const
{
    QFile file("/proc/cpuinfo");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return {};
    while (!file.atEnd()) {
        const QString line = QString::fromUtf8(file.readLine());
        if (line.startsWith("model name")) return line.section(':', 1).trimmed();
        if (line.startsWith("Hardware")) return line.section(':', 1).trimmed();
    }
    return QSysInfo::currentCpuArchitecture();
}

int Fa3RepositoryModel::cpuSockets() const
{
    QFile file("/proc/cpuinfo");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return 1;
    QSet<QString> sockets;
    while (!file.atEnd()) {
        const QString line = QString::fromUtf8(file.readLine());
        if (line.startsWith("physical id")) sockets.insert(line.section(':', 1).trimmed());
    }
    return sockets.isEmpty() ? 1 : sockets.size();
}

int Fa3RepositoryModel::cpuCores() const
{
    QFile file("/proc/cpuinfo");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return qMax(1, cpuThreads());
    QSet<QString> cores;
    QString socket = "0";
    QString core;
    while (!file.atEnd()) {
        const QString line = QString::fromUtf8(file.readLine()).trimmed();
        if (line.startsWith("physical id")) socket = line.section(':', 1).trimmed();
        else if (line.startsWith("core id")) core = line.section(':', 1).trimmed();
        else if (line.isEmpty() && !core.isEmpty()) {
            cores.insert(socket + ':' + core);
            core.clear();
        }
    }
    if (!core.isEmpty()) cores.insert(socket + ':' + core);
    return cores.isEmpty() ? qMax(1, cpuThreads()) : cores.size();
}

QVariantList Fa3RepositoryModel::gpuDevices() const
{
    QVariantList result;
    QSet<QString> seen;

    const QDir nvidiaDir("/proc/driver/nvidia/gpus");
    for (const QString &entry : nvidiaDir.entryList(QDir::Dirs | QDir::NoDotAndDotDot)) {
        const QVariantMap info = parseColonFile(nvidiaDir.filePath(entry + "/information"));
        QVariantMap gpu;
        const QString model = info.value("Model").toString();
        const QString uuid = info.value("GPU UUID").toString();
        gpu.insert("name", model.isEmpty() ? QString("NVIDIA GPU %1").arg(entry) : model);
        gpu.insert("vendor", "NVIDIA");
        gpu.insert("bus", info.value("Bus Location").toString().isEmpty() ? entry : info.value("Bus Location").toString());
        gpu.insert("uuid", uuid);
        gpu.insert("driver", "nvidia");
        gpu.insert("source", "/proc/driver/nvidia");
        result.append(gpu);
        seen.insert(gpu.value("bus").toString());
    }

    const QDir drmDir("/sys/class/drm");
    for (const QString &card : drmDir.entryList({"card[0-9]*"}, QDir::Dirs | QDir::NoDotAndDotDot)) {
        const QString base = drmDir.filePath(card + "/device");
        const QString vendor = readTrimmed(base + "/vendor");
        const QString device = readTrimmed(base + "/device");
        const QString bus = QFileInfo(base).canonicalFilePath().section('/', -1);
        if (!bus.isEmpty() && seen.contains(bus)) continue;
        const QString driverTarget = QFileInfo(base + "/driver").symLinkTarget();
        QVariantMap gpu;
        gpu.insert("name", QString("%1 (%2:%3)").arg(card, vendor, device));
        gpu.insert("vendor", vendor);
        gpu.insert("bus", bus);
        gpu.insert("uuid", "");
        gpu.insert("driver", QFileInfo(driverTarget).fileName());
        gpu.insert("source", "/sys/class/drm");
        result.append(gpu);
    }
    return result;
}

QVariantList Fa3RepositoryModel::storageDevices() const
{
    QVariantList result;
    for (const QStorageInfo &storage : QStorageInfo::mountedVolumes()) {
        if (!storage.isValid() || !storage.isReady() || storage.bytesTotal() <= 0) continue;
        QVariantMap item;
        item.insert("name", storage.displayName().isEmpty() ? storage.rootPath() : storage.displayName());
        item.insert("root", storage.rootPath());
        item.insert("filesystem", QString::fromUtf8(storage.fileSystemType()));
        item.insert("totalGiB", storage.bytesTotal() / 1024.0 / 1024.0 / 1024.0);
        item.insert("freeGiB", storage.bytesAvailable() / 1024.0 / 1024.0 / 1024.0);
        item.insert("readOnly", storage.isReadOnly());
        result.append(item);
    }
    return result;
}

QVariantList Fa3RepositoryModel::peripheralDevices() const
{
    QVariantList result;
    QSet<QString> keys;
    auto add = [&](const QString &category, const QString &name, const QString &path, const QString &detail) {
        if (name.trimmed().isEmpty() || result.size() >= 128) return;
        const QString key = category + '|' + name + '|' + path;
        if (keys.contains(key)) return;
        keys.insert(key);
        QVariantMap item;
        item.insert("category", category);
        item.insert("name", name.trimmed());
        item.insert("path", path);
        item.insert("detail", detail.trimmed());
        result.append(item);
    };

    const QDir inputDir("/sys/class/input");
    for (const QString &entry : inputDir.entryList({"event*"}, QDir::Dirs | QDir::NoDotAndDotDot)) {
        add("Input / HID", readTrimmed(inputDir.filePath(entry + "/device/name")), "/dev/input/" + entry, entry);
    }

    const QDir videoDir("/sys/class/video4linux");
    for (const QString &entry : videoDir.entryList({"video*"}, QDir::Dirs | QDir::NoDotAndDotDot)) {
        add("Camera / V4L2", readTrimmed(videoDir.filePath(entry + "/name")), "/dev/" + entry, entry);
    }

    const QDir soundDir("/sys/class/sound");
    for (const QString &entry : soundDir.entryList({"midiC*"}, QDir::Dirs | QDir::NoDotAndDotDot)) {
        add("MIDI", entry, "/dev/snd/" + entry, "ALSA MIDI device");
    }

    const QDir usbDir("/sys/bus/usb/devices");
    for (const QString &entry : usbDir.entryList(QDir::Dirs | QDir::NoDotAndDotDot)) {
        const QString product = readTrimmed(usbDir.filePath(entry + "/product"));
        if (product.isEmpty()) continue;
        const QString manufacturer = readTrimmed(usbDir.filePath(entry + "/manufacturer"));
        add("USB", product, entry, manufacturer);
    }
    return result;
}
