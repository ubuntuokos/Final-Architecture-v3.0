#include "OrchestrationMonitorService.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>

OrchestrationMonitorService::OrchestrationMonitorService(QObject *parent)
    : QObject(parent)
{
    connect(&m_watcher, &QFileSystemWatcher::fileChanged, this, [this] { reload(); });
    connect(&m_watcher, &QFileSystemWatcher::directoryChanged, this, [this] { reload(); });
    reload();
}

QString OrchestrationMonitorService::state() const { return m_state; }
QString OrchestrationMonitorService::sourcePath() const { return m_sourcePath; }
QString OrchestrationMonitorService::lastUpdated() const { return m_lastUpdated; }
int OrchestrationMonitorService::taskCount() const { return m_taskCount; }
int OrchestrationMonitorService::routedCount() const { return m_routedCount; }
int OrchestrationMonitorService::attentionRequired() const { return m_attentionRequired; }
QVariantList OrchestrationMonitorService::livenessRows() const { return m_livenessRows; }
bool OrchestrationMonitorService::authority() const { return false; }

QString OrchestrationMonitorService::projectionPath() const
{
    const QString explicitPath = qEnvironmentVariable("FA3_ORCHESTRATION_MONITOR_PROJECTION");
    if (!explicitPath.isEmpty())
        return QFileInfo(explicitPath).absoluteFilePath();

    QString runtime = QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
    if (runtime.isEmpty())
        runtime = qEnvironmentVariable("XDG_RUNTIME_DIR");
    if (runtime.isEmpty())
        return {};
    return QDir(runtime).filePath(QStringLiteral("fa3/orchestration/monitor.json"));
}

void OrchestrationMonitorService::installWatch()
{
    if (!m_watcher.files().isEmpty())
        m_watcher.removePaths(m_watcher.files());
    if (!m_watcher.directories().isEmpty())
        m_watcher.removePaths(m_watcher.directories());

    if (m_sourcePath.isEmpty())
        return;

    QFileInfo info(m_sourcePath);
    if (info.exists()) {
        m_watcher.addPath(m_sourcePath);
        return;
    }

    QDir parent = info.absoluteDir();
    while (!parent.exists() && parent.cdUp()) {}
    if (parent.exists())
        m_watcher.addPath(parent.absolutePath());
}

void OrchestrationMonitorService::reload()
{
    m_sourcePath = projectionPath();
    m_taskCount = 0;
    m_routedCount = 0;
    m_attentionRequired = 0;
    m_livenessRows.clear();
    m_lastUpdated.clear();

    if (m_sourcePath.isEmpty()) {
        m_state = QStringLiteral("RUNTIME_PATH_UNAVAILABLE");
        installWatch();
        emit projectionChanged();
        return;
    }

    QFile file(m_sourcePath);
    if (!file.open(QIODevice::ReadOnly)) {
        m_state = QStringLiteral("PENDING_TELEMETRY");
        installWatch();
        emit projectionChanged();
        return;
    }

    QJsonParseError error;
    const QJsonDocument doc = QJsonDocument::fromJson(file.readAll(), &error);
    file.close();
    if (error.error != QJsonParseError::NoError || !doc.isObject()) {
        m_state = QStringLiteral("INVALID_PROJECTION");
        installWatch();
        emit projectionChanged();
        return;
    }

    const QJsonObject root = doc.object();
    if (root.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.orchestration-monitor-projection.v1")
        || root.value(QStringLiteral("authority")).toBool(true)
        || root.value(QStringLiteral("durable_source")).toString() != QStringLiteral("Temporal")) {
        m_state = QStringLiteral("REJECTED_PROJECTION");
        installWatch();
        emit projectionChanged();
        return;
    }

    m_taskCount = root.value(QStringLiteral("task_count")).toInt();
    m_routedCount = root.value(QStringLiteral("routed")).toInt();
    m_attentionRequired = root.value(QStringLiteral("attention_required")).toInt();

    const QJsonObject liveness = root.value(QStringLiteral("liveness_counts")).toObject();
    QStringList keys = liveness.keys();
    keys.sort();
    for (const QString &key : keys) {
        QVariantMap row;
        row.insert(QStringLiteral("state"), key);
        row.insert(QStringLiteral("count"), liveness.value(key).toInt());
        m_livenessRows.push_back(row);
    }

    m_lastUpdated = QFileInfo(m_sourcePath).lastModified().toUTC().toString(Qt::ISODate);
    m_state = QStringLiteral("LIVE_PROJECTION");
    installWatch();
    emit projectionChanged();
}
