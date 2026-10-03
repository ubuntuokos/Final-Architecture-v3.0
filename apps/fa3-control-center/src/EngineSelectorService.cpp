#include "EngineSelectorService.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMap>
#include <QMetaType>
#include <algorithm>

namespace {
const QSet<QString> kScopes = {
    "GLOBAL", "APPLICATION", "WORKSPACE", "PROJECT", "SEQUENCE",
    "SCENE", "TRACK", "CLIP", "NODE", "TASK"
};
const QSet<QString> kFallbackModes = {"OFF", "ASK", "APPROVED_ONLY"};
const QSet<QString> kReadyHealth = {"READY", "AVAILABLE_CONDITIONAL"};
}

EngineSelectorService::EngineSelectorService(const QString &repoRoot, QObject *parent)
    : QObject(parent), m_repoRoot(QDir(repoRoot).absolutePath())
{
    refresh();
}

QVariantMap EngineSelectorService::readObject(const QString &relativePath) const
{
    QFile file(QDir(m_repoRoot).filePath(relativePath));
    if (!file.open(QIODevice::ReadOnly)) return {};
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) return {};
    return document.object().toVariantMap();
}

QVariant EngineSelectorService::resolvePointer(const QVariantMap &object, const QString &pointer) const
{
    QVariant current = object;
    for (const auto &part : pointer.split('.', Qt::SkipEmptyParts)) {
        const auto map = current.toMap();
        if (!map.contains(part)) return {};
        current = map.value(part);
    }
    return current;
}

QStringList EngineSelectorService::strings(const QVariant &value)
{
    QStringList out;
    if (value.metaType().id() == QMetaType::QStringList) return value.toStringList();
    if (value.metaType().id() == QMetaType::QVariantList) {
        for (const auto &row : value.toList()) {
            const auto text = row.toString().trimmed();
            if (!text.isEmpty()) out.append(text);
        }
        return out;
    }
    const auto text = value.toString().trimmed();
    if (!text.isEmpty()) out.append(text);
    return out;
}

QString EngineSelectorService::healthFromProvider(const QVariantMap &provider)
{
    const auto status = provider.value("status").toString().toUpper();
    if (status.contains("REFERENCE_ONLY")) return "REFERENCE_ONLY";
    if (status.contains("DISABLED") || status.contains("RETIRED")) return "DISABLED";
    const auto runtime = provider.value("runtime_activation").toMap();
    if (!runtime.isEmpty() && runtime.value("current_host_runtime_promotion_claimed").isValid()
        && !runtime.value("current_host_runtime_promotion_claimed").toBool()) {
        return "CURRENT_HOST_NOT_ADMITTED";
    }
    if (status.contains("PENDING") || status.contains("NOT_PROMOTED")) return "CURRENT_HOST_NOT_ADMITTED";
    return "AVAILABLE_CONDITIONAL";
}

QStringList EngineSelectorService::executionModes(const QVariantMap &provider, const QStringList &defaults)
{
    for (const auto &token : strings(provider.value("classification"))) {
        const auto upper = token.toUpper();
        if (upper.contains("REMOTE") || upper.contains("CLOUD")) return {"CLOUD"};
    }
    return defaults;
}

void EngineSelectorService::refresh()
{
    const auto registry = readObject("canonical/FA3-ENGINE-REGISTRY-001.json");
    QMap<QString, QVariantMap> catalog;

    for (const auto &value : registry.value("engine_records").toList()) {
        auto row = value.toMap();
        const auto id = row.value("engine_id").toString();
        if (!id.isEmpty()) catalog.insert(id, row);
    }

    for (const auto &ruleValue : registry.value("provider_projection_rules").toList()) {
        const auto rule = ruleValue.toMap();
        const auto source = readObject(rule.value("source").toString());
        const auto providerIds = strings(resolvePointer(source, rule.value("pointer").toString()));
        const auto classes = strings(rule.value("engine_classes"));
        const auto defaults = strings(rule.value("execution_mode_default"));

        for (const auto &providerId : providerIds) {
            const auto provider = readObject(QString("canonical/providers/%1.json").arg(providerId));
            if (provider.isEmpty() && rule.value("require_provider_record").toBool()) continue;

            QVariantMap row;
            const auto engineId = QString("FA3-ENGINE-PROJECTION::%1").arg(providerId);
            row.insert("engine_id", engineId);
            row.insert("name", provider.value("name", providerId));
            row.insert("implementation_kind", "CANONICAL_PROVIDER_PROJECTION");
            row.insert("engine_classes", classes);
            row.insert("capability_projection", strings(provider.value("capability_projection")));
            row.insert("execution_modes", executionModes(provider, defaults.isEmpty() ? QStringList{"UNSPECIFIED"} : defaults));
            row.insert("status", provider.value("status", "UNKNOWN"));
            row.insert("health_state", provider.isEmpty() ? "MISSING_PROVIDER_RECORD" : healthFromProvider(provider));
            row.insert("architectural_authority", false);
            row.insert("provider_record", providerId);
            row.insert("model_router_bound", !rule.value("provider_model_selection_authority").toString().isEmpty());
            row.insert("current_host_runtime_promotion_claim", false);
            catalog.insert(engineId, row);
        }
    }

    m_engines.clear();
    for (auto it = catalog.cbegin(); it != catalog.cend(); ++it) m_engines.append(it.value());
    std::sort(m_engines.begin(), m_engines.end(), [](const QVariant &left, const QVariant &right) {
        return left.toMap().value("name").toString().localeAwareCompare(
                   right.toMap().value("name").toString()) < 0;
    });
    m_lastRefresh = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
    emit catalogChanged();
}

QVariantList EngineSelectorService::filterEngines(const QString &query,
                                                   const QString &engineClass,
                                                   bool localAllowed,
                                                   bool lanAllowed,
                                                   bool cloudAllowed,
                                                   bool showUnavailable) const
{
    QVariantList out;
    const auto needle = query.trimmed();
    const auto wantedClass = engineClass.trimmed().toUpper();
    const bool modeFilter = localAllowed || lanAllowed || cloudAllowed;

    for (const auto &value : m_engines) {
        const auto row = value.toMap();
        const auto health = row.value("health_state").toString();
        if (!showUnavailable && !kReadyHealth.contains(health)) continue;

        const auto classes = strings(row.value("engine_classes"));
        if (!wantedClass.isEmpty() && wantedClass != "ALL" && !classes.contains(wantedClass)) continue;

        const auto modes = strings(row.value("execution_modes"));
        if (modeFilter) {
            const bool match =
                (localAllowed && modes.contains("LOCAL")) ||
                (lanAllowed && modes.contains("LAN")) ||
                (cloudAllowed && (modes.contains("CLOUD") || modes.contains("REMOTE") || modes.contains("HYBRID"))) ||
                (showUnavailable && modes.contains("UNSPECIFIED"));
            if (!match) continue;
        }

        const auto haystack = QString("%1 %2 %3 %4 %5")
            .arg(row.value("name").toString(),
                 row.value("engine_id").toString(),
                 classes.join(' '),
                 strings(row.value("capability_projection")).join(' '),
                 modes.join(' '));
        if (!needle.isEmpty() && !haystack.contains(needle, Qt::CaseInsensitive)) continue;
        out.append(row);
    }
    return out;
}

QVariantMap EngineSelectorService::engineById(const QString &engineId) const
{
    for (const auto &value : m_engines) {
        const auto row = value.toMap();
        if (row.value("engine_id").toString() == engineId) return row;
    }
    return {};
}

QVariantMap EngineSelectorService::prepareSelection(const QString &engineId,
                                                     const QString &scope,
                                                     const QString &fallbackMode) const
{
    QVariantMap out;
    out.insert("schema", "fa3.engine-selection-intent.v1");
    out.insert("execution_requested", false);
    out.insert("runtime_execution_allowed", false);

    const auto normalizedScope = scope.trimmed().toUpper();
    const auto normalizedFallback = fallbackMode.trimmed().toUpper();
    const auto engine = engineById(engineId);

    if (engine.isEmpty()) {
        out.insert("status", "REJECTED");
        out.insert("reason", "UNKNOWN_ENGINE");
        return out;
    }
    if (!kScopes.contains(normalizedScope)) {
        out.insert("status", "REJECTED");
        out.insert("reason", "INVALID_SCOPE");
        return out;
    }
    if (!kFallbackModes.contains(normalizedFallback)) {
        out.insert("status", "REJECTED");
        out.insert("reason", "INVALID_FALLBACK_MODE");
        return out;
    }

    QStringList approvedAlternates;
    if (normalizedFallback == "APPROVED_ONLY") {
        for (const auto &id : m_compareIds) {
            if (id != engineId && !engineById(id).isEmpty()) approvedAlternates.append(id);
        }
        approvedAlternates.sort();
        if (approvedAlternates.isEmpty()) {
            out.insert("status", "REJECTED");
            out.insert("reason", "APPROVED_ONLY_REQUIRES_SELECTED_ALTERNATES");
            return out;
        }
    }

    QVariantMap fallback;
    fallback.insert("mode", normalizedFallback);
    fallback.insert("approved_engine_ids", approvedAlternates);

    out.insert("status", "PREFERENCE_INTENT_READY");
    out.insert("scope", normalizedScope);
    out.insert("engine_id", engineId);
    out.insert("health_state", engine.value("health_state"));
    out.insert("execution_ready", engine.value("health_state").toString() == "READY");
    out.insert("fallback_policy", fallback);
    out.insert("implicit_substitution_allowed", false);
    out.insert("provider_model_routing_authority", "FA3-AUTH-MODEL-ROUTER-001");
    out.insert("resource_authority", "FA3-AUTH-HOST-RESOURCE-BROKER-001");
    out.insert("secret_authority", "FA3-AUTH-SECRETS-001");
    return out;
}

void EngineSelectorService::toggleCompare(const QString &engineId, bool enabled)
{
    if (enabled) {
        if (!engineById(engineId).isEmpty()) m_compareIds.insert(engineId);
    } else {
        m_compareIds.remove(engineId);
    }
}

QVariantList EngineSelectorService::prepareComparison() const
{
    QVariantList out;
    QStringList ids;
    for (const auto &id : m_compareIds) ids.append(id);
    ids.sort();
    for (const auto &id : ids) {
        const auto engine = engineById(id);
        if (engine.isEmpty()) continue;
        QVariantMap row;
        row.insert("engine_id", id);
        row.insert("name", engine.value("name"));
        row.insert("engine_classes", engine.value("engine_classes"));
        row.insert("capabilities", engine.value("capability_projection"));
        row.insert("execution_modes", engine.value("execution_modes"));
        row.insert("health_state", engine.value("health_state"));
        row.insert("implementation_kind", engine.value("implementation_kind"));
        row.insert("comparison_mode", "STATIC_METADATA_ONLY");
        out.append(row);
    }
    return out;
}
