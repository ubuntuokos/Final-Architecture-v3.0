#include "ExternalLlmCatalogModel.h"

#include <QDir>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcessEnvironment>
#include <QSet>

namespace {
const QSet<QString> kAllowedStates = {
    QStringLiteral("DISCOVERED"),
    QStringLiteral("OBSERVED"),
    QStringLiteral("VERIFIED"),
    QStringLiteral("ADMITTED"),
    QStringLiteral("ENABLED"),
};

QString defaultCatalogPath()
{
    const auto env = QProcessEnvironment::systemEnvironment();
    const QString overridePath = env.value(QStringLiteral("FA3_EXTERNAL_LLM_CATALOG_PATH")).trimmed();
    if (!overridePath.isEmpty()) {
        return overridePath;
    }
    return QDir::homePath() + QStringLiteral("/.local/share/fa3/external-llm-catalog/catalog.json");
}

QVariantMap projectAllowedFields(const QJsonObject &row)
{
    QVariantMap out;
    const QString key = row.value(QStringLiteral("external_provider_key")).toString().trimmed();
    const QString name = row.value(QStringLiteral("provider_name")).toString().trimmed();
    const QString state = row.value(QStringLiteral("discovery_state")).toString().trimmed();

    if (key.isEmpty() || name.isEmpty() || !kAllowedStates.contains(state)) {
        return {};
    }

    out.insert(QStringLiteral("external_provider_key"), key);
    out.insert(QStringLiteral("provider_name"), name);
    out.insert(QStringLiteral("discovery_state"), state);
    out.insert(QStringLiteral("free_tier_kind"), row.value(QStringLiteral("free_tier_kind")).toString());
    out.insert(QStringLiteral("free_models"), row.value(QStringLiteral("free_models")).toVariant());
    out.insert(QStringLiteral("max_context"), row.value(QStringLiteral("max_context")).toString());
    out.insert(QStringLiteral("modalities"), row.value(QStringLiteral("modalities")).toArray().toVariantList());
    out.insert(QStringLiteral("registration_requirement"), row.value(QStringLiteral("registration_requirement")).toString());
    out.insert(QStringLiteral("base_url"), row.value(QStringLiteral("base_url")).toString());
    return out;
}
}

ExternalLlmCatalogModel::ExternalLlmCatalogModel(QObject *parent)
    : QObject(parent),
      m_catalogPath(defaultCatalogPath())
{
    reload();
}

QVariantList ExternalLlmCatalogModel::providers() const
{
    return m_providers;
}

QString ExternalLlmCatalogModel::status() const
{
    return m_status;
}

QString ExternalLlmCatalogModel::sourceCommit() const
{
    return m_sourceCommit;
}

QString ExternalLlmCatalogModel::catalogPath() const
{
    return m_catalogPath;
}

bool ExternalLlmCatalogModel::reload()
{
    m_providers.clear();
    m_sourceCommit.clear();

    QFile file(m_catalogPath);
    if (!file.exists()) {
        m_status = QStringLiteral("CATALOG_NOT_MATERIALIZED");
        emit catalogChanged();
        return false;
    }
    if (!file.open(QIODevice::ReadOnly)) {
        m_status = QStringLiteral("CATALOG_UNREADABLE_FAIL_CLOSED");
        emit catalogChanged();
        return false;
    }

    QJsonParseError error;
    const QJsonDocument doc = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject()) {
        m_status = QStringLiteral("CATALOG_INVALID_FAIL_CLOSED");
        emit catalogChanged();
        return false;
    }

    const QJsonObject root = doc.object();
    if (root.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.external-llm-runtime-catalog.v1")
        || root.value(QStringLiteral("canonical_policy")).toBool(true)
        || root.value(QStringLiteral("contains_secret_values")).toBool(true)) {
        m_status = QStringLiteral("CATALOG_POLICY_BOUNDARY_REJECTED");
        emit catalogChanged();
        return false;
    }

    const QJsonObject source = root.value(QStringLiteral("source")).toObject();
    const QString commit = source.value(QStringLiteral("commit")).toString();
    if (commit.size() != 40) {
        m_status = QStringLiteral("CATALOG_SOURCE_IDENTITY_REJECTED");
        emit catalogChanged();
        return false;
    }

    const QJsonArray rows = root.value(QStringLiteral("providers")).toArray();
    QVariantList projected;
    projected.reserve(rows.size());
    QSet<QString> seen;
    for (const QJsonValue &value : rows) {
        if (!value.isObject()) {
            m_status = QStringLiteral("CATALOG_ROW_REJECTED");
            emit catalogChanged();
            return false;
        }
        QVariantMap item = projectAllowedFields(value.toObject());
        const QString key = item.value(QStringLiteral("external_provider_key")).toString();
        if (item.isEmpty() || seen.contains(key)) {
            m_status = QStringLiteral("CATALOG_ROW_REJECTED");
            emit catalogChanged();
            return false;
        }
        seen.insert(key);
        projected.push_back(item);
    }

    m_providers = projected;
    m_sourceCommit = commit;
    m_status = QStringLiteral("DISCOVERY_CATALOG_LOADED_READ_ONLY");
    emit catalogChanged();
    return true;
}
