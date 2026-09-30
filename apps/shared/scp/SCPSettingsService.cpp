#include "SCPSettingsService.h"

#include <QDateTime>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUuid>

SCPSettingsService::SCPSettingsService(QObject *parent)
    : QObject(parent)
{
    refresh();
}

QString SCPSettingsService::fabricState() const
{
    return m_fabricState;
}

QVariantList SCPSettingsService::components() const
{
    return m_components;
}

QVariantList SCPSettingsService::policyLayers() const
{
    return {
        QVariantMap{{"id", "GLOBAL"}, {"label", "Global policy"}, {"locked", true}},
        QVariantMap{{"id", "HOST"}, {"label", "Host policy"}, {"locked", true}},
        QVariantMap{{"id", "USER_ROLE"}, {"label", "User / role"}, {"locked", true}},
        QVariantMap{{"id", "PROJECT"}, {"label", "Project"}, {"locked", false}},
        QVariantMap{{"id", "APPLICATION"}, {"label", "Application"}, {"locked", false}},
        QVariantMap{{"id", "MODULE_PLUGIN"}, {"label", "Module / plugin"}, {"locked", false}},
        QVariantMap{{"id", "CAPABILITY"}, {"label", "Capability"}, {"locked", false}}
    };
}

QString SCPSettingsService::lastDraftPath() const
{
    return m_lastDraftPath;
}

QVariantMap SCPSettingsService::componentRow(const QString &name,
                                             const QString &role,
                                             const QStringList &executables,
                                             bool mandatory) const
{
    QString discovered;
    for (const auto &candidate : executables) {
        const auto path = QStandardPaths::findExecutable(candidate);
        if (!path.isEmpty()) {
            discovered = path;
            break;
        }
    }

    return {
        {"name", name},
        {"role", role},
        {"mandatory", mandatory},
        {"discoveredPath", discovered},
        {"state", discovered.isEmpty() ? "UNAVAILABLE" : "DISCOVERED_NOT_ADMITTED"}
    };
}

void SCPSettingsService::refresh()
{
    m_fabricState = QStringLiteral("STATIC_UI_READY_RUNTIME_PENDING");
    m_components = {
        componentRow("step-ca", "Trust / PKI", {"step-ca"}, true),
        componentRow("Envoy", "L4/L7 enforcement adapter", {"envoy"}, false),
        componentRow("SPIRE Agent", "Workload identity adapter", {"spire-agent"}, false),
        componentRow("OPA", "Contextual policy evaluator", {"opa"}, false),
        componentRow("nftables", "Generic Linux firewall", {"nft"}, true),
        componentRow("WireGuard", "Multi-host encryption", {"wg"}, false),
        componentRow("Falco", "Runtime sensor", {"falco"}, false),
        componentRow("Tetragon", "eBPF runtime enforcement", {"tetragon"}, false),
        componentRow("Cilium", "Advanced cluster network adapter", {"cilium"}, false),
        componentRow("Suricata", "IDS / IPS", {"suricata"}, false),
        componentRow("Trivy", "Supply-chain scanner", {"trivy"}, false),
        componentRow("Cosign", "Artifact signature verifier", {"cosign"}, false),
        componentRow("ClamAV", "Malware scanner", {"clamscan", "clamdscan"}, false),
        componentRow("YARA", "Threat-pattern scanner", {"yara", "yr"}, false),
        componentRow("bubblewrap", "Untrusted first-load sandbox", {"bwrap"}, false),
        componentRow("OpenTelemetry Collector", "Telemetry transport", {"otelcol", "otelcol-contrib"}, false)
    };
    emit stateChanged();
}

QVariantMap SCPSettingsService::evaluateRequest(const QVariantMap &context) const
{
    static const QStringList required = {
        "authenticated_source",
        "authenticated_destination",
        "trusted_host",
        "valid_layer",
        "valid_scope",
        "valid_capability",
        "valid_security_state",
        "destination_allowed"
    };

    QStringList reasons;
    for (const auto &key : required) {
        if (!context.value(key, false).toBool()) {
            reasons << QStringLiteral("MISSING_OR_FALSE:") + key;
        }
    }

    const QString trafficClass = context.value("traffic_class").toString();
    const bool external = trafficClass == "EXTERNAL_EGRESS" || trafficClass == "EXTERNAL_INGRESS";
    if (external && !context.value("external_permission", false).toBool()) {
        reasons << QStringLiteral("EXTERNAL_PERMISSION_REQUIRED");
    }

    if (context.value("ai_request", false).toBool()) {
        for (const auto &key : {"ai_enabled", "provider_admitted", "model_route_approved"}) {
            if (!context.value(key, false).toBool()) {
                reasons << QStringLiteral("AI_POLICY_DENY:") + key;
            }
        }
    }

    const bool allowed = reasons.isEmpty();
    return {
        {"allowed", allowed},
        {"decision", allowed ? "ALLOW" : "DENY"},
        {"reasons", reasons}
    };
}

QString SCPSettingsService::createDraftChange(const QString &scope,
                                              const QString &key,
                                              const QVariant &value)
{
    if (scope.trimmed().isEmpty() || key.trimmed().isEmpty()) {
        return {};
    }

    const QString root = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation)
        + QStringLiteral("/fa3/scp/drafts");
    QDir().mkpath(root);

    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QString path = root + QStringLiteral("/scp-draft-") + id + QStringLiteral(".json");

    QJsonObject doc{
        {"schema", "fa3.scp-draft-change.v1"},
        {"id", id},
        {"status", "DRAFT_NOT_SUBMITTED"},
        {"created_at", QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {"scope", scope},
        {"key", key},
        {"value", QJsonValue::fromVariant(value)},
        {"authority", false},
        {"direct_execution", false},
        {"approval_required", true}
    };

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return {};
    }
    file.write(QJsonDocument(doc).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        return {};
    }

    m_lastDraftPath = path;
    emit draftCreated();
    return path;
}
