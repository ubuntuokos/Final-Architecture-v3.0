#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

#include <functional>

class QJsonObject;

class LlmfitClient final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool available READ available NOTIFY stateChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY stateChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY stateChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY stateChanged)
    Q_PROPERTY(QString socketPath READ socketPath CONSTANT)
    Q_PROPERTY(QVariantMap system READ system NOTIFY dataChanged)
    Q_PROPERTY(QVariantList models READ models NOTIFY dataChanged)
    Q_PROPERTY(QString useCase READ useCase NOTIFY filtersChanged)
    Q_PROPERTY(QString runtime READ runtime NOTIFY filtersChanged)
    Q_PROPERTY(int maxContext READ maxContext NOTIFY filtersChanged)

public:
    explicit LlmfitClient(QObject *parent = nullptr);

    bool available() const { return m_available; }
    bool busy() const { return m_busy; }
    QString statusText() const;
    QString lastError() const { return m_lastError; }
    QString socketPath() const { return m_socketPath; }
    QVariantMap system() const { return m_system; }
    QVariantList models() const { return m_models; }
    QString useCase() const { return m_useCase; }
    QString runtime() const { return m_runtime; }
    int maxContext() const { return m_maxContext; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE void recommendModels(const QString &useCase, const QString &runtime, int maxContext);

signals:
    void stateChanged();
    void dataChanged();
    void filtersChanged();

private:
    using JsonHandler = std::function<void(const QJsonObject &)>;

    void requestJson(const QString &path, JsonHandler handler);
    void requestSystem();
    void requestModels();
    void setBusy(bool busy);
    void setError(const QString &message);

    bool m_available = false;
    bool m_busy = false;
    QString m_lastError;
    QString m_socketPath;
    QVariantMap m_system;
    QVariantList m_models;
    QString m_useCase = "general";
    QString m_runtime = "any";
    int m_maxContext = 8192;
};
