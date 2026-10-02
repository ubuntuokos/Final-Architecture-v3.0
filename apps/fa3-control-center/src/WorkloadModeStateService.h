#pragma once
#include <QDBusServiceWatcher>
#include <QObject>
#include <QVariantMap>

class WorkloadModeStateService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString effectiveMode READ effectiveMode NOTIFY stateChanged)
    Q_PROPERTY(QString localMode READ localMode NOTIFY stateChanged)
    Q_PROPERTY(QString authority READ authority NOTIFY stateChanged)
    Q_PROPERTY(QString fa3State READ fa3State NOTIFY stateChanged)
    Q_PROPERTY(QString gameModeState READ gameModeState NOTIFY stateChanged)
    Q_PROPERTY(QString safetyState READ safetyState NOTIFY stateChanged)
    Q_PROPERTY(QString conflictState READ conflictState NOTIFY stateChanged)
    Q_PROPERTY(QString resourcePressure READ resourcePressure NOTIFY stateChanged)
    Q_PROPERTY(int activeWorkloadCount READ activeWorkloadCount NOTIFY stateChanged)
    Q_PROPERTY(bool degraded READ degraded NOTIFY stateChanged)
    Q_PROPERTY(QString degradedReason READ degradedReason NOTIFY stateChanged)
    Q_PROPERTY(bool serviceAvailable READ serviceAvailable NOTIFY stateChanged)

public:
    explicit WorkloadModeStateService(QObject *parent = nullptr);
    QString effectiveMode() const { return m_effectiveMode; }
    QString localMode() const { return m_localMode; }
    QString authority() const { return m_authority; }
    QString fa3State() const { return m_fa3State; }
    QString gameModeState() const { return m_gameModeState; }
    QString safetyState() const { return m_safetyState; }
    QString conflictState() const { return m_conflictState; }
    QString resourcePressure() const { return m_resourcePressure; }
    int activeWorkloadCount() const { return m_activeWorkloadCount; }
    bool degraded() const { return m_degraded; }
    QString degradedReason() const { return m_degradedReason; }
    bool serviceAvailable() const { return m_serviceAvailable; }

    Q_INVOKABLE void refresh();

signals:
    void stateChanged();

private slots:
    void onRemoteStateChanged(const QVariantMap &state);
    void onServiceRegistered(const QString &service);
    void onServiceUnregistered(const QString &service);

private:
    void applyState(const QVariantMap &state);
    void markUnavailable(const QString &reason);
    QDBusServiceWatcher m_watcher;
    QString m_effectiveMode = QStringLiteral("DEGRADED");
    QString m_localMode = QStringLiteral("NORMAL");
    QString m_authority = QStringLiteral("UNAVAILABLE");
    QString m_fa3State = QStringLiteral("DISCONNECTED");
    QString m_gameModeState = QStringLiteral("UNAVAILABLE");
    QString m_safetyState = QStringLiteral("PASS");
    QString m_conflictState = QStringLiteral("NONE");
    QString m_resourcePressure = QStringLiteral("UNKNOWN");
    int m_activeWorkloadCount = 0;
    bool m_degraded = true;
    QString m_degradedReason = QStringLiteral("WORKLOAD_MODE_REQUIRED_SERVICE_UNAVAILABLE");
    bool m_serviceAvailable = false;
};
