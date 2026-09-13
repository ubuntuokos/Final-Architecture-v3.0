#pragma once

#include <QObject>
#include <QHash>
#include <QStringList>
#include <QVariantList>
#include <QVariantMap>

class QFile;
class QNetworkAccessManager;
class QNetworkReply;
class QCryptographicHash;

class OpenModelDbService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList models READ models NOTIFY modelsChanged)
    Q_PROPERTY(QVariantList tags READ tags NOTIFY modelsChanged)
    Q_PROPERTY(QStringList scales READ scales NOTIFY modelsChanged)
    Q_PROPERTY(QStringList architectures READ architectures NOTIFY modelsChanged)
    Q_PROPERTY(QStringList platforms READ platforms NOTIFY modelsChanged)
    Q_PROPERTY(QVariantList downloads READ downloads NOTIFY downloadsChanged)
    Q_PROPERTY(QString catalogStatus READ catalogStatus NOTIFY catalogStatusChanged)
    Q_PROPERTY(bool catalogBusy READ catalogBusy NOTIFY catalogStatusChanged)
    Q_PROPERTY(QString stagingRoot READ stagingRoot CONSTANT)

public:
    explicit OpenModelDbService(QObject *parent = nullptr);
    ~OpenModelDbService() override;

    QVariantList models() const { return m_models; }
    QVariantList tags() const { return m_tags; }
    QStringList scales() const { return m_scales; }
    QStringList architectures() const { return m_architectures; }
    QStringList platforms() const { return m_platforms; }
    QVariantList downloads() const { return m_downloads; }
    QString catalogStatus() const { return m_catalogStatus; }
    bool catalogBusy() const { return m_catalogBusy; }
    QString stagingRoot() const { return m_stagingRoot; }

    Q_INVOKABLE void refreshCatalog();
    Q_INVOKABLE bool openExternalUrl(const QString &url) const;
    Q_INVOKABLE bool openStagingFolder() const;
    Q_INVOKABLE QString queueDownload(const QString &modelId,
                                      const QString &modelName,
                                      const QString &licenseId,
                                      const QVariantMap &resource);
    Q_INVOKABLE bool cancelDownload(const QString &downloadId);
    Q_INVOKABLE bool retryDownload(const QString &downloadId);

signals:
    void modelsChanged();
    void downloadsChanged();
    void catalogStatusChanged();

private:
    struct ActiveDownload {
        QString id;
        QString finalPath;
        QString partPath;
        QString expectedSha256;
        QNetworkReply *reply = nullptr;
        QFile *file = nullptr;
        QCryptographicHash *hash = nullptr;
        bool cancelled = false;
        bool ioFailed = false;
    };

    static QString scalarToString(const QVariant &value);
    static QString safeSegment(const QString &value);
    static QString resourceFileName(const QString &modelName, const QVariantMap &resource);
    static int scaleFromName(const QString &value);
    static bool validSha256(const QString &value);
    static bool dangerousFormat(const QString &format);

    QVariantMap parseModel(const QString &key, const QVariantMap &raw) const;
    QVariantMap parseResource(const QVariantMap &raw) const;
    QVariantMap parseTag(const QVariantMap &raw) const;
    void rebuildFacetLists();
    int downloadIndex(const QString &id) const;
    void updateDownload(const QString &id, const QVariantMap &changes);
    void startNextDownload();
    void startDownload(const QString &id);
    void finishActiveDownload();
    void setCatalogState(const QString &status, bool busy);

    QNetworkAccessManager *m_network = nullptr;
    QVariantList m_models;
    QVariantList m_tags;
    QStringList m_scales;
    QStringList m_architectures;
    QStringList m_platforms;
    QVariantList m_downloads;
    QString m_catalogStatus = QStringLiteral("NOT_LOADED");
    bool m_catalogBusy = false;
    QString m_stagingRoot;
    QString m_activeId;
    QHash<QString, ActiveDownload *> m_activeDownloads;
};
