#include "SecretBrokerService.h"

#include <QCoreApplication>
#include <QProcessEnvironment>
#include <QSettings>

namespace {
QSettings metadataSettings()
{
    return QSettings();
}

const QStringList knownProviders{
    QStringLiteral("civitai"),
    QStringLiteral("huggingface"),
    QStringLiteral("generic")
};
}

SecretBrokerService::SecretBrokerService(QObject *parent)
    : QObject(parent)
{
    refreshStatus();
}

QString SecretBrokerService::normalizedProvider(const QString &providerId)
{
    QString value = providerId.trimmed().toLower();
    value.remove(QChar(' '));
    return value;
}

QString SecretBrokerService::envNameForProvider(const QString &providerId)
{
    const QString provider = normalizedProvider(providerId);
    if (provider == QStringLiteral("civitai"))
        return QStringLiteral("CIVITAI_API_TOKEN");
    if (provider == QStringLiteral("huggingface"))
        return QStringLiteral("HF_TOKEN");
    return QStringLiteral("FA3_PROVIDER_TOKEN_%1").arg(provider.toUpper());
}

QVariantList SecretBrokerService::backends() const
{
    return {
        QVariantMap{{"id", "SESSION_MEMORY"}, {"label", "Session memory"}, {"available", true}, {"persistent", false}},
        QVariantMap{{"id", "ENVIRONMENT_REFERENCE"}, {"label", "Environment reference"}, {"available", true}, {"persistent", false}},
        QVariantMap{{"id", "SYSTEMD_CREDENTIAL"}, {"label", "systemd credential reference"}, {"available", true}, {"persistent", false}},
        QVariantMap{{"id", "EXTERNAL_SECRETREF"}, {"label", "External SecretRef"}, {"available", true}, {"persistent", true}},
        QVariantMap{{"id", "OPENBAO"}, {"label", "OpenBao / external vault"}, {"available", false}, {"persistent", true}},
        QVariantMap{{"id", "OS_KEYCHAIN"}, {"label", "OS keychain / Secret Service"}, {"available", false}, {"persistent", true}},
        QVariantMap{{"id", "KWALLET"}, {"label", "KWallet (optional)"}, {"available", false}, {"persistent", true}, {"required", false}}
    };
}

QVariantMap SecretBrokerService::storedReference(const QString &providerId) const
{
    const QString provider = normalizedProvider(providerId);
    QSettings settings = metadataSettings();
    settings.beginGroup(QStringLiteral("credentialRefs/%1").arg(provider));
    QVariantMap result;
    result.insert(QStringLiteral("backend"), settings.value(QStringLiteral("backend")).toString());
    result.insert(QStringLiteral("referenceId"), settings.value(QStringLiteral("referenceId")).toString());
    result.insert(QStringLiteral("accountLabel"), settings.value(QStringLiteral("accountLabel")).toString());
    settings.endGroup();
    return result;
}

QVariantMap SecretBrokerService::credentialStatus(const QString &providerId) const
{
    const QString provider = normalizedProvider(providerId);
    const QVariantMap reference = storedReference(provider);
    const QString envName = envNameForProvider(provider);
    const bool session = m_sessionSecrets.contains(provider) && !m_sessionSecrets.value(provider).isEmpty();
    const bool environment = QProcessEnvironment::systemEnvironment().contains(envName);
    const QString backend = reference.value(QStringLiteral("backend")).toString();
    const QString referenceId = reference.value(QStringLiteral("referenceId")).toString();

    QVariantMap result;
    result.insert(QStringLiteral("providerId"), provider);
    result.insert(QStringLiteral("configured"), session || environment || !referenceId.isEmpty());
    result.insert(QStringLiteral("sessionSecret"), session);
    result.insert(QStringLiteral("environmentAvailable"), environment);
    result.insert(QStringLiteral("environmentName"), envName);
    result.insert(QStringLiteral("backend"), session ? QStringLiteral("SESSION_MEMORY")
                                  : environment ? QStringLiteral("ENVIRONMENT_REFERENCE")
                                                : backend);
    result.insert(QStringLiteral("referenceId"), referenceId);
    result.insert(QStringLiteral("accountLabel"), reference.value(QStringLiteral("accountLabel")));
    result.insert(QStringLiteral("kwalletRequired"), false);
    result.insert(QStringLiteral("secretValueExposed"), false);
    return result;
}

QVariantList SecretBrokerService::providers() const
{
    QVariantList rows;
    for (const QString &provider : knownProviders)
        rows.append(credentialStatus(provider));
    return rows;
}

bool SecretBrokerService::setSessionSecret(const QString &providerId, const QString &secretValue)
{
    const QString provider = normalizedProvider(providerId);
    const QByteArray secret = secretValue.toUtf8();
    if (provider.isEmpty() || secret.isEmpty())
        return false;
    m_sessionSecrets.insert(provider, secret);
    refreshStatus();
    emit changed();
    return true;
}

bool SecretBrokerService::clearSessionSecret(const QString &providerId)
{
    const QString provider = normalizedProvider(providerId);
    if (!m_sessionSecrets.contains(provider))
        return false;
    QByteArray value = m_sessionSecrets.take(provider);
    value.fill('\0');
    refreshStatus();
    emit changed();
    return true;
}

bool SecretBrokerService::configureReference(const QString &providerId,
                                             const QString &backend,
                                             const QString &referenceId,
                                             const QString &accountLabel)
{
    const QString provider = normalizedProvider(providerId);
    const QString backendId = backend.trimmed().toUpper();
    const QString ref = referenceId.trimmed();
    const QStringList allowed{
        QStringLiteral("ENVIRONMENT_REFERENCE"),
        QStringLiteral("SYSTEMD_CREDENTIAL"),
        QStringLiteral("EXTERNAL_SECRETREF"),
        QStringLiteral("OPENBAO"),
        QStringLiteral("OS_KEYCHAIN"),
        QStringLiteral("KWALLET")
    };
    if (provider.isEmpty() || ref.isEmpty() || !allowed.contains(backendId))
        return false;

    QSettings settings = metadataSettings();
    settings.beginGroup(QStringLiteral("credentialRefs/%1").arg(provider));
    settings.setValue(QStringLiteral("backend"), backendId);
    settings.setValue(QStringLiteral("referenceId"), ref);
    settings.setValue(QStringLiteral("accountLabel"), accountLabel.trimmed());
    settings.endGroup();
    settings.sync();
    refreshStatus();
    emit changed();
    return true;
}

bool SecretBrokerService::clearReference(const QString &providerId)
{
    const QString provider = normalizedProvider(providerId);
    QSettings settings = metadataSettings();
    settings.beginGroup(QStringLiteral("credentialRefs"));
    settings.remove(provider);
    settings.endGroup();
    settings.sync();
    refreshStatus();
    emit changed();
    return true;
}

QByteArray SecretBrokerService::resolveSecret(const QString &providerId) const
{
    const QString provider = normalizedProvider(providerId);
    if (m_sessionSecrets.contains(provider))
        return m_sessionSecrets.value(provider);

    const QString envName = envNameForProvider(provider);
    const QByteArray env = qgetenv(envName.toUtf8().constData());
    if (!env.isEmpty())
        return env;

    // External SecretRef, systemd credentials, OS keychain, OpenBao and optional KWallet
    // are references here. A backend adapter must resolve them without returning values to QML.
    return {};
}

void SecretBrokerService::refreshStatus()
{
    int configured = 0;
    for (const QString &provider : knownProviders) {
        if (credentialStatus(provider).value(QStringLiteral("configured")).toBool())
            ++configured;
    }
    m_statusText = QStringLiteral("provider-neutral SecretRef broker · %1 configured · KWallet optional").arg(configured);
}
