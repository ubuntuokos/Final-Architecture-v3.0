#include "CivitaiClient.h"
#include "SecretBrokerService.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QUrlQuery>

CivitaiClient::CivitaiClient(SecretBrokerService *broker, QObject *parent)
    : QObject(parent), m_broker(broker), m_network(new QNetworkAccessManager(this))
{
}

QString CivitaiClient::statusText() const
{
    if (m_busy) return QStringLiteral("LOADING");
    if (!m_errorText.isEmpty()) return QStringLiteral("ERROR");
    return m_models.isEmpty() ? QStringLiteral("READY") : QStringLiteral("LOADED");
}

void CivitaiClient::searchModels(const QString &queryText)
{
    if (m_busy) return;
    m_busy = true;
    m_errorText.clear();
    emit changed();

    QUrl url(QStringLiteral("https://civitai.com/api/v1/models"));
    QUrlQuery query;
    if (!queryText.trimmed().isEmpty()) query.addQueryItem(QStringLiteral("query"), queryText.trimmed());
    query.addQueryItem(QStringLiteral("limit"), QStringLiteral("24"));
    url.setQuery(query);

    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("FA3-Control-Center/0.4 CivitAI-Provider"));
    request.setRawHeader("Accept", "application/json");
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);

    QByteArray token = m_broker ? m_broker->resolveSecret(QStringLiteral("civitai")) : QByteArray();
    if (!token.isEmpty()) request.setRawHeader("Authorization", QByteArray("Bearer ") + token);
    if (!token.isEmpty()) token.fill('\0');

    QNetworkReply *reply = m_network->get(request);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        const QByteArray payload = reply->readAll();
        m_busy = false;
        if (reply->error() != QNetworkReply::NoError) {
            m_errorText = reply->errorString();
            emit changed();
            reply->deleteLater();
            return;
        }

        QJsonParseError parseError;
        const QJsonDocument doc = QJsonDocument::fromJson(payload, &parseError);
        if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
            m_errorText = QStringLiteral("INVALID_CIVITAI_JSON");
            emit changed();
            reply->deleteLater();
            return;
        }

        QVariantList next;
        const QJsonArray items = doc.object().value(QStringLiteral("items")).toArray();
        for (const QJsonValue &itemValue : items) {
            const QJsonObject item = itemValue.toObject();
            const QJsonObject creator = item.value(QStringLiteral("creator")).toObject();
            const QJsonArray versions = item.value(QStringLiteral("modelVersions")).toArray();
            const QJsonObject version = versions.isEmpty() ? QJsonObject() : versions.first().toObject();
            const QJsonArray files = version.value(QStringLiteral("files")).toArray();
            const QJsonObject file = files.isEmpty() ? QJsonObject() : files.first().toObject();
            const QJsonObject hashes = file.value(QStringLiteral("hashes")).toObject();

            QVariantMap row;
            row.insert(QStringLiteral("id"), QString::number(item.value(QStringLiteral("id")).toVariant().toLongLong()));
            row.insert(QStringLiteral("name"), item.value(QStringLiteral("name")).toString());
            row.insert(QStringLiteral("type"), item.value(QStringLiteral("type")).toString());
            row.insert(QStringLiteral("creator"), creator.value(QStringLiteral("username")).toString());
            row.insert(QStringLiteral("versionId"), QString::number(version.value(QStringLiteral("id")).toVariant().toLongLong()));
            row.insert(QStringLiteral("versionName"), version.value(QStringLiteral("name")).toString());
            row.insert(QStringLiteral("fileName"), file.value(QStringLiteral("name")).toString());
            row.insert(QStringLiteral("downloadUrl"), file.value(QStringLiteral("downloadUrl")).toString());
            row.insert(QStringLiteral("sha256"), hashes.value(QStringLiteral("SHA256")).toString().toLower());
            row.insert(QStringLiteral("sizeKB"), file.value(QStringLiteral("sizeKB")).toDouble());
            row.insert(QStringLiteral("pickleScanResult"), file.value(QStringLiteral("pickleScanResult")).toString());
            row.insert(QStringLiteral("virusScanResult"), file.value(QStringLiteral("virusScanResult")).toString());
            next.push_back(row);
        }
        m_models = next;
        m_errorText.clear();
        emit changed();
        reply->deleteLater();
    });
}
