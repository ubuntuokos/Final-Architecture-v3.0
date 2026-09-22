#pragma once
#include <QObject>
#include <QString>

class SessionVaultService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool configured READ configured NOTIFY stateChanged)
    Q_PROPERTY(bool unlocked READ unlocked NOTIFY stateChanged)
    Q_PROPERTY(QString imagePath READ imagePath CONSTANT)
    Q_PROPERTY(QString mountPath READ mountPath NOTIFY stateChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY stateChanged)
    Q_PROPERTY(QString errorMessage READ errorMessage NOTIFY stateChanged)
public:
    explicit SessionVaultService(QObject *parent = nullptr);
    ~SessionVaultService() override;
    bool configured() const;
    bool unlocked() const { return m_unlocked; }
    QString imagePath() const { return m_imagePath; }
    QString mountPath() const { return m_mountPath; }
    QString statusText() const { return m_statusText; }
    QString errorMessage() const { return m_errorMessage; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE bool unlockWithPassphrase(const QString &passphrase);
    Q_INVOKABLE bool tryAutoUnlock();
    Q_INVOKABLE bool unlockWithSecretService();
    Q_INVOKABLE bool unlockWithSecretFile(const QString &pathOrUrl);
    Q_INVOKABLE bool storePassphraseInSecretService(const QString &passphrase);
    Q_INVOKABLE bool lock();

signals:
    void stateChanged();

private:
    bool fail(const QString &message);
    bool openVault(const QString &passphrase);
    void clearError();
    QString localPath(const QString &pathOrUrl) const;

    QString m_imagePath;
    QString m_loopObject;
    QString m_clearObject;
    QString m_mountPath;
    QString m_aliasPath;
    QString m_statusText = QStringLiteral("NOT_CONFIGURED");
    QString m_errorMessage;
    bool m_unlocked = false;
};
