// SPDX-License-Identifier: Apache-2.0
#include "OfficeFabricService.h"

#include <QStandardPaths>

OfficeFabricService::OfficeFabricService(QObject *parent)
    : QObject(parent)
{
}

QString OfficeFabricService::fabricState() const
{
    return QStringLiteral("STATIC_MATERIALIZED_RUNTIME_ADMISSION_PENDING");
}

QString OfficeFabricService::engineCandidate() const
{
    return QStringLiteral("LibreOffice Core / LibreOfficeKit / UNO");
}

QVariantList OfficeFabricService::surfaces() const
{
    return {
        QVariantMap{{"id","WRITER"},{"label","Writer"},{"kind","TEXT_DOCUMENT"}},
        QVariantMap{{"id","SHEETS"},{"label","Sheets"},{"kind","SPREADSHEET"}},
        QVariantMap{{"id","PRESENTATION"},{"label","Presentation"},{"kind","PRESENTATION"}},
        QVariantMap{{"id","DOCUMENTS"},{"label","Documents"},{"kind","DOCUMENT_VIEW"}},
        QVariantMap{{"id","FORMS"},{"label","Forms"},{"kind","FORM"}}
    };
}

QVariantList OfficeFabricService::formatProfiles() const
{
    return {
        QVariantMap{{"id","ODT"},{"state","PENDING_GOLDEN_ROUNDTRIP"},{"editableCandidate",true}},
        QVariantMap{{"id","DOCX"},{"state","PENDING_GOLDEN_ROUNDTRIP"},{"editableCandidate",true}},
        QVariantMap{{"id","ODS"},{"state","PENDING_GOLDEN_ROUNDTRIP"},{"editableCandidate",true}},
        QVariantMap{{"id","XLSX"},{"state","PENDING_GOLDEN_ROUNDTRIP"},{"editableCandidate",true}},
        QVariantMap{{"id","ODP"},{"state","PENDING_GOLDEN_ROUNDTRIP"},{"editableCandidate",true}},
        QVariantMap{{"id","PPTX"},{"state","PENDING_GOLDEN_ROUNDTRIP"},{"editableCandidate",true}},
        QVariantMap{{"id","PDF"},{"state","DELIVERY_OR_PREVIEW_ONLY"},{"editableCandidate",false}}
    };
}

QVariantMap OfficeFabricService::runtimeProbe() const
{
    QString executable = QStandardPaths::findExecutable(QStringLiteral("libreoffice"));
    if (executable.isEmpty())
        executable = QStandardPaths::findExecutable(QStringLiteral("soffice"));

    return {
        {"engine","LibreOffice"},
        {"installed",!executable.isEmpty()},
        {"executable",executable},
        {"probe_mode","READ_ONLY_DISCOVERY"},
        {"runtime_admission","PENDING_LICENSE_RIGHTS_AND_PHYSICAL_CURRENT_HOST"},
        {"execution_started",false},
        {"user_profile_mutated",false}
    };
}

bool OfficeFabricService::supportedSurface(const QString &surface)
{
    return surface == "WRITER" || surface == "SHEETS" || surface == "PRESENTATION"
        || surface == "DOCUMENTS" || surface == "FORMS";
}

bool OfficeFabricService::candidateEditableFormat(const QString &format)
{
    return format == "ODT" || format == "DOCX" || format == "ODS"
        || format == "XLSX" || format == "ODP" || format == "PPTX";
}

QVariantMap OfficeFabricService::prepareSession(const QString &surface,
                                                const QString &format,
                                                bool aiEnabled) const
{
    if (!supportedSurface(surface)) {
        return {
            {"schema","fa3.office-session-plan.v1"},
            {"state","DENIED_UNKNOWN_SURFACE"},
            {"execution_authorized",false}
        };
    }

    const bool editable = candidateEditableFormat(format);
    if (!editable && format != "PDF") {
        return {
            {"schema","fa3.office-session-plan.v1"},
            {"state","DENIED_UNKNOWN_FORMAT_PROFILE"},
            {"execution_authorized",false},
            {"silent_fallback",false}
        };
    }

    const QString operationMode = editable
        ? QStringLiteral("EDITABLE_CANDIDATE_PENDING_GOLDEN_ROUNDTRIP")
        : QStringLiteral("PREVIEW_OR_DELIVERY_ONLY");

    return {
        {"schema","fa3.office-session-plan.v1"},
        {"state","DRAFT_REQUIRES_RUNTIME_ADMISSION_AND_HUMAN_APPROVAL"},
        {"surface",surface},
        {"format",format},
        {"format_mode",operationMode},
        {"document_authority","FA3-DOC-001"},
        {"engine_candidate","LibreOffice"},
        {"runtime_worker","ISOLATED_FA3_OFFICE_WORKER"},
        {"runtime_admission","PENDING"},
        {"ai_enabled_for_session",aiEnabled},
        {"ai_invocation_started",false},
        {"preview_required_before_mutation",true},
        {"explicit_apply_required",true},
        {"undo_required",true},
        {"same_type_export_required",editable},
        {"loss_receipt_required",true},
        {"execution_authorized",false},
        {"silent_fallback",false},
        {"physical_current_host_pass_claimed",false}
    };
}
