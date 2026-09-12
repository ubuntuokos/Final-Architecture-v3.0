#pragma once

#include <QObject>
#include <QVariantList>

class Fa3RepositoryModel final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString repoRoot READ repoRoot NOTIFY repoRootChanged)
    Q_PROPERTY(int canonicalRecordCount READ canonicalRecordCount NOTIFY statisticsChanged)
    Q_PROPERTY(int profileCount READ profileCount NOTIFY statisticsChanged)
    Q_PROPERTY(int providerCount READ providerCount NOTIFY statisticsChanged)
    Q_PROPERTY(int decisionCount READ decisionCount NOTIFY statisticsChanged)
    Q_PROPERTY(int evidenceCount READ evidenceCount NOTIFY statisticsChanged)
    Q_PROPERTY(int pendingCount READ pendingCount NOTIFY statisticsChanged)
    Q_PROPERTY(QString lastRefresh READ lastRefresh NOTIFY statisticsChanged)
    Q_PROPERTY(QString hostName READ hostName CONSTANT)
    Q_PROPERTY(QString kernelVersion READ kernelVersion CONSTANT)
    Q_PROPERTY(int cpuThreads READ cpuThreads CONSTANT)
    Q_PROPERTY(double memoryGiB READ memoryGiB CONSTANT)
    Q_PROPERTY(QVariantList records READ records NOTIFY recordsChanged)

public:
    explicit Fa3RepositoryModel(QObject *parent = nullptr);

    QString repoRoot() const { return m_repoRoot; }
    int canonicalRecordCount() const { return m_canonicalRecordCount; }
    int profileCount() const { return m_profileCount; }
    int providerCount() const { return m_providerCount; }
    int decisionCount() const { return m_decisionCount; }
    int evidenceCount() const { return m_evidenceCount; }
    int pendingCount() const { return m_pendingCount; }
    QString lastRefresh() const { return m_lastRefresh; }
    QString hostName() const;
    QString kernelVersion() const;
    int cpuThreads() const;
    double memoryGiB() const;
    QVariantList records() const { return m_records; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantList searchRecords(const QString &query) const;
    Q_INVOKABLE QVariantList recordsByCategory(const QString &category) const;
    Q_INVOKABLE QString createDraftChangeSet(const QString &scope, const QString &action, const QString &target, const QString &rationale);
    Q_INVOKABLE bool openLocalPath(const QString &relativePath) const;

signals:
    void repoRootChanged();
    void statisticsChanged();
    void recordsChanged();

private:
    QString discoverRepositoryRoot() const;
    void scanCanonical();
    void scanEvidence();
    QVariantMap recordFromJson(const QString &absolutePath, const QString &relativePath) const;

    QString m_repoRoot;
    QVariantList m_records;
    int m_canonicalRecordCount = 0;
    int m_profileCount = 0;
    int m_providerCount = 0;
    int m_decisionCount = 0;
    int m_evidenceCount = 0;
    int m_pendingCount = 0;
    QString m_lastRefresh;
};
