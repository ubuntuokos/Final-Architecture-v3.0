#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class DecisionFabricService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(QVariantList recentDecisions READ recentDecisions NOTIFY recentDecisionsChanged)
    Q_PROPERTY(QVariantList radarProjects READ radarProjects NOTIFY radarProjectsChanged)
    Q_PROPERTY(QVariantList contextItems READ contextItems NOTIFY contextItemsChanged)
    Q_PROPERTY(QString snapshotCommit READ snapshotCommit NOTIFY radarProjectsChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

public:
    explicit DecisionFabricService(QObject *parent = nullptr);

    QString state() const;
    QVariantList recentDecisions() const;
    QVariantList radarProjects() const;
    QVariantList contextItems() const;
    QString snapshotCommit() const;
    QString lastError() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap canonicalSnapshot() const;

signals:
    void stateChanged();
    void recentDecisionsChanged();
    void radarProjectsChanged();
    void contextItemsChanged();
    void lastErrorChanged();

private:
    QString locateRepoRoot() const;
    QString tracePath() const;
    QString contextPath() const;
    void loadTraces();
    void loadRadar();
    void loadContext();

    QString m_state = QStringLiteral("UNVERIFIED");
    QVariantList m_recentDecisions;
    QVariantList m_radarProjects;
    QVariantList m_contextItems;
    QString m_snapshotCommit = QStringLiteral("a27922ad457389775f4fe4eadcf688afc9d36d83");
    QString m_lastError;
};
