#include "Fa3RepositoryModel.h"

#include <QCoreApplication>
#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QSettings>
#include <QSet>
#include <QStandardPaths>
#include <QUrl>

namespace {
QJsonObject admittedHostAttestation(const QString &repoRoot)
{
    const auto receiptPath = QDir(repoRoot).filePath(QStringLiteral("evidence/receipts/resource-admission-current-host.json"));
    QFile file(receiptPath);
    if (!file.open(QIODevice::ReadOnly)) return {};

    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) return {};

    const auto receipt = document.object();
    if (receipt.value(QStringLiteral("evidence_class")).toString() != QStringLiteral("CURRENT_HOST_ADMISSION")) return {};

    const auto subject = receipt.value(QStringLiteral("subject")).toObject();
    if (subject.value(QStringLiteral("profile_id")).toString() != QStringLiteral("FA3-RESOURCE-ADMISSION-CONTRACTS-001")) return {};
    if (subject.value(QStringLiteral("gate_id")).toString() != QStringLiteral("FA3-GATE-RESOURCE-ADMISSION-CURRENT-HOST-001")) return {};

    const auto result = receipt.value(QStringLiteral("result")).toObject();
    if (result.value(QStringLiteral("status")).toString() != QStringLiteral("PASS")) return {};
    bool passClaim = false;
    for (const auto &claim : result.value(QStringLiteral("claims")).toArray()) {
        if (claim.toString() == QStringLiteral("CURRENT_HOST_RESOURCE_ADMISSION_PASS")) {
            passClaim = true;
            break;
        }
    }
    if (!passClaim) return {};

    const auto payload = receipt.value(QStringLiteral("payload")).toObject();
    if (payload.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.resource-admission-current-host.payload.v1")) return {};

    const auto attestation = payload.value(QStringLiteral("host_attestation")).toObject();
    if (attestation.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.host-attestation.v1")) return {};
    if (attestation.value(QStringLiteral("secret_collection")).toString() != QStringLiteral("PROHIBITED")) return {};
    return attestation;
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

void Fa3RepositoryModel::scanApplications()
{
    m_installedApplications.clear();
    QStringList roots = {
        QStandardPaths::writableLocation(QStandardPaths::ApplicationsLocation),
        QStringLiteral("/usr/local/share/applications"),
        QStringLiteral("/usr/share/applications")
    };
    QSet<QString> seenRoots;
    QSet<QString> seenNames;
    for (const auto &root : roots) {
        const auto cleanRoot = QDir::cleanPath(root);
        if (cleanRoot.isEmpty() || seenRoots.contains(cleanRoot) || !QDir(cleanRoot).exists()) continue;
        seenRoots.insert(cleanRoot);
        QDirIterator it(cleanRoot, {QStringLiteral("*.desktop")}, QDir::Files, QDirIterator::Subdirectories);
        while (it.hasNext()) {
            const auto path = it.next();
            QSettings desktop(path, QSettings::IniFormat);
            desktop.beginGroup(QStringLiteral("Desktop Entry"));
            const auto type = desktop.value(QStringLiteral("Type")).toString();
            const bool hidden = desktop.value(QStringLiteral("Hidden"), false).toBool();
            const bool noDisplay = desktop.value(QStringLiteral("NoDisplay"), false).toBool();
            const auto name = desktop.value(QStringLiteral("Name")).toString().trimmed();
            const auto comment = desktop.value(QStringLiteral("Comment")).toString().trimmed();
            const auto exec = desktop.value(QStringLiteral("Exec")).toString().trimmed();
            desktop.endGroup();
            if (type != QStringLiteral("Application") || hidden || noDisplay || name.isEmpty()) continue;
            const auto key = name.toCaseFolded();
            if (seenNames.contains(key)) continue;
            seenNames.insert(key);
            QVariantMap row;
            row.insert(QStringLiteral("id"), QFileInfo(path).baseName());
            row.insert(QStringLiteral("title"), name);
            row.insert(QStringLiteral("subtitle"), comment.isEmpty() ? exec : comment);
            row.insert(QStringLiteral("status"), QStringLiteral("INSTALLED"));
            row.insert(QStringLiteral("category"), QStringLiteral("APPLICATION"));
            row.insert(QStringLiteral("sourceType"), QStringLiteral("APPLICATION"));
            row.insert(QStringLiteral("pageIndex"), -1);
            row.insert(QStringLiteral("path"), path);
            row.insert(QStringLiteral("exec"), exec);
            m_installedApplications.append(row);
        }
    }
}

void Fa3RepositoryModel::refresh()
{
    const auto discovered = discoverRepositoryRoot();
    if (discovered != m_repoRoot) { m_repoRoot = discovered; emit repoRootChanged(); }
    scanCanonical();
    scanEvidence();
    scanApplications();
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

QVariantList Fa3RepositoryModel::searchInstalledApplications(const QString &query) const
{
    const auto needle = query.trimmed();
    QVariantList result;
    for (const auto &value : m_installedApplications) {
        const auto map = value.toMap();
        const auto haystack = QStringLiteral("%1 %2 %3 %4")
            .arg(map.value(QStringLiteral("title")).toString(),
                 map.value(QStringLiteral("subtitle")).toString(),
                 map.value(QStringLiteral("id")).toString(),
                 map.value(QStringLiteral("exec")).toString());
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

QString Fa3RepositoryModel::hostName() const
{
    const auto attestation = admittedHostAttestation(m_repoRoot);
    return attestation.value(QStringLiteral("host")).toString(QStringLiteral("unavailable"));
}

QString Fa3RepositoryModel::kernelVersion() const
{
    const auto attestation = admittedHostAttestation(m_repoRoot);
    return attestation.value(QStringLiteral("kernel")).toString(QStringLiteral("unavailable"));
}

int Fa3RepositoryModel::cpuThreads() const
{
    const auto attestation = admittedHostAttestation(m_repoRoot);
    return attestation.value(QStringLiteral("cpu_topology")).toObject().value(QStringLiteral("logical_cpus")).toInt(0);
}

double Fa3RepositoryModel::memoryGiB() const
{
    const auto attestation = admittedHostAttestation(m_repoRoot);
    const auto bytes = attestation.value(QStringLiteral("memory_total_bytes")).toDouble(0.0);
    return bytes > 0.0 ? bytes / 1024.0 / 1024.0 / 1024.0 : 0.0;
}
