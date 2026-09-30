#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class ScopeAuthorityGuardService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(QVariantList layers READ layers NOTIFY layersChanged)
    Q_PROPERTY(QVariantList actors READ actors NOTIFY actorsChanged)
    Q_PROPERTY(QVariantList recentEvents READ recentEvents NOTIFY recentEventsChanged)
    Q_PROPERTY(QVariantMap counters READ counters NOTIFY recentEventsChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

public:
    explicit ScopeAuthorityGuardService(QObject *parent = nullptr);

    QString state() const;
    QVariantList layers() const;
    QVariantList actors() const;
    QVariantList recentEvents() const;
    QVariantMap counters() const;
    QString lastError() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap canonicalSnapshot() const;
    Q_INVOKABLE QString eventLogPath() const;

signals:
    void stateChanged();
    void layersChanged();
    void actorsChanged();
    void recentEventsChanged();
    void lastErrorChanged();

private:
    QString locateRepoRoot() const;
    bool loadCanonical();
    void loadEvents();

    QString m_state = QStringLiteral("UNVERIFIED");
    QVariantList m_layers;
    QVariantList m_actors;
    QVariantList m_recentEvents;
    QString m_lastError;
};
