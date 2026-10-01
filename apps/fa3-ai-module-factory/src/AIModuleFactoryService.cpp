// SPDX-License-Identifier: Apache-2.0
#include "AIModuleFactoryService.h"

#include <QDateTime>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUuid>

namespace {
const QString kCapability = QStringLiteral("CAP-095");
const QString kKnowledgeProfile = QStringLiteral("FA3-SHARED-KNOWLEDGE-RETRIEVAL-001");
const QString kModelRouter = QStringLiteral("FA3-AUTH-MODEL-ROUTER-001");
const QString kHrb = QStringLiteral("FA3-AUTH-HOST-RESOURCE-BROKER-001");
const QString kRights = QStringLiteral("FA3-LICENSE-RIGHTS-001");
const QString kEvidence = QStringLiteral("FA3-AUTH-OBS-EVIDENCE-001");
}

AIModuleFactoryService::AIModuleFactoryService(QObject *parent)
    : QObject(parent)
{
}

QString AIModuleFactoryService::fabricState() const
{
    return QStringLiteral("STATIC_APP_MATERIALIZED_RUNTIME_HANDOFF_PENDING");
}

QVariantList AIModuleFactoryService::moduleTypes() const
{
    return {
        QVariantMap{{"id","KNOWLEDGE"},{"label","Knowledge / RAG"},{"trainingRequired",false}},
        QVariantMap{{"id","PREFERENCE"},{"label","Preference profile"},{"trainingRequired",true}},
        QVariantMap{{"id","SKILL_ADAPTER"},{"label","Skill adapter / LoRA"},{"trainingRequired",true}},
        QVariantMap{{"id","WORKFLOW"},{"label","Workflow module"},{"trainingRequired",true}},
        QVariantMap{{"id","NATIVE_MODEL"},{"label","Native AI model"},{"trainingRequired",true}}
    };
}

QVariantList AIModuleFactoryService::sourceApplications() const
{
    return {
        QVariantMap{{"id","fa3.video-editor"},{"label","FA3 Video Editor"}},
        QVariantMap{{"id","fa3.quickclip"},{"label","FA3 QuickClip"}},
        QVariantMap{{"id","fa3.story-screenplay"},{"label","FA3 Story / Screenplay"}},
        QVariantMap{{"id","fa3.music-studio"},{"label","FA3 Music Studio"}},
        QVariantMap{{"id","fa3.character-studio"},{"label","FA3 Character Studio"}}
    };
}

QVariantMap AIModuleFactoryService::lastPlan() const
{
    return m_lastPlan;
}

QString AIModuleFactoryService::lastDraftPath() const
{
    return m_lastDraftPath;
}

bool AIModuleFactoryService::supportedModuleType(const QString &moduleType)
{
    return moduleType == "KNOWLEDGE" || moduleType == "PREFERENCE"
        || moduleType == "SKILL_ADAPTER" || moduleType == "WORKFLOW"
        || moduleType == "NATIVE_MODEL";
}

bool AIModuleFactoryService::trainingRequired(const QString &moduleType)
{
    return moduleType != "KNOWLEDGE";
}

QString AIModuleFactoryService::safeName(QString value)
{
    value = value.trimmed();
    value.replace('/', '_');
    value.replace('\\', '_');
    return value;
}

QVariantMap AIModuleFactoryService::qualifyArtifact(const QVariantMap &artifact,
                                                    const QString &moduleType) const
{
    QVariantList reasons;
    if (!supportedModuleType(moduleType))
        reasons << QStringLiteral("UNSUPPORTED_MODULE_TYPE");
    if (artifact.value("artifact_id").toString().trimmed().isEmpty())
        reasons << QStringLiteral("MISSING_ARTIFACT_ID");
    if (artifact.value("source_application").toString().trimmed().isEmpty())
        reasons << QStringLiteral("MISSING_SOURCE_APPLICATION");
    if (!artifact.value("approved_final").toBool())
        reasons << QStringLiteral("NOT_HUMAN_APPROVED_FINAL");
    if (artifact.value("provenance_status").toString() != "VERIFIED")
        reasons << QStringLiteral("PROVENANCE_NOT_VERIFIED");
    if (artifact.value("use_rights").toString() != "ALLOWED")
        reasons << QStringLiteral("USE_RIGHTS_NOT_ALLOWED");

    const QString scope = artifact.value("consent_scope").toString();
    if (scope != "PRIVATE" && scope != "PROJECT" && scope != "SHARED")
        reasons << QStringLiteral("INVALID_CONSENT_SCOPE");

    if (trainingRequired(moduleType)) {
        if (artifact.value("training_rights").toString() != "ALLOWED")
            reasons << QStringLiteral("TRAINING_RIGHTS_NOT_ALLOWED");
        if (artifact.value("derivative_model_rights").toString() != "ALLOWED")
            reasons << QStringLiteral("DERIVATIVE_MODEL_RIGHTS_NOT_ALLOWED");
    }

    return {
        {"artifact_id", artifact.value("artifact_id")},
        {"eligible", reasons.isEmpty()},
        {"reasons", reasons},
        {"training_required", trainingRequired(moduleType)}
    };
}

QVariantMap AIModuleFactoryService::preparePlan(const QString &moduleName,
                                                const QString &moduleType,
                                                const QVariantList &artifacts,
                                                bool aiEnabled)
{
    QVariantList rejected;
    QVariantList qualified;

    if (!aiEnabled) {
        m_lastPlan = {
            {"schema","fa3.ai-module-plan.v1"},
            {"state","DENIED_AI_DISABLED"},
            {"execution_authorized",false},
            {"direct_provider_execution",false},
            {"silent_fallback",false}
        };
        emit planChanged();
        return m_lastPlan;
    }

    if (moduleName.trimmed().isEmpty() || !supportedModuleType(moduleType)) {
        m_lastPlan = {
            {"schema","fa3.ai-module-plan.v1"},
            {"state","DENIED_INVALID_REQUEST"},
            {"execution_authorized",false}
        };
        emit planChanged();
        return m_lastPlan;
    }

    for (const auto &value : artifacts) {
        const QVariantMap artifact = value.toMap();
        const QVariantMap result = qualifyArtifact(artifact, moduleType);
        if (result.value("eligible").toBool())
            qualified << artifact;
        else
            rejected << result;
    }

    if (qualified.isEmpty() || !rejected.isEmpty()) {
        m_lastPlan = {
            {"schema","fa3.ai-module-plan.v1"},
            {"state","DENIED_ARTIFACT_INELIGIBLE"},
            {"module_name",moduleName.trimmed()},
            {"module_type",moduleType},
            {"qualified_artifact_count",qualified.size()},
            {"rejected",rejected},
            {"execution_authorized",false},
            {"license_rights_gate_required",true}
        };
        emit planChanged();
        return m_lastPlan;
    }

    const bool trains = trainingRequired(moduleType);
    m_lastPlan = {
        {"schema","fa3.ai-module-plan.v1"},
        {"id",QUuid::createUuid().toString(QUuid::WithoutBraces)},
        {"state","DRAFT_REQUIRES_HUMAN_APPROVAL"},
        {"module_name",moduleName.trimmed()},
        {"module_type",moduleType},
        {"training_required",trains},
        {"execution_profile", trains ? kCapability : kKnowledgeProfile},
        {"qualified_artifact_count",qualified.size()},
        {"source_artifacts",qualified},
        {"capability_baseline",175},
        {"model_router_authority",kModelRouter},
        {"resource_authority",kHrb},
        {"license_rights_profile",kRights},
        {"evidence_authority",kEvidence},
        {"human_approval_required",true},
        {"execution_authorized",false},
        {"direct_provider_execution",false},
        {"direct_hardware_selection",false},
        {"silent_fallback",false},
        {"current_host_pass_claimed",false},
        {"native_model_escalation",moduleType == "NATIVE_MODEL"}
    };
    emit planChanged();
    return m_lastPlan;
}

QString AIModuleFactoryService::saveLastPlanDraft()
{
    if (m_lastPlan.isEmpty() || m_lastPlan.value("state").toString() != "DRAFT_REQUIRES_HUMAN_APPROVAL")
        return {};

    const QString root = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation)
        + QStringLiteral("/fa3/ai-module-factory/drafts");
    if (!QDir().mkpath(root))
        return {};

    const QString name = safeName(m_lastPlan.value("module_name").toString());
    const QString path = root + "/" + (name.isEmpty() ? QStringLiteral("module") : name)
        + "-" + m_lastPlan.value("id").toString() + ".json";

    QJsonObject document = QJsonObject::fromVariantMap(m_lastPlan);
    document.insert("saved_at", QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
    document.insert("persistence_scope", "DRAFT_ONLY");

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text))
        return {};
    file.write(QJsonDocument(document).toJson(QJsonDocument::Indented));
    if (!file.commit())
        return {};

    m_lastDraftPath = path;
    emit draftCreated();
    return path;
}
