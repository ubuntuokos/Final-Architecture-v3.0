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
#include <QStandardPaths>
#include <QSysInfo>
#include <QThread>
#include <QUrl>

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
QString Fa3RepositoryModel::kernelVersion() const { return QSysInfo::kernelVersion(); }
int Fa3RepositoryModel::cpuThreads() const { return QThread::idealThreadCount(); }

double Fa3RepositoryModel::memoryGiB() const
{
    QFile file("/proc/meminfo");
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return 0.0;
    while (!file.atEnd()) {
        const auto line = QString::fromUtf8(file.readLine());
        if (line.startsWith("MemTotal:")) {
            const auto parts = line.simplified().split(' ');
            if (parts.size() >= 2) {
                bool ok = false;
                const auto kib = parts.at(1).toDouble(&ok);
                if (ok) return kib / 1024.0 / 1024.0;
            }
        }
    }
    return 0.0;
}
