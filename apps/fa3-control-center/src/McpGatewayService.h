#pragma once

#include <QObject>
#include <functional>
#include <QVariantList>
#include <QVariantMap>

class QNetworkAccessManager;
class QNetworkReply;

class McpGatewayService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString state READ state NOTIFY stateChanged)
    Q_PROPERTY(QVariantMap health READ health NOTIFY healthChanged)
    Q_PROPERTY(QVariantMap readiness READ readiness NOTIFY readinessChanged)
    Q_PROPERTY(QVariantList capabilities READ capabilities NOTIFY capabilitiesChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

public:
    explicit McpGatewayService(QObject *parent = nullptr);

    QString state() const;
    QVariantMap health() const;
    QVariantMap readiness() const;
    QVariantList capabilities() const;
    QString lastError() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantList sections() const;
    Q_INVOKABLE QVariantMap canonicalSnapshot() const;

signals:
    void stateChanged();
    void healthChanged();
    void readinessChanged();
    void capabilitiesChanged();
    void lastErrorChanged();

private:
    void getJson(const QString &path, const std::function<void(const QVariantMap &)> &onSuccess);
    void setError(const QString &message);

    QNetworkAccessManager *m_network;
    QString m_state = QStringLiteral("UNVERIFIED");
    QVariantMap m_health;
    QVariantMap m_readiness;
    QVariantList m_capabilities;
    QString m_lastError;
};
