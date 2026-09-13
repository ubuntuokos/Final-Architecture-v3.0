#pragma once

#include <QObject>
#include <QVariantList>

class JournalService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString storageRoot READ storageRoot CONSTANT)
    Q_PROPERTY(QString lastRefresh READ lastRefresh NOTIFY changed)
    Q_PROPERTY(QString lastResult READ lastResult NOTIFY changed)
    Q_PROPERTY(int eventCount READ eventCount NOTIFY changed)
    Q_PROPERTY(int archiveCount READ archiveCount NOTIFY changed)
    Q_PROPERTY(int systemCount READ systemCount NOTIFY changed)
    Q_PROPERTY(int conversationCount READ conversationCount NOTIFY changed)
    Q_PROPERTY(int activeProjectCount READ activeProjectCount NOTIFY changed)
    Q_PROPERTY(int closedProjectCount READ closedProjectCount NOTIFY changed)
    Q_PROPERTY(int plannedProjectCount READ plannedProjectCount NOTIFY changed)
    Q_PROPERTY(QVariantList events READ events NOTIFY changed)
    Q_PROPERTY(QVariantList archives READ archives NOTIFY changed)

public:
    explicit JournalService(QObject *parent = nullptr);

    QString storageRoot() const { return m_storageRoot; }
    QString lastRefresh() const { return m_lastRefresh; }
    QString lastResult() const { return m_lastResult; }
    int eventCount() const { return m_events.size(); }
    int archiveCount() const { return m_archives.size(); }
    int systemCount() const { return m_systemCount; }
    int conversationCount() const { return m_conversationCount; }
    int activeProjectCount() const { return m_activeProjectCount; }
    int closedProjectCount() const { return m_closedProjectCount; }
    int plannedProjectCount() const { return m_plannedProjectCount; }
    QVariantList events() const { return m_events; }
    QVariantList archives() const { return m_archives; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantList filteredEvents(const QString &domain, const QString &query) const;
    Q_INVOKABLE QString recordEvent(const QString &domain,
                                    const QString &source,
                                    const QString &projectId,
                                    const QString &lifecycle,
                                    const QString &summary,
                                    const QString &details);
    Q_INVOKABLE QString archiveAll(const QString &reason = QStringLiteral("MANUAL"));
    Q_INVOKABLE QString archiveByPolicy();
    Q_INVOKABLE QString verifyArchive(const QString &fileName);
    Q_INVOKABLE QString restoreArchive(const QString &fileName);
    Q_INVOKABLE QString retireArchive(const QString &fileName);
    Q_INVOKABLE QString softDeleteEvent(const QString &eventId);
    Q_INVOKABLE QString exportJournal(const QString &format, const QString &query = QString());
    Q_INVOKABLE QString printJournal(const QString &query = QString());
    Q_INVOKABLE QString shareJournal(const QString &channel, const QString &query = QString());
    Q_INVOKABLE bool openStorageRoot() const;

signals:
    void changed();

private:
    QString activeLogPath() const;
    QString archivesPath() const;
    QString exportsPath() const;
    QString trashPath() const;
    bool ensureLayout();
    bool appendObject(const QJsonObject &object);
    QJsonArray activeObjects() const;
    static QByteArray canonicalPayload(const QJsonArray &events);
    static QString digestFor(const QJsonArray &events);
    static QString archiveFileName(const QString &archiveId);
    QJsonObject readArchive(const QString &fileName, QString *error = nullptr) const;
    QString createArchive(const QJsonArray &events, const QString &reason, bool clearActive);
    void recomputeStatistics();
    void setResult(const QString &value);

    QString m_storageRoot;
    QString m_lastRefresh;
    QString m_lastResult;
    QVariantList m_events;
    QVariantList m_archives;
    int m_systemCount = 0;
    int m_conversationCount = 0;
    int m_activeProjectCount = 0;
    int m_closedProjectCount = 0;
    int m_plannedProjectCount = 0;
};
