#include "SkillFabricService.h"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStringList>
#include <QVariantMap>

namespace {
QString existingRoot(const QString &candidate)
{
    QDir dir(candidate);
    if (QFileInfo::exists(dir.filePath(QStringLiteral("canonical/skill-registry.json")))
        && QFileInfo::exists(dir.filePath(QStringLiteral("canonical/profiles/FA3-SKILL-FABRIC-001.json"))))
        return dir.absolutePath();
    return {};
}
}

SkillFabricService::SkillFabricService(QObject *parent) : QObject(parent)
{
    connect(&m_watcher, &QFileSystemWatcher::fileChanged, this,
            [this](const QString &) { refresh(); });
    refresh();
}

QString SkillFabricService::locateRepoRoot() const
{
    const QString envRoot = qEnvironmentVariable("FA3_REPO_ROOT");
    if (!envRoot.isEmpty()) {
        const QString found = existingRoot(envRoot);
        if (!found.isEmpty()) return found;
    }
    for (const QString &candidate : {
             QDir::currentPath(),
             QCoreApplication::applicationDirPath() + QStringLiteral("/.."),
             QCoreApplication::applicationDirPath() + QStringLiteral("/../.."),
             QCoreApplication::applicationDirPath() + QStringLiteral("/../../..")}) {
        const QString found = existingRoot(candidate);
        if (!found.isEmpty()) return found;
    }
    return {};
}

void SkillFabricService::watchFiles(const QStringList &paths)
{
    if (!m_watcher.files().isEmpty())
        m_watcher.removePaths(m_watcher.files());
    QStringList existing;
    for (const QString &path : paths) {
        if (QFileInfo::exists(path)) existing.append(path);
    }
    if (!existing.isEmpty()) m_watcher.addPaths(existing);
}

void SkillFabricService::refresh()
{
    m_lastError.clear();
    m_skills.clear();
    m_reportSha256.clear();
    m_registryState = QStringLiteral("REGISTRY_NOT_AVAILABLE");
    m_referenceGateState = QStringLiteral("STATIC_REPORT_NOT_AVAILABLE");

    const QString root = locateRepoRoot();
    if (root.isEmpty()) {
        m_lastError = QStringLiteral("FA3 repository not available; no skill admission or runtime evidence inferred.");
        watchFiles({});
        emit changed();
        return;
    }

    const QString registryPath = QDir(root).filePath(QStringLiteral("canonical/skill-registry.json"));
    const QString reportPath = QDir(root).filePath(QStringLiteral("reports/skill-fabric-gate-report.json"));
    QFile registryFile(registryPath);
    if (!registryFile.open(QIODevice::ReadOnly)) {
        m_lastError = QStringLiteral("Skill registry unreadable.");
        watchFiles({registryPath, reportPath});
        emit changed();
        return;
    }
    QJsonParseError parse;
    const QJsonDocument registry = QJsonDocument::fromJson(registryFile.readAll(), &parse);
    if (parse.error != QJsonParseError::NoError || !registry.isObject()
        || registry.object().value(QStringLiteral("id")).toString()
            != QStringLiteral("FA3-SKILL-REGISTRY-001")) {
        m_registryState = QStringLiteral("REGISTRY_INVALID");
        m_lastError = QStringLiteral("Canonical skill registry parse or identity validation failed.");
        watchFiles({registryPath, reportPath});
        emit changed();
        return;
    }
    for (const QJsonValue &value : registry.object().value(QStringLiteral("entries")).toArray()) {
        if (!value.isObject()) continue;
        const QJsonObject record = value.toObject();
        QVariantMap row;
        row.insert(QStringLiteral("skill_id"), record.value(QStringLiteral("skill_id")).toString());
        row.insert(QStringLiteral("version"), record.value(QStringLiteral("version")).toString());
        row.insert(QStringLiteral("admission_status"),
                   record.value(QStringLiteral("admission_status")).toString());
        row.insert(QStringLiteral("distribution_class"),
                   record.value(QStringLiteral("distribution_class")).toString());
        row.insert(QStringLiteral("task_scoped"), record.value(QStringLiteral("task_scoped")).toBool());
        row.insert(QStringLiteral("authority"), false);
        row.insert(QStringLiteral("runtime_evidence"), QStringLiteral("NOT_VERIFIED_BY_THIS_VIEW"));
        m_skills.append(row);
    }
    m_registryState = QStringLiteral("REGISTRY_METADATA_ONLY");

    QFile reportFile(reportPath);
    if (reportFile.open(QIODevice::ReadOnly)) {
        const QByteArray bytes = reportFile.readAll();
        m_reportSha256 = QString::fromLatin1(
            QCryptographicHash::hash(bytes, QCryptographicHash::Sha256).toHex());
        parse = QJsonParseError{};
        const QJsonDocument report = QJsonDocument::fromJson(bytes, &parse);
        if (parse.error == QJsonParseError::NoError && report.isObject()
            && report.object().value(QStringLiteral("gate_id")).toString()
                == QStringLiteral("FA3-GATE-SKILL-FABRIC-001")) {
            const QJsonObject object = report.object();
            if (object.value(QStringLiteral("current_host_runtime_claim")).toBool()) {
                m_referenceGateState = QStringLiteral("UNTRUSTED_RUNTIME_CLAIM");
            } else if (object.value(QStringLiteral("result")).toString()
                       == QStringLiteral("PASS")) {
                m_referenceGateState = QStringLiteral("STATIC_REFERENCE_PASS");
            } else {
                m_referenceGateState = QStringLiteral("STATIC_REFERENCE_FAIL_OR_PENDING");
            }
        } else {
            m_referenceGateState = QStringLiteral("STATIC_REPORT_INVALID");
        }
    }
    // A locally generated reference report can never promote current-host
    // evidence or turn this GUI into a new validation/authorization authority.
    watchFiles({registryPath, reportPath});
    emit changed();
}
