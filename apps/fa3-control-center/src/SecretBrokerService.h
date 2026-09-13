#pragma once

#include <QObject>
#include <QHash>
#include <QVariantList>
#include <QVariantMap>

class SecretBrokerService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList providers READ providers NOTIFY changed)
    Q_PROPERTY(QVariantList backends READ backends CONSTANT)
    Q_PROPERTY(bool kwalletRequired READ kwalletRequired CONSTANT)
    Q_PROPERTY(QString statusText READ statusText NOTIFY changed)

public:
    explicit SecretBrokerService(QObject *parent = nullptr);

    QVariantList providers() const;
    QVariantList backends() const;
    bool kwalletRequired() const { return false; }
    QString statusText() const { return m_statusText; }

    Q_INVOKABLE QVariantMap credentialStatus(const QString &providerId) const;
    Q_INVOKABLE bool setSessionSecret(const QString &providerId, const QString &secretValue);
    Q_INVOKABLE bool clearSessionSecret(const QString &providerId);
    Q_INVOKABLE bool configureReference(const QString &providerId,
                                        const QString &backend,
                                        const QString &referenceId,
                                        const QString &accountLabel = QString());
    Q_INVOKABLE bool clearReference(const QString &providerId);

    // C++-only: never exposed to QML. Callers receive the value only for bounded request execution.
    QByteArray resolveSecret(const QString &providerId) const;

signals:
    void changed();

private:
    static QString normalizedProvider(const QString &providerId);
    static QString envNameForProvider(const QString &providerId);
    QVariantMap storedReference(const QString &providerId) const;
    void refreshStatus();

    QHash<QString, QByteArray> m_sessionSecrets;
    QString m_statusText;
};
