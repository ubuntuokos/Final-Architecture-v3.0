#include "McpControlService.h"

#include <QDateTime>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUuid>

namespace {
QVariantMap targetRecord(const QString &id,
                         const QString &name,
                         const QString &adapter,
                         const QString &capabilities)
{
    return {
        {QStringLiteral("id"), id},
        {QStringLiteral("name"), name},
        {QStringLiteral("adapter"), adapter},
        {QStringLiteral("capabilities"), capabilities},
        {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")},
        {QStringLiteral("liveHealth"), QStringLiteral("N/A")},
        {QStringLiteral("executionAuthority"), false}
    };
}

QVariantMap stageRecord(const QString &id, const QString &state, const QString &detail)
{
    return {
        {QStringLiteral("id"), id},
        {QStringLiteral("state"), state},
        {QStringLiteral("detail"), detail}
    };
}
}

McpControlService::McpControlService(QObject *parent)
    : QObject(parent)
{
}

QVariantList McpControlService::targets() const
{
    return {
        targetRecord(QStringLiteral("AUTO"), QStringLiteral("Auto / FA3 router"), QStringLiteral("central-mcp-gateway"), QStringLiteral("Capability-based routing; no direct app invocation from GUI")),
        targetRecord(QStringLiteral("GIMP"), QStringLiteral("GIMP"), QStringLiteral("gimp-mcp"), QStringLiteral("Image edit, tools, layers, export")),
        targetRecord(QStringLiteral("KRITA"), QStringLiteral("Krita"), QStringLiteral("krita-mcp"), QStringLiteral("Canvas, layers, paint/edit, export")),
        targetRecord(QStringLiteral("BLENDER"), QStringLiteral("Blender"), QStringLiteral("blender-mcp"), QStringLiteral("Scene, objects, materials, camera, render")),
        targetRecord(QStringLiteral("BFORARTIST"), QStringLiteral("Bforartist"), QStringLiteral("blender-compatible-mcp"), QStringLiteral("Blender-compatible DCC capability surface")),
        targetRecord(QStringLiteral("KDENLIVE"), QStringLiteral("Kdenlive"), QStringLiteral("kdenlive-mcp"), QStringLiteral("Project, bin, timeline, effects, render")),
        targetRecord(QStringLiteral("OPENSHOT"), QStringLiteral("OpenShot"), QStringLiteral("openshot-mcp"), QStringLiteral("Project, clips, timeline, transitions, export")),
        targetRecord(QStringLiteral("INKSCAPE"), QStringLiteral("Inkscape"), QStringLiteral("inkscape-mcp"), QStringLiteral("SVG document, objects, paths, export")),
        targetRecord(QStringLiteral("ARDOUR"), QStringLiteral("Ardour"), QStringLiteral("ardour-mcp"), QStringLiteral("Session, transport, mixer, plugin parameters"))
    };
}

bool McpControlService::isKnownTarget(const QString &targetId) const
{
    const auto rows = targets();
    for (const auto &value : rows) {
        if (value.toMap().value(QStringLiteral("id")).toString() == targetId)
            return true;
    }
    return false;
}

QVariantMap McpControlService::authoritySnapshot(const QString &targetId) const
{
    const QString effectiveTarget = isKnownTarget(targetId) ? targetId : QStringLiteral("AUTO");
    QVariantList stages {
        stageRecord(QStringLiteral("CAPTURE"), QStringLiteral("READY"), QStringLiteral("GUI captures operator intent only")),
        stageRecord(QStringLiteral("PLANNER"), QStringLiteral("ADAPTER-GATED"), QStringLiteral("Model/tool planner must produce typed capability calls")),
        stageRecord(QStringLiteral("POLICY"), QStringLiteral("REQUIRED"), QStringLiteral("Central policy authority classifies and authorizes requested capabilities")),
        stageRecord(QStringLiteral("APPROVAL"), QStringLiteral("REQUIRED"), QStringLiteral("Mutating, destructive and external-side-effect actions require explicit approval")),
        stageRecord(QStringLiteral("MCP GATEWAY"), QStringLiteral("ADAPTER-GATED"), QStringLiteral("Only the central gateway may route an admitted tool call")),
        stageRecord(QStringLiteral("TARGET"), QStringLiteral("NOT-INVOKED"), effectiveTarget),
        stageRecord(QStringLiteral("EVIDENCE"), QStringLiteral("REQUIRED"), QStringLiteral("Execution result, artifact and provenance receipt must be recorded"))
    };

    return {
        {QStringLiteral("profileId"), QStringLiteral("FA3-MCP-CONTROL-CHAT-001")},
        {QStringLiteral("target"), effectiveTarget},
        {QStringLiteral("canExecute"), false},
        {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")},
        {QStringLiteral("reason"), QStringLiteral("Planner/gateway/app adapters do not yet provide verified runtime admission to this GUI")),
        {QStringLiteral("stages"), stages}
    };
}

QVariantMap McpControlService::createDraftRequest(const QString &mode,
                                                  const QString &targetId,
                                                  const QString &prompt,
                                                  const QString &attachmentsJson,
                                                  const QString &riskHint) const
{
    const QString normalizedMode = mode.trimmed().toUpper();
    if (normalizedMode != QStringLiteral("MCP CONTROL") && normalizedMode != QStringLiteral("WORKFLOW")) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unsupported MCP chat mode")}};
    }
    if (!isKnownTarget(targetId)) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unknown MCP target")}};
    }

    QJsonParseError parseError;
    QJsonDocument attachmentsDoc = QJsonDocument::fromJson(attachmentsJson.toUtf8(), &parseError);
    QJsonArray attachments;
    if (parseError.error == QJsonParseError::NoError && attachmentsDoc.isArray())
        attachments = attachmentsDoc.array();

    if (prompt.trimmed().isEmpty() && attachments.isEmpty()) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Prompt or attachment is required")}};
    }

    QString base = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    if (base.isEmpty())
        base = QDir::homePath() + QStringLiteral("/.local/share/fa3-control-center");
    const QString requestDir = base + QStringLiteral("/mcp-control/requests");
    if (!QDir().mkpath(requestDir)) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unable to create MCP request directory")}};
    }

    const QString requestId = QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QString path = requestDir + QLatin1Char('/') + requestId + QStringLiteral(".json");

    QJsonArray authority;
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("GUI_CAPTURE")}, {QStringLiteral("state"), QStringLiteral("READY")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("PLANNER")}, {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("POLICY")}, {QStringLiteral("state"), QStringLiteral("REQUIRED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("APPROVAL")}, {QStringLiteral("state"), QStringLiteral("REQUIRED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("MCP_GATEWAY")}, {QStringLiteral("state"), QStringLiteral("ADAPTER-GATED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("TARGET")}, {QStringLiteral("state"), QStringLiteral("NOT-INVOKED")}});
    authority.append(QJsonObject{{QStringLiteral("stage"), QStringLiteral("EVIDENCE")}, {QStringLiteral("state"), QStringLiteral("REQUIRED")}});

    QJsonObject request {
        {QStringLiteral("schema_version"), 1},
        {QStringLiteral("request_id"), requestId},
        {QStringLiteral("profile_id"), QStringLiteral("FA3-MCP-CONTROL-CHAT-001")},
        {QStringLiteral("created_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("state"), QStringLiteral("DRAFT_NOT_SUBMITTED")},
        {QStringLiteral("mode"), normalizedMode},
        {QStringLiteral("target"), targetId},
        {QStringLiteral("prompt"), prompt},
        {QStringLiteral("attachments"), attachments},
        {QStringLiteral("risk_hint"), riskHint.trimmed().isEmpty() ? QStringLiteral("AUTO") : riskHint.trimmed().toUpper()},
        {QStringLiteral("authority_chain"), authority},
        {QStringLiteral("direct_tool_invocation_allowed"), false},
        {QStringLiteral("gui_self_approval_allowed"), false},
        {QStringLiteral("execution_without_policy_allowed"), false},
        {QStringLiteral("execution_without_evidence_allowed"), false}
    };

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unable to open MCP request draft for writing")}};
    }
    file.write(QJsonDocument(request).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        return {{QStringLiteral("ok"), false}, {QStringLiteral("error"), QStringLiteral("Unable to commit MCP request draft")}};
    }

    return {
        {QStringLiteral("ok"), true},
        {QStringLiteral("requestId"), requestId},
        {QStringLiteral("path"), path},
        {QStringLiteral("state"), QStringLiteral("DRAFT_NOT_SUBMITTED")},
        {QStringLiteral("target"), targetId},
        {QStringLiteral("summary"), QStringLiteral("Intent captured; planner, policy, approval, gateway and evidence stages remain authoritative and fail-closed.")}
    };
}
