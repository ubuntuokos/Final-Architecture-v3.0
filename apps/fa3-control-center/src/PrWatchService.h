#pragma once

#include <QObject>
#include <QFileSystemWatcher>
#include <QVariantList>

// Read-only display projection of FA3 PR Watch's signed-observation cache.
// This does not hold GitHub credentials, authorize actions, run agents or grant PASS.
class PrWatchService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList items READ items NOTIFY changed)
    Q_PROPERTY(QString status READ status NOTIFY changed)
    Q_PROPERTY(QString lastObservedAt READ lastObservedAt NOTIFY changed)

public:
    explicit PrWatchService(QObject *parent = nullptr);
    QVariantList items() const { return m_items; }
    QString status() const { return m_status; }
    QString lastObservedAt() const { return m_lastObservedAt; }
    Q_INVOKABLE void refresh();

signals:
    void changed();

private:
    QString m_stateDir;
    QString m_stateFile;
    QVariantList m_items;
    QString m_status = QStringLiteral("PENDING_NO_OBSERVATIONS");
    QString m_lastObservedAt;
    QFileSystemWatcher m_watcher;
};
