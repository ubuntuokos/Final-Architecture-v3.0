#include "DecisionFabricService.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcessEnvironment>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QTextStream>

namespace {
QString existingRepoCandidate(const QString &path)
{
    QDir dir(path);
    if (QFileInfo::exists(dir.filePath(QStringLiteral("canonical/profiles/FA3-DECISION-FABRIC-001.json"))))
        return dir.absolutePath();
    return {};
}
}

DecisionFabricService::DecisionFabricService(QObject *parent)
    : QObject(parent)
{
    refresh();
}

QString DecisionFabricService::state() const { return m_state; }
QVariantList DecisionFabricService::recentDecisions() const { return m_recentDecisions; }
QVariantList DecisionFabricService::radarProjects() const { return m_radarProjects; }
QVariantList DecisionFabricService::contextItems() const { return m_contextItems; }
QString DecisionFabricService::snapshotCommit() const { return m_snapshotCommit; }
QString DecisionFabricService::lastError() const { return m_lastError; }

QString DecisionFabricService::locateRepoRoot() const
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

QString DecisionFabricService::tracePath() const
{
    const QString stateHome = qEnvironmentVariable("XDG_STATE_HOME");
    const QString base = stateHome.isEmpty()
        ? QDir::homePath() + QStringLiteral("/.local/state")
        : stateHome;
    return QDir(base).filePath(QStringLiteral("fa3/decision-traces.jsonl"));
}

QString DecisionFabricService::contextPath() const
{
    const QString stateHome = qEnvironmentVariable("XDG_STATE_HOME");
    const QString base = stateHome.isEmpty()
        ? QDir::homePath() + QStringLiteral("/.local/state")
        : stateHome;
    return QDir(base).filePath(QStringLiteral("fa3/context-projection.json"));
}

void DecisionFabricService::loadTraces()
{
    QVariantList rows;
    QFile file(tracePath());
    if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QList<QByteArray> lines;
        while (!file.atEnd()) lines.push_back(file.readLine());
        const int start = qMax(0, lines.size() - 100);
        for (int i = start; i < lines.size(); ++i) {
            QJsonParseError error;
            const QJsonDocument doc = QJsonDocument::fromJson(lines.at(i).trimmed(), &error);
            if (error.error == QJsonParseError::NoError && doc.isObject()
                && doc.object().value(QStringLiteral("schema")).toString() == QStringLiteral("fa3.decision-trace.v1")) {
                rows.push_back(doc.object().toVariantMap());
            }
        }
    }
    m_recentDecisions = rows;
    emit recentDecisionsChanged();
}

void DecisionFabricService::loadRadar()
{
    QVariantList rows;
    const QString root = locateRepoRoot();
    if (root.isEmpty()) {
        m_radarProjects = rows;
        emit radarProjectsChanged();
        return;
    }
    const QString readmePath = QDir(root).filePath(
        QStringLiteral("research/external-project-radar/jev/upstream/%1/README.md").arg(m_snapshotCommit));
    QFile file(readmePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        m_radarProjects = rows;
        emit radarProjectsChanged();
        return;
    }

    QRegularExpression projectRx(QStringLiteral(
        R"(^- \[\*\*(.+?)\*\*\]\((https://github\.com/[^)]+)\))"));
    QString category = QStringLiteral("UNCLASSIFIED");
    QTextStream stream(&file);
    while (!stream.atEnd()) {
        const QString line = stream.readLine();
        if (line.startsWith(QStringLiteral("## ")) && !line.startsWith(QStringLiteral("### "))) {
            category = line.mid(3).trimmed();
            continue;
        }
        const auto match = projectRx.match(line);
        if (match.hasMatch()) {
            QVariantMap row;
            row.insert(QStringLiteral("name"), match.captured(1));
            row.insert(QStringLiteral("repository"), match.captured(2));
            row.insert(QStringLiteral("category"), category);
            row.insert(QStringLiteral("status"), QStringLiteral("REFERENCE_PENDING_FA3_REVIEW"));
            rows.push_back(row);
        }
    }
    m_radarProjects = rows;
    emit radarProjectsChanged();
}

void DecisionFabricService::loadContext()
{
    QVariantList rows;
    QFile file(contextPath());
    if (file.open(QIODevice::ReadOnly)) {
        QJsonParseError error;
        const QJsonDocument doc = QJsonDocument::fromJson(file.readAll(), &error);
        if (error.error == QJsonParseError::NoError && doc.isObject())
            rows = doc.object().value(QStringLiteral("items")).toArray().toVariantList();
    }
    m_contextItems = rows;
    emit contextItemsChanged();
}

QVariantMap DecisionFabricService::canonicalSnapshot() const
{
    return {
        {QStringLiteral("profile"), QStringLiteral("FA3-DECISION-FABRIC-001")},
        {QStringLiteral("contracts"), QStringLiteral("FA3-DECISION-FABRIC-CONTRACTS-001")},
        {QStringLiteral("context"), QStringLiteral("FA3-CONTEXT-SELECTION-001")},
        {QStringLiteral("radar"), QStringLiteral("FA3-EXTERNAL-PROJECT-RADAR-001")},
        {QStringLiteral("authority"), false},
        {QStringLiteral("modelRouterAuthority"), QStringLiteral("FA3-AUTH-MODEL-ROUTER-001")},
        {QStringLiteral("mcpAuthority"), QStringLiteral("FA3-AUTH-MCP-GATEWAY-001")},
        {QStringLiteral("resourceAuthority"), QStringLiteral("FA3-AUTH-HOST-RESOURCE-BROKER-001")},
        {QStringLiteral("directExecutionAllowed"), false},
        {QStringLiteral("candidateExpansionAllowed"), false},
        {QStringLiteral("mandatoryJev"), false},
        {QStringLiteral("defaultRollout"), QStringLiteral("SHADOW")}
    };
}

void DecisionFabricService::refresh()
{
    m_lastError.clear();
    const QString root = locateRepoRoot();
    if (root.isEmpty()) {
        m_state = QStringLiteral("REPOSITORY_NOT_FOUND");
        m_lastError = QStringLiteral("FA3 repository root not found; runtime projections remain unverified.");
    } else {
        m_state = QStringLiteral("CANONICAL_READ_ONLY");
    }
    emit stateChanged();
    emit lastErrorChanged();
    loadTraces();
    loadRadar();
    loadContext();
}
