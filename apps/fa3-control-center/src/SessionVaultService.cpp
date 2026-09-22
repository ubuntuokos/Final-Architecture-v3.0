#include "SessionVaultService.h"

#include <QDBusInterface>
#include <QDBusMessage>
#include <QDBusObjectPath>
#include <QDBusUnixFileDescriptor>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QProcess>
#include <QStandardPaths>
#include <QTimer>
#include <QUrl>
#include <QVariantMap>
#include <unistd.h>

static constexpr auto UDISKS_SERVICE = "org.freedesktop.UDisks2";

SessionVaultService::SessionVaultService(QObject *parent)
    : QObject(parent)
{
    const QString explicitImage = qEnvironmentVariable("FA3_SESSION_VAULT_IMAGE");
    const QString defaultImage = QDir::homePath() + QStringLiteral("/.local/share/fa3/state/fa3-state.img");
    const QString legacyImage = QDir::homePath() + QStringLiteral("/.local/share/fa3/vault/fa3-session-vault.img");
    if (!explicitImage.isEmpty())
        m_imagePath = explicitImage;
    else if (QFileInfo::exists(defaultImage))
        m_imagePath = defaultImage;
    else if (QFileInfo::exists(legacyImage))
        m_imagePath = legacyImage;
    else
        m_imagePath = defaultImage;
    const QString runtime = QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
    m_aliasPath = runtime + QStringLiteral("/fa3-state");
    refresh();
    QTimer::singleShot(0, this, [this]() { tryAutoUnlock(); });
}

SessionVaultService::~SessionVaultService()
{
    if (m_unlocked)
        lock();
}

bool SessionVaultService::configured() const
{
    const QFileInfo info(m_imagePath);
    return info.isFile() && info.size() > 0;
}

void SessionVaultService::clearError()
{
    m_errorMessage.clear();
}

bool SessionVaultService::fail(const QString &message)
{
    m_errorMessage = message;
    m_statusText = QStringLiteral("ERROR");
    emit stateChanged();
    return false;
}

void SessionVaultService::refresh()
{
    if (m_unlocked && !m_mountPath.isEmpty() && QDir(m_mountPath).exists())
        m_statusText = QStringLiteral("UNLOCKED");
    else if (configured())
        m_statusText = QStringLiteral("LOCKED");
    else
        m_statusText = QStringLiteral("NOT_CONFIGURED");
    emit stateChanged();
}

QString SessionVaultService::localPath(const QString &pathOrUrl) const
{
    const QUrl url(pathOrUrl);
    return url.isLocalFile() ? url.toLocalFile() : pathOrUrl;
}

bool SessionVaultService::openVault(const QString &passphrase)
{
    clearError();
    if (!configured())
        return fail(QStringLiteral("FA3 session vault image is not configured."));
    if (m_unlocked)
        return true;
    if (passphrase.isEmpty())
        return fail(QStringLiteral("Empty vault secret is not allowed."));

    QFile image(m_imagePath);
    if (!image.open(QIODevice::ReadWrite))
        return fail(QStringLiteral("Cannot open vault image."));

    QDBusInterface manager(UDISKS_SERVICE, "/org/freedesktop/UDisks2/Manager",
                           "org.freedesktop.UDisks2.Manager", QDBusConnection::systemBus());
    QDBusUnixFileDescriptor fd(image.handle());
    QVariantMap loopOptions;
    loopOptions.insert(QStringLiteral("read-only"), false);
    QDBusMessage loopReply = manager.call(QStringLiteral("LoopSetup"), QVariant::fromValue(fd), loopOptions);
    if (loopReply.type() == QDBusMessage::ErrorMessage || loopReply.arguments().isEmpty())
        return fail(QStringLiteral("UDisks2 LoopSetup failed: ") + loopReply.errorMessage());

    m_loopObject = qvariant_cast<QDBusObjectPath>(loopReply.arguments().constFirst()).path();

    QDBusInterface encrypted(UDISKS_SERVICE, m_loopObject,
                             "org.freedesktop.UDisks2.Encrypted", QDBusConnection::systemBus());
    QDBusMessage unlockReply = encrypted.call(QStringLiteral("Unlock"), passphrase, QVariantMap{});
    if (unlockReply.type() == QDBusMessage::ErrorMessage || unlockReply.arguments().isEmpty()) {
        QDBusInterface loop(UDISKS_SERVICE, m_loopObject, "org.freedesktop.UDisks2.Loop",
                            QDBusConnection::systemBus());
        loop.call(QStringLiteral("Delete"), QVariantMap{});
        m_loopObject.clear();
        return fail(QStringLiteral("Vault unlock failed."));
    }

    m_clearObject = qvariant_cast<QDBusObjectPath>(unlockReply.arguments().constFirst()).path();
    QDBusInterface filesystem(UDISKS_SERVICE, m_clearObject,
                              "org.freedesktop.UDisks2.Filesystem", QDBusConnection::systemBus());
    QVariantMap mountOptions;
    mountOptions.insert(QStringLiteral("options"), QStringLiteral("nodev,nosuid,noexec"));
    const QString user = qEnvironmentVariable("USER");
    if (!user.isEmpty())
        mountOptions.insert(QStringLiteral("as-user"), user);
    QDBusMessage mountReply = filesystem.call(QStringLiteral("Mount"), mountOptions);
    if (mountReply.type() == QDBusMessage::ErrorMessage || mountReply.arguments().isEmpty()) {
        encrypted.call(QStringLiteral("Lock"), QVariantMap{});
        QDBusInterface loop(UDISKS_SERVICE, m_loopObject, "org.freedesktop.UDisks2.Loop",
                            QDBusConnection::systemBus());
        loop.call(QStringLiteral("Delete"), QVariantMap{});
        m_loopObject.clear();
        m_clearObject.clear();
        return fail(QStringLiteral("Vault mount failed: ") + mountReply.errorMessage());
    }

    m_mountPath = mountReply.arguments().constFirst().toString();
    QFile::remove(m_aliasPath);
    const QByteArray target = QFile::encodeName(m_mountPath);
    const QByteArray alias = QFile::encodeName(m_aliasPath);
    if (::symlink(target.constData(), alias.constData()) != 0) {
        filesystem.call(QStringLiteral("Unmount"), QVariantMap{});
        encrypted.call(QStringLiteral("Lock"), QVariantMap{});
        QDBusInterface loop(UDISKS_SERVICE, m_loopObject, "org.freedesktop.UDisks2.Loop",
                            QDBusConnection::systemBus());
        loop.call(QStringLiteral("Delete"), QVariantMap{});
        m_loopObject.clear();
        m_clearObject.clear();
        m_mountPath.clear();
        return fail(QStringLiteral("Cannot create session vault runtime alias."));
    }

    m_unlocked = true;
    m_statusText = QStringLiteral("UNLOCKED");
    emit stateChanged();
    return true;
}

bool SessionVaultService::unlockWithPassphrase(const QString &passphrase)
{
    return openVault(passphrase);
}

bool SessionVaultService::tryAutoUnlock()
{
    if (!configured() || m_unlocked)
        return m_unlocked;

    QProcess p;
    p.start(QStringLiteral("secret-tool"),
            {QStringLiteral("lookup"), QStringLiteral("application"), QStringLiteral("FA3"),
             QStringLiteral("purpose"), QStringLiteral("session-vault")});
    if (!p.waitForStarted(1000) || !p.waitForFinished(3000) || p.exitCode() != 0) {
        clearError();
        m_statusText = QStringLiteral("LOCKED");
        emit stateChanged();
        return false;
    }

    QByteArray secret = p.readAllStandardOutput();
    while (secret.endsWith('\n') || secret.endsWith('\r'))
        secret.chop(1);
    if (secret.isEmpty()) {
        clearError();
        m_statusText = QStringLiteral("LOCKED");
        emit stateChanged();
        return false;
    }

    const QString passphrase = QString::fromUtf8(secret);
    secret.fill('\0');
    return openVault(passphrase);
}

bool SessionVaultService::unlockWithSecretService()
{
    QProcess p;
    p.start(QStringLiteral("secret-tool"),
            {QStringLiteral("lookup"), QStringLiteral("application"), QStringLiteral("FA3"),
             QStringLiteral("purpose"), QStringLiteral("session-vault")});
    if (!p.waitForStarted(3000) || !p.waitForFinished(10000) || p.exitCode() != 0)
        return fail(QStringLiteral("Secret Service lookup failed or secret-tool is unavailable."));
    QByteArray secret = p.readAllStandardOutput();
    while (secret.endsWith('\n') || secret.endsWith('\r'))
        secret.chop(1);
    const QString passphrase = QString::fromUtf8(secret);
    secret.fill('\0');
    if (passphrase.isEmpty())
        return fail(QStringLiteral("No FA3 session-vault secret found in Secret Service."));
    return openVault(passphrase);
}

bool SessionVaultService::unlockWithSecretFile(const QString &pathOrUrl)
{
    QFile f(localPath(pathOrUrl));
    if (!f.open(QIODevice::ReadOnly))
        return fail(QStringLiteral("Cannot open selected secret file."));
    QByteArray secret = f.read(4097);
    if (secret.size() > 4096)
        return fail(QStringLiteral("Secret file is unexpectedly large."));
    while (secret.endsWith('\n') || secret.endsWith('\r'))
        secret.chop(1);
    const QString passphrase = QString::fromUtf8(secret);
    secret.fill('\0');
    return openVault(passphrase);
}

bool SessionVaultService::storePassphraseInSecretService(const QString &passphrase)
{
    if (passphrase.isEmpty())
        return fail(QStringLiteral("Cannot store an empty vault secret."));
    QProcess p;
    p.start(QStringLiteral("secret-tool"),
            {QStringLiteral("store"), QStringLiteral("--label=FA3 Session Vault"),
             QStringLiteral("application"), QStringLiteral("FA3"),
             QStringLiteral("purpose"), QStringLiteral("session-vault")});
    if (!p.waitForStarted(3000))
        return fail(QStringLiteral("secret-tool is unavailable."));
    QByteArray secret = passphrase.toUtf8();
    secret.append('\n');
    p.write(secret);
    secret.fill('\0');
    p.closeWriteChannel();
    if (!p.waitForFinished(15000) || p.exitCode() != 0)
        return fail(QStringLiteral("Secret Service store failed."));
    clearError();
    m_statusText = m_unlocked ? QStringLiteral("UNLOCKED") : QStringLiteral("LOCKED");
    emit stateChanged();
    return true;
}

bool SessionVaultService::lock()
{
    clearError();
    bool ok = true;
    QString error;

    if (!m_clearObject.isEmpty()) {
        QDBusInterface filesystem(UDISKS_SERVICE, m_clearObject,
                                  "org.freedesktop.UDisks2.Filesystem", QDBusConnection::systemBus());
        QDBusMessage r = filesystem.call(QStringLiteral("Unmount"), QVariantMap{});
        if (r.type() == QDBusMessage::ErrorMessage) {
            ok = false;
            error = QStringLiteral("Vault unmount failed: ") + r.errorMessage();
        }
    }

    if (ok && !m_loopObject.isEmpty()) {
        QDBusInterface encrypted(UDISKS_SERVICE, m_loopObject,
                                 "org.freedesktop.UDisks2.Encrypted", QDBusConnection::systemBus());
        QDBusMessage r = encrypted.call(QStringLiteral("Lock"), QVariantMap{});
        if (r.type() == QDBusMessage::ErrorMessage) {
            ok = false;
            error = QStringLiteral("Vault lock failed: ") + r.errorMessage();
        }
    }

    if (ok && !m_loopObject.isEmpty()) {
        QDBusInterface loop(UDISKS_SERVICE, m_loopObject,
                            "org.freedesktop.UDisks2.Loop", QDBusConnection::systemBus());
        QDBusMessage r = loop.call(QStringLiteral("Delete"), QVariantMap{});
        if (r.type() == QDBusMessage::ErrorMessage) {
            ok = false;
            error = QStringLiteral("Loop cleanup failed: ") + r.errorMessage();
        }
    }

    if (!ok)
        return fail(error);

    QFile::remove(m_aliasPath);
    m_loopObject.clear();
    m_clearObject.clear();
    m_mountPath.clear();
    m_unlocked = false;
    m_statusText = configured() ? QStringLiteral("LOCKED") : QStringLiteral("NOT_CONFIGURED");
    emit stateChanged();
    return true;
}
