#pragma once
#include <QDBusContext>
#include <QHash>
#include <QObject>
#include <QSet>
#include <QString>
#include <QVariantMap>

class ModeManager final : public QObject, protected QDBusContext
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.workloadmode.Manager1")
    Q_PROPERTY(QString effectiveMode READ effectiveMode NOTIFY stateChanged)
    Q_PROPERTY(QString authority READ authority NOTIFY stateChanged)
    Q_PROPERTY(QString fa3State READ fa3State NOTIFY stateChanged)
    Q_PROPERTY(QString gameModeState READ gameModeState NOTIFY stateChanged)
    Q_PROPERTY(QString safetyState READ safetyState NOTIFY stateChanged)
    Q_PROPERTY(QString conflictState READ conflictState NOTIFY stateChanged)
    Q_PROPERTY(QString resourcePressure READ resourcePressure NOTIFY stateChanged)
    Q_PROPERTY(int workloadCount READ workloadCount NOTIFY stateChanged)

public:
    explicit ModeManager(QObject *parent = nullptr);
    QString effectiveMode() const { return m_effectiveMode; }
    QString authority() const { return m_authority; }
    QString fa3State() const { return m_fa3State; }
    QString gameModeState() const { return m_gameModeState; }
    QString safetyState() const { return m_safetyState; }
    QString conflictState() const { return m_conflictState; }
    QString resourcePressure() const { return m_resourcePressure; }
    int workloadCount() const { return m_workloads.size(); }

    Q_SCRIPTABLE QVariantMap Hello(const QVariantMap &request);
    Q_SCRIPTABLE QVariantMap Status() const;
    Q_SCRIPTABLE QVariantMap RegisterWorkload(const QVariantMap &workload);
    Q_SCRIPTABLE QVariantMap ReleaseWorkload(const QString &workloadId);
    Q_SCRIPTABLE QVariantMap SetGameModeState(const QString &state);

    void refreshGameMode();
    void serviceOwnerChanged(const QString &name, const QString &oldOwner, const QString &newOwner);

signals:
    void stateChanged();
    void StateChanged(const QVariantMap &state);

private:
    void recompute();
    void publish();
    QVariantMap stateMap() const;
    static QString normalizedDomain(const QString &value);

    QHash<QString, QVariantMap> m_workloads;
    QSet<QString> m_fa3Peers;
    QString m_effectiveMode = QStringLiteral("NORMAL");
    QString m_authority = QStringLiteral("WORKLOAD_MODE_LOCAL");
    QString m_fa3State = QStringLiteral("DISCONNECTED");
    QString m_gameModeState = QStringLiteral("UNAVAILABLE");
    QString m_safetyState = QStringLiteral("PASS");
    QString m_conflictState = QStringLiteral("NONE");
    QString m_resourcePressure = QStringLiteral("NORMAL");
};
