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

QStringList EngineSelectorService::flattenStrings(const QVariant &value)
{
    QStringList out;
    if (!value.isValid() || value.isNull()) return out;
    if (value.metaType().id() == QMetaType::QVariantMap) {
        const auto map=value.toMap();
        for (auto it=map.cbegin(); it!=map.cend(); ++it) out.append(flattenStrings(it.value()));
        return out;
    }
    if (value.metaType().id() == QMetaType::QVariantList) {
        for (const auto &row : value.toList()) out.append(flattenStrings(row));
        return out;
    }
    if (value.metaType().id() == QMetaType::Bool) {
        out.append(value.toBool() ? "TRUE" : "FALSE");
        return out;
    }
    const auto text=value.toString().trimmed();
    if (!text.isEmpty()) out.append(text);
    return out;
}

QStringList EngineSelectorService::providerCapabilities(const QVariantMap &provider)
{
    QSet<QString> values;
    for (const auto &key : {"capability_projection","capability_bindings","capabilities"}) {
        for (const auto &value : flattenStrings(provider.value(key))) {
            if (value.startsWith("CAP-")) values.insert(value);
        }
    }
    QStringList out;
    for (const auto &value : values) out.append(value);
    out.sort();
    return out;
}

bool EngineSelectorService::selectableHealth(const QString &health)
{
    return health == "READY" || health == "AVAILABLE_CONDITIONAL";
}

QString EngineSelectorService::healthFromProvider(const QVariantMap &provider)
{
    QStringList tokens;
    for (const auto &key : {
             "status","runtime_activation_status","runtime_admission",
             "activation_mode","activation","runtime_activation","license_admission"}) {
        tokens.append(flattenStrings(provider.value(key)));
    }
    const auto text=tokens.join(' ').toUpper();
    const auto activation=provider.value("activation").toMap();
    const auto runtime=provider.value("runtime_activation").toMap();
    const auto runtimeAdmission=provider.value("runtime_admission").toMap();

    if (text.contains("SECURITY_BLOCKED") || text.contains("SECURITY_DENIED")) return "SECURITY_BLOCKED";
    if (text.contains("LICENSE_BLOCKED") || text.contains("LICENSE_DENIED")) return "LICENSE_BLOCKED";
    if (text.contains("NOT_ADMITTED") || text.contains("REFERENCE_ONLY")
        || text.contains("ACCEPTED_REFERENCE") || text.contains("REFERENCE_NOT_PRODUCTION")) {
        return "REFERENCE_ONLY";
    }
    if (text.contains("DISABLED") || text.contains("RETIRED")) return "DISABLED";
    if (activation.value("production_admitted").isValid() && activation.value("production_admitted").toBool()) return "READY";
    if (runtime.value("current_host_runtime_promotion_claimed").isValid()
        && runtime.value("current_host_runtime_promotion_claimed").toBool()) return "READY";
    if (runtimeAdmission.value("current_host_runtime_promotion_claim").isValid()
        && runtimeAdmission.value("current_host_runtime_promotion_claim").toBool()) return "READY";
    if (text.contains("CURRENT_HOST_PASS")
        || (text.contains("PRODUCTION_ADMITTED") && !text.contains("NOT_PRODUCTION_ADMITTED"))) return "READY";
    return "CURRENT_HOST_NOT_ADMITTED";
}

QStringList EngineSelectorService::executionModes(const QVariantMap &provider, const QStringList &defaults)
{
    QStringList tokens;
    for (const auto &key : {"execution_modes","execution_topologies","classification"})
        tokens.append(flattenStrings(provider.value(key)));

    QSet<QString> modes;
    for (const auto &token : tokens) {
        const auto upper=token.toUpper();
        if (upper.contains("LOCAL")) modes.insert("LOCAL");
        if (upper.contains("LAN")) modes.insert("LAN");
        if (upper.contains("REMOTE")) modes.insert("REMOTE");
        if (upper.contains("CLOUD")) modes.insert("CLOUD");
        if (upper.contains("HYBRID")) modes.insert("HYBRID");
    }
    if (modes.isEmpty()) return defaults;
    QStringList out;
    for (const auto &mode : modes) out.append(mode);
    out.sort();
    return out;
}

void EngineSelectorService::refresh()
{
    const auto registry = readObject("canonical/FA3-ENGINE-REGISTRY-001.json");
    QMap<QString, QVariantMap> catalog;
    QMap<QString, QString> explicitProviderEngines;

    for (const auto &value : registry.value("engine_records").toList()) {
        auto row = value.toMap();
        const auto id = row.value("engine_id").toString();
        if (id.isEmpty()) continue;
        catalog.insert(id, row);
        const auto providerId=row.value("provider_record").toString();
        if (!providerId.isEmpty()) explicitProviderEngines.insert(providerId,id);
    }

    for (const auto &ruleValue : registry.value("provider_projection_rules").toList()) {
        const auto rule = ruleValue.toMap();
        const auto source = readObject(rule.value("source").toString());
        const auto providerIds = strings(resolvePointer(source, rule.value("pointer").toString()));
        const auto classes = strings(rule.value("engine_classes"));
        const auto defaults = strings(rule.value("execution_mode_default"));

        for (const auto &providerId : providerIds) {
            if (explicitProviderEngines.contains(providerId)) continue;
            const auto provider = readObject(QString("canonical/providers/%1.json").arg(providerId));

            QVariantMap row;
            const auto engineId = QString("FA3-ENGINE-PROJECTION::%1").arg(providerId);
            row.insert("engine_id", engineId);
            row.insert("name", provider.value("name", providerId));
            row.insert("implementation_kind", "CANONICAL_PROVIDER_PROJECTION");
            row.insert("engine_classes", classes);
            row.insert("capability_projection", providerCapabilities(provider));
            row.insert("execution_modes", executionModes(provider, defaults.isEmpty() ? QStringList{"UNSPECIFIED"} : defaults));
            row.insert("status", provider.isEmpty() ? "MISSING_PROVIDER_RECORD" : provider.value("status", "UNKNOWN"));
            row.insert("health_state", provider.isEmpty() ? "MISSING_PROVIDER_RECORD" : healthFromProvider(provider));
            row.insert("architectural_authority", false);
            row.insert("provider_record", providerId);
            row.insert("model_router_bound", !rule.value("provider_model_selection_authority").toString().isEmpty());
            row.insert("current_host_runtime_promotion_claim", false);
            row.insert("required_provider_record_missing", provider.isEmpty() && rule.value("require_provider_record").toBool());
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
        if (!showUnavailable && !selectableHealth(health)) continue;

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

QVariantMap EngineSelectorService::compatibilityReport(const QString &engineId,
                                                        const QVariantList &requiredCapabilities) const
{
    QVariantMap out;
    out.insert("schema", "fa3.engine-compatibility-report.v1");
    out.insert("engine_id", engineId);
    const auto engine=engineById(engineId);
    if (engine.isEmpty()) {
        out.insert("grade","UNSUPPORTED");
        out.insert("execution_eligible",false);
        out.insert("reason","UNKNOWN_ENGINE");
        return out;
    }

    const QSet<QString> required(strings(requiredCapabilities).cbegin(), strings(requiredCapabilities).cend());
    const auto declaredList=strings(engine.value("capability_projection"));
    const QSet<QString> declared(declaredList.cbegin(),declaredList.cend());
    QStringList supported;
    QStringList missing;
    for (const auto &cap : required) {
        if (declared.contains(cap)) supported.append(cap);
        else missing.append(cap);
    }
    supported.sort();
    missing.sort();

    QString grade;
    if (required.isEmpty() || missing.isEmpty()) grade="NATIVE";
    else if (!supported.isEmpty()) grade="PARTIAL";
    else grade="UNSUPPORTED";

    out.insert("required_capabilities", strings(requiredCapabilities));
    out.insert("supported_capabilities", supported);
    out.insert("missing_capabilities", missing);
    out.insert("grade",grade);
    out.insert("execution_eligible",selectableHealth(engine.value("health_state").toString()));
    out.insert("health_state",engine.value("health_state"));
    out.insert("evidence_semantics","DECLARED_CAPABILITY_PROJECTION_ONLY");
    out.insert("unproven_grade_escalation",false);
    return out;
}

QVariantMap EngineSelectorService::prepareSelection(const QString &engineId,
                                                     const QString &scope,
                                                     const QString &scopeTargetId,
                                                     const QVariantList &requiredCapabilities,
                                                     const QString &fallbackMode) const
{
    QVariantMap out;
    out.insert("schema", "fa3.engine-selection-intent.v1");
    out.insert("execution_requested", false);
    out.insert("runtime_execution_allowed", false);

    const auto normalizedScope = scope.trimmed().toUpper();
    const auto normalizedFallback = fallbackMode.trimmed().toUpper();
    auto normalizedTarget=scopeTargetId.trimmed();
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
    if (normalizedScope=="GLOBAL") normalizedTarget="GLOBAL";
    else if (normalizedTarget.isEmpty()) {
        out.insert("status","REJECTED");
        out.insert("reason","SCOPE_TARGET_REQUIRED");
        return out;
    }
    if (!kFallbackModes.contains(normalizedFallback)) {
        out.insert("status", "REJECTED");
        out.insert("reason", "INVALID_FALLBACK_MODE");
        return out;
    }
    if (!selectableHealth(engine.value("health_state").toString())) {
        out.insert("status","REJECTED");
        out.insert("reason","ENGINE_NOT_EXECUTION_ELIGIBLE");
        return out;
    }

    const auto required=strings(requiredCapabilities);
    const auto declared=strings(engine.value("capability_projection"));
    for (const auto &cap : required) {
        if (!declared.contains(cap)) {
            out.insert("status","REJECTED");
            out.insert("reason","REQUIRED_CAPABILITY_MISSING");
            out.insert("missing_capability",cap);
            return out;
        }
    }

    QStringList approvedAlternates;
    if (normalizedFallback == "APPROVED_ONLY") {
        for (const auto &id : m_compareIds) {
            if (id == engineId) continue;
            const auto candidate=engineById(id);
            if (candidate.isEmpty() || !selectableHealth(candidate.value("health_state").toString())) continue;
            const auto candidateCaps=strings(candidate.value("capability_projection"));
            bool compatible=true;
            for (const auto &cap : required) if (!candidateCaps.contains(cap)) compatible=false;
            if (compatible) approvedAlternates.append(id);
        }
        approvedAlternates.sort();
        if (approvedAlternates.isEmpty()) {
            out.insert("status", "REJECTED");
            out.insert("reason", "APPROVED_ONLY_REQUIRES_SELECTED_ELIGIBLE_ALTERNATES");
            return out;
        }
    }

    QVariantMap fallback;
    fallback.insert("mode", normalizedFallback);
    fallback.insert("approved_engine_ids", approvedAlternates);

    out.insert("status", "PREFERENCE_INTENT_READY");
    out.insert("scope", normalizedScope);
    out.insert("scope_target_id",normalizedTarget);
    out.insert("engine_id", engineId);
    out.insert("required_capabilities", required);
    out.insert("compatibility",compatibilityReport(engineId,requiredCapabilities));
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

QVariantList EngineSelectorService::prepareComparison(const QVariantList &requiredCapabilities) const
{
    QVariantList out;
    QStringList ids;
    for (const auto &id : m_compareIds) ids.append(id);
    ids.sort();
    for (const auto &id : ids) {
        const auto engine = engineById(id);
        if (engine.isEmpty()) continue;
        const auto compatibility=compatibilityReport(id,requiredCapabilities);
        QVariantMap row;
        row.insert("engine_id", id);
        row.insert("name", engine.value("name"));
        row.insert("engine_classes", engine.value("engine_classes"));
        row.insert("capabilities", engine.value("capability_projection"));
        row.insert("execution_modes", engine.value("execution_modes"));
        row.insert("health_state", engine.value("health_state"));
        row.insert("implementation_kind", engine.value("implementation_kind"));
        row.insert("compatibility_grade",compatibility.value("grade"));
        row.insert("compatibility",compatibility);
        row.insert("comparison_mode", "STATIC_METADATA_ONLY");
        out.append(row);
    }
    return out;
}
