#include "ScopeAuthorityGuardService.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>

namespace {
QString existingRepoCandidate(const QString &path)
{
    QDir dir(path);
    if (QFileInfo::exists(dir.filePath(QStringLiteral("canonical/FA3-AUTHORITY-CONTRACT-REGISTRY-001.json")))
        && QFileInfo::exists(dir.filePath(QStringLiteral("canonical/FA3-LAYER-CONTRACT-REGISTRY-001.json"))))
        return dir.absolutePath();
    return {};
}

QJsonObject readObject(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    QJsonParseError error;
    const QJsonDocument doc = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject()) return {};
    return doc.object();
}
}

ScopeAuthorityGuardService::ScopeAuthorityGuardService(QObject *parent)
    : QObject(parent)
{
    refresh();
}

QString ScopeAuthorityGuardService::state() const { return m_state; }
QVariantList ScopeAuthorityGuardService::layers() const { return m_layers; }
QVariantList ScopeAuthorityGuardService::actors() const { return m_actors; }
QVariantList ScopeAuthorityGuardService::recentEvents() const { return m_recentEvents; }
QString ScopeAuthorityGuardService::lastError() const { return m_lastError; }

QString ScopeAuthorityGuardService::locateRepoRoot() const
{
    const QString envRoot = qEnvironmentVariable("FA3_REPO_ROOT");
    if (!envRoot.isEmpty()) {
        const QString found = existingRepoCandidate(envRoot);
        if (!found.isEmpty()) return found;
    }
    for (const QString &candidate : {
             QDir::currentPath(),
             QCoreApplication::applicationDirPath() + QStringLiteral("/.."),
             QCoreApplication::applicationDirPath() + QStringLiteral("/../.."),
             QCoreApplication::applicationDirPath() + QStringLiteral("/../../..")}) {
        const QString found = existingRepoCandidate(QDir(candidate).absolutePath());
        if (!found.isEmpty()) return found;
    }
    return {};
}

QString ScopeAuthorityGuardService::eventLogPath() const
{
    const QString configured = qEnvironmentVariable("FA3_SCOPE_GUARD_EVENT_LOG");
    if (!configured.isEmpty() && configured != QStringLiteral("AUTO"))
        return configured;
    const QString stateHome = qEnvironmentVariable("XDG_STATE_HOME");
    const QString base = stateHome.isEmpty()
        ? QDir::homePath() + QStringLiteral("/.local/state")
        : stateHome;
    return QDir(base).filePath(QStringLiteral("fa3/scope-authority-guard/decisions.jsonl"));
}

bool ScopeAuthorityGuardService::loadCanonical()
{
    const QString root = locateRepoRoot();
    if (root.isEmpty()) return false;
    const QJsonObject authority = readObject(QDir(root).filePath(
        QStringLiteral("canonical/FA3-AUTHORITY-CONTRACT-REGISTRY-001.json")));
    const QJsonObject layers = readObject(QDir(root).filePath(
        QStringLiteral("canonical/FA3-LAYER-CONTRACT-REGISTRY-001.json")));
    if (authority.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.authority-contract-registry.v1")
        || layers.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.layer-contract-registry.v1"))
        return false;
    m_actors = authority.value(QStringLiteral("actors")).toArray().toVariantList();
    m_layers = layers.value(QStringLiteral("layers")).toArray().toVariantList();
    emit actorsChanged();
    emit layersChanged();
    return true;
}

void ScopeAuthorityGuardService::loadEvents()
{
    QVariantList rows;
    QFile file(eventLogPath());
    if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QList<QByteArray> lines;
        while (!file.atEnd()) lines.push_back(file.readLine());
        const int start = qMax(0, lines.size() - 250);
        for (int i = start; i < lines.size(); ++i) {
            QJsonParseError error;
            const QJsonDocument doc = QJsonDocument::fromJson(lines.at(i).trimmed(), &error);
            if (error.error == QJsonParseError::NoError && doc.isObject()
                && doc.object().value(QStringLiteral("schema")).toString() == QStringLiteral("fa3.scope-authority-guard-event.v1"))
                rows.push_back(doc.object().toVariantMap());
        }
    }
    m_recentEvents = rows;
    emit recentEventsChanged();
}

QVariantMap ScopeAuthorityGuardService::counters() const
{
    QVariantMap out{{QStringLiteral("ALLOW"), 0}, {QStringLiteral("DELEGATE"), 0},
                    {QStringLiteral("SPLIT"), 0}, {QStringLiteral("ESCALATE"), 0},
                    {QStringLiteral("DENY"), 0}, {QStringLiteral("QUARANTINE"), 0}};
    for (const QVariant &entry : m_recentEvents) {
        const QString result = entry.toMap().value(QStringLiteral("result")).toString();
        if (out.contains(result)) out[result] = out.value(result).toInt() + 1;
    }
    return out;
}

QVariantMap ScopeAuthorityGuardService::canonicalSnapshot() const
{
    return {
        {QStringLiteral("profile"), QStringLiteral("FA3-SCOPE-AUTHORITY-GUARD-001")},
        {QStringLiteral("authorityRegistry"), QStringLiteral("FA3-AUTHORITY-CONTRACT-REGISTRY-001")},
        {QStringLiteral("layerRegistry"), QStringLiteral("FA3-LAYER-CONTRACT-REGISTRY-001")},
        {QStringLiteral("layerCount"), 12},
        {QStringLiteral("capabilityCount"), 175},
        {QStringLiteral("defaultPolicy"), QStringLiteral("DENY")},
        {QStringLiteral("guardIsAuthority"), false},
        {QStringLiteral("directScopeOverride"), false},
        {QStringLiteral("operatorActionsAreDraftOnly"), true}
    };
}

void ScopeAuthorityGuardService::refresh()
{
    m_lastError.clear();
    if (loadCanonical()) {
        m_state = QStringLiteral("CANONICAL_READ_ONLY");
    } else {
        m_state = QStringLiteral("REPOSITORY_NOT_FOUND_OR_INVALID");
        m_lastError = QStringLiteral("Canonical guard registries unavailable; no authority state is inferred.");
    }
    emit stateChanged();
    emit lastErrorChanged();
    loadEvents();
}
