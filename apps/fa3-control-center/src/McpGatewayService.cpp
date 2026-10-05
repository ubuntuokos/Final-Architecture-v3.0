#include "McpGatewayService.h"

#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>

McpGatewayService::McpGatewayService(QObject *parent)
    : QObject(parent),
      m_network(new QNetworkAccessManager(this))
{
}

QString McpGatewayService::state() const { return m_state; }
QVariantMap McpGatewayService::health() const { return m_health; }
QVariantMap McpGatewayService::readiness() const { return m_readiness; }
QVariantList McpGatewayService::capabilities() const { return m_capabilities; }
QString McpGatewayService::lastError() const { return m_lastError; }

QVariantList McpGatewayService::sections() const
{
    return {
        QStringLiteral("Overview"), QStringLiteral("Servers"), QStringLiteral("Tools"),
        QStringLiteral("Providers"), QStringLiteral("Capabilities"), QStringLiteral("Routes"),
        QStringLiteral("Requests"), QStringLiteral("Permissions"), QStringLiteral("Security"),
        QStringLiteral("Logs"), QStringLiteral("MCP Inspector"), QStringLiteral("Settings")
    };
}

QVariantMap McpGatewayService::canonicalSnapshot() const
{
    return {
        {QStringLiteral("profile"), QStringLiteral("FA3-MCP-GATEWAY-001")},
        {QStringLiteral("authority"), QStringLiteral("FA3-AUTH-MCP-GATEWAY-001")},
        {QStringLiteral("protocol"), QStringLiteral("MCP 2026-07-28")},
        {QStringLiteral("transport"), QStringLiteral("STATELESS")},
        {QStringLiteral("endpoint"), QStringLiteral("http://127.0.0.1:18790/mcp")},
        {QStringLiteral("currentHostProfile"), QStringLiteral("FA3-MCP-CURRENT-HOST-001")},
        {QStringLiteral("directQmlExecutionAllowed"), false},
        {QStringLiteral("guiSelfApprovalAllowed"), false},
        {QStringLiteral("runtimePromotion"), QStringLiteral("EVIDENCE-GATED")}
    };
}

void McpGatewayService::setError(const QString &message)
{
    m_lastError = message;
    m_state = QStringLiteral("UNREACHABLE_OR_UNVERIFIED");
    emit lastErrorChanged();
    emit stateChanged();
}

void McpGatewayService::getJson(const QString &path, const std::function<void(const QVariantMap &)> &onSuccess)
{
    QNetworkRequest request(QUrl(QStringLiteral("http://127.0.0.1:18790") + path));
    request.setRawHeader("Accept", "application/json");
    QNetworkReply *reply = m_network->get(request);
    connect(reply, &QNetworkReply::finished, this, [this, reply, path, onSuccess]() {
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        const QByteArray raw = reply->readAll();
        QJsonParseError error;
        const QJsonDocument doc = QJsonDocument::fromJson(raw, &error);
        const bool expectedNotReady = path == QStringLiteral("/readyz") && status == 503;
        if ((!expectedNotReady && reply->error() != QNetworkReply::NoError) ||
            error.error != QJsonParseError::NoError || !doc.isObject()) {
            setError(reply->error() == QNetworkReply::NoError
                ? QStringLiteral("Invalid gateway JSON response")
                : reply->errorString());
            reply->deleteLater();
            return;
        }
        onSuccess(doc.object().toVariantMap());
        reply->deleteLater();
    });
}

void McpGatewayService::refresh()
{
    m_lastError.clear();
    emit lastErrorChanged();
    getJson(QStringLiteral("/healthz"), [this](const QVariantMap &value) {
        m_health = value;
        emit healthChanged();
        m_state = value.value(QStringLiteral("status")).toString() == QStringLiteral("ok")
            ? QStringLiteral("HEALTHY_NOT_YET_ADMISSION_EQUIVALENT")
            : QStringLiteral("UNVERIFIED");
        emit stateChanged();
    });
    getJson(QStringLiteral("/readyz"), [this](const QVariantMap &value) {
        m_readiness = value;
        emit readinessChanged();
    });
    getJson(QStringLiteral("/capabilities"), [this](const QVariantMap &value) {
        m_capabilities = value.value(QStringLiteral("capabilities")).toList();
        emit capabilitiesChanged();
    });
}
