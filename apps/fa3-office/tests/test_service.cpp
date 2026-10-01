// SPDX-License-Identifier: Apache-2.0
#include "OfficeFabricService.h"

#include <QtTest>

class OfficeFabricServiceTest final : public QObject
{
    Q_OBJECT
private slots:
    void staticStateIsPendingRuntime()
    {
        OfficeFabricService service;
        QCOMPARE(service.fabricState(), QStringLiteral("STATIC_MATERIALIZED_RUNTIME_ADMISSION_PENDING"));
        const auto probe = service.runtimeProbe();
        QCOMPARE(probe.value("execution_started").toBool(), false);
        QCOMPARE(probe.value("user_profile_mutated").toBool(), false);
    }

    void editableCandidateDoesNotAuthorizeExecution()
    {
        OfficeFabricService service;
        const auto plan = service.prepareSession("WRITER", "DOCX", false);
        QCOMPARE(plan.value("state").toString(), QStringLiteral("DRAFT_REQUIRES_RUNTIME_ADMISSION_AND_HUMAN_APPROVAL"));
        QCOMPARE(plan.value("execution_authorized").toBool(), false);
        QCOMPARE(plan.value("same_type_export_required").toBool(), true);
        QCOMPARE(plan.value("ai_invocation_started").toBool(), false);
    }

    void pdfIsNotEditableClaim()
    {
        OfficeFabricService service;
        const auto plan = service.prepareSession("DOCUMENTS", "PDF", false);
        QCOMPARE(plan.value("format_mode").toString(), QStringLiteral("PREVIEW_OR_DELIVERY_ONLY"));
        QCOMPARE(plan.value("same_type_export_required").toBool(), false);
    }

    void unknownFormatFailsClosed()
    {
        OfficeFabricService service;
        const auto plan = service.prepareSession("WRITER", "UNKNOWN", true);
        QCOMPARE(plan.value("state").toString(), QStringLiteral("DENIED_UNKNOWN_FORMAT_PROFILE"));
        QCOMPARE(plan.value("execution_authorized").toBool(), false);
        QCOMPARE(plan.value("silent_fallback").toBool(), false);
    }
};

QTEST_MAIN(OfficeFabricServiceTest)
#include "test_service.moc"
