#pragma once

#include <QNetworkAccessManager>
#include <QObject>
#include <QPointer>
#include <QUrl>
#include <QVariantList>
#include <QVariantMap>

class QNetworkReply;
class QSaveFile;

class ModelLibraryService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString sharedRoot READ sharedRoot NOTIFY sharedRootChanged)
    Q_PROPERTY(QVariantList items READ items NOTIFY itemsChanged)
    Q_PROPERTY(QVariantList clients READ clients NOTIFY clientsChanged)
    Q_PROPERTY(bool downloadActive READ downloadActive NOTIFY downloadStateChanged)
    Q_PROPERTY(int downloadProgress READ downloadProgress NOTIFY downloadStateChanged)
    Q_PROPERTY(QString downloadStatus READ downloadStatus NOTIFY downloadStateChanged)

public:
    explicit ModelLibraryService(QObject *parent = nullptr);
    ~ModelLibraryService() override;

    QString sharedRoot() const { return m_sharedRoot; }
    QVariantList items() const { return m_items; }
    QVariantList clients() const { return m_clients; }
    bool downloadActive() const { return m_downloadActive; }
    int downloadProgress() const { return m_downloadProgress; }
    QString downloadStatus() const { return m_downloadStatus; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap setSharedRoot(const QUrl &directory);
    Q_INVOKABLE QVariantMap importFiles(const QVariantList &urls, const QString &category);
    Q_INVOKABLE QVariantMap moveModel(const QUrl &source, const QString &category);
    Q_INVOKABLE QVariantMap saveMetadata(const QUrl &modelUrl, const QVariantMap &metadata);
    Q_INVOKABLE QVariantMap setPreview(const QUrl &modelUrl, const QUrl &previewUrl);
    Q_INVOKABLE QVariantMap setClientRoot(const QString &clientKey, const QUrl &directory);
    Q_INVOKABLE QVariantMap linkClient(const QString &clientKey);
    Q_INVOKABLE QVariantMap startDownload(const QUrl &url, const QString &category, const QString &fileName = QString());
    Q_INVOKABLE void cancelDownload();
    Q_INVOKABLE bool openLocalPath(const QUrl &url) const;

signals:
    void sharedRootChanged();
    void itemsChanged();
    void clientsChanged();
    void downloadStateChanged();

private:
    struct ClientDefinition {
        QString key;
        QString name;
        QStringList candidates;
        QList<QPair<QString, QString>> links;
    };

    static QStringList modelExtensions();
    static QStringList previewExtensions();
    static QString categoryLabel(const QString &category);
    static QString humanReadableSize(qint64 bytes);
    static QString cleanFileName(const QString &name);
    static bool isInside(const QString &childPath, const QString &parentPath);
    static QString metadataPathFor(const QString &modelPath);
    static QString previewPathFor(const QString &modelPath);

    QList<ClientDefinition> clientDefinitions() const;
    QString defaultSharedRoot() const;
    QString categoryDirectory(const QString &category) const;
    void ensureSharedLayout();
    void scanItems();
    void scanClients();
    QVariantMap itemFromFile(const QString &absolutePath) const;
    QVariantMap result(bool ok, const QString &message) const;
    QVariantMap copyIntoCategory(const QString &sourcePath, const QString &category);
    QString clientRootFor(const ClientDefinition &definition) const;
    QString linkStateFor(const ClientDefinition &definition, const QString &rootPath) const;
    bool urlContainsCredentialMaterial(const QUrl &url) const;
    QString chooseDownloadFileName() const;
    bool prepareDownloadFile();
    void resetDownloadState(const QString &status, bool active, int progress);

    QString m_sharedRoot;
    QVariantList m_items;
    QVariantList m_clients;

    QNetworkAccessManager m_network;
    QPointer<QNetworkReply> m_reply;
    QSaveFile *m_downloadFile = nullptr;
    QUrl m_downloadUrl;
    QString m_downloadCategory;
    QString m_downloadRequestedName;
    QString m_downloadDestination;
    bool m_downloadActive = false;
    int m_downloadProgress = 0;
    QString m_downloadStatus;
};
