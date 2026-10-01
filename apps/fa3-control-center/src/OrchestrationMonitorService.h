#pragma once

#include <QFileSystemWatcher>
#include <QObject>
#include <QVariantList>

class OrchestrationMonitorService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY projectionChanged)
    Q_PROPERTY(QString sourcePath READ sourcePath NOTIFY projectionChanged)
    Q_PROPERTY(QString lastUpdated READ lastUpdated NOTIFY projectionChanged)
    Q_PROPERTY(int taskCount READ taskCount NOTIFY projectionChanged)
    Q_PROPERTY(int routedCount READ routedCount NOTIFY projectionChanged)
    Q_PROPERTY(int attentionRequired READ attentionRequired NOTIFY projectionChanged)
    Q_PROPERTY(QVariantList livenessRows READ livenessRows NOTIFY projectionChanged)
    Q_PROPERTY(bool authority READ authority CONSTANT)

public:
    explicit OrchestrationMonitorService(QObject *parent = nullptr);

    QString state() const;
    QString sourcePath() const;
    QString lastUpdated() const;
    int taskCount() const;
    int routedCount() const;
    int attentionRequired() const;
    QVariantList livenessRows() const;
    bool authority() const;

    Q_INVOKABLE void reload();

signals:
    void projectionChanged();

private:
    QString projectionPath() const;
    void installWatch();

    QFileSystemWatcher m_watcher;
    QString m_state = QStringLiteral("PENDING_TELEMETRY");
    QString m_sourcePath;
    QString m_lastUpdated;
    int m_taskCount = 0;
    int m_routedCount = 0;
    int m_attentionRequired = 0;
    QVariantList m_livenessRows;
};
