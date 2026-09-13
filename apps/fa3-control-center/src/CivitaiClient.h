#pragma once

#include <QObject>
#include <QVariantList>

class QNetworkAccessManager;
class SecretBrokerService;

class CivitaiClient final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool busy READ busy NOTIFY changed)
    Q_PROPERTY(QString statusText READ statusText NOTIFY changed)
    Q_PROPERTY(QString errorText READ errorText NOTIFY changed)
    Q_PROPERTY(QVariantList models READ models NOTIFY changed)

public:
    explicit CivitaiClient(SecretBrokerService *broker, QObject *parent = nullptr);

    bool busy() const { return m_busy; }
    QString statusText() const;
    QString errorText() const { return m_errorText; }
    QVariantList models() const { return m_models; }

    Q_INVOKABLE void searchModels(const QString &query);

signals:
    void changed();

private:
    SecretBrokerService *m_broker = nullptr;
    QNetworkAccessManager *m_network = nullptr;
    bool m_busy = false;
    QString m_errorText;
    QVariantList m_models;
};
