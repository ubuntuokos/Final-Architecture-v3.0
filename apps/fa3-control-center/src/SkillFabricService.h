#pragma once

#include <QFileSystemWatcher>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QVariantList>

class SkillFabricService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString registryState READ registryState NOTIFY changed)
    Q_PROPERTY(QString referenceGateState READ referenceGateState NOTIFY changed)
    Q_PROPERTY(QString reportSha256 READ reportSha256 NOTIFY changed)
    Q_PROPERTY(QString lastError READ lastError NOTIFY changed)
    Q_PROPERTY(QVariantList skills READ skills NOTIFY changed)
    Q_PROPERTY(bool currentHostVerified READ currentHostVerified NOTIFY changed)

public:
    explicit SkillFabricService(QObject *parent = nullptr);

    QString registryState() const { return m_registryState; }
    QString referenceGateState() const { return m_referenceGateState; }
    QString reportSha256() const { return m_reportSha256; }
    QString lastError() const { return m_lastError; }
    QVariantList skills() const { return m_skills; }

    // This read-only service has NO trusted physical evidence verifier. Even
    // a local report asserting production PASS cannot change this property.
    bool currentHostVerified() const { return false; }

    Q_INVOKABLE void refresh();

signals:
    void changed();

private:
    QString locateRepoRoot() const;
    void watchFiles(const QStringList &paths);

    QString m_registryState = QStringLiteral("REGISTRY_NOT_AVAILABLE");
    QString m_referenceGateState = QStringLiteral("STATIC_REPORT_NOT_AVAILABLE");
    QString m_reportSha256;
    QString m_lastError;
    QVariantList m_skills;
    QFileSystemWatcher m_watcher;
};
