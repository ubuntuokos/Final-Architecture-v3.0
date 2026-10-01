// SPDX-License-Identifier: Apache-2.0
#include "../src/AIModuleFactoryService.h"

#include <QtTest>

class AIModuleFactoryServiceTest final : public QObject
{
    Q_OBJECT

private slots:
    void aiOffDenies();
    void rightsFailClosed();
    void knowledgeAvoidsTraining();
    void adapterRoutesToCap095();
};

static QVariantMap goodArtifact()
{
    return {
        {"artifact_id","artifact-1"},
        {"source_application","fa3.video-editor"},
        {"approved_final",true},
        {"provenance_status","VERIFIED"},
        {"use_rights","ALLOWED"},
        {"training_rights","ALLOWED"},
        {"derivative_model_rights","ALLOWED"},
        {"consent_scope","PROJECT"}
    };
}

void AIModuleFactoryServiceTest::aiOffDenies()
{
    AIModuleFactoryService service;
    const auto plan = service.preparePlan("x", "SKILL_ADAPTER", {goodArtifact()}, false);
    QCOMPARE(plan.value("state").toString(), QString("DENIED_AI_DISABLED"));
    QCOMPARE(plan.value("execution_authorized").toBool(), false);
}

void AIModuleFactoryServiceTest::rightsFailClosed()
{
    AIModuleFactoryService service;
    auto artifact = goodArtifact();
    artifact["training_rights"] = "UNKNOWN";
    const auto plan = service.preparePlan("x", "SKILL_ADAPTER", {artifact}, true);
    QCOMPARE(plan.value("state").toString(), QString("DENIED_ARTIFACT_INELIGIBLE"));
    QCOMPARE(plan.value("execution_authorized").toBool(), false);
}

void AIModuleFactoryServiceTest::knowledgeAvoidsTraining()
{
    AIModuleFactoryService service;
    auto artifact = goodArtifact();
    artifact.remove("training_rights");
    artifact.remove("derivative_model_rights");
    const auto plan = service.preparePlan("knowledge", "KNOWLEDGE", {artifact}, true);
    QCOMPARE(plan.value("state").toString(), QString("DRAFT_REQUIRES_HUMAN_APPROVAL"));
    QCOMPARE(plan.value("training_required").toBool(), false);
    QCOMPARE(plan.value("execution_profile").toString(), QString("FA3-SHARED-KNOWLEDGE-RETRIEVAL-001"));
    QCOMPARE(plan.value("execution_authorized").toBool(), false);
}

void AIModuleFactoryServiceTest::adapterRoutesToCap095()
{
    AIModuleFactoryService service;
    const auto plan = service.preparePlan("adapter", "SKILL_ADAPTER", {goodArtifact()}, true);
    QCOMPARE(plan.value("state").toString(), QString("DRAFT_REQUIRES_HUMAN_APPROVAL"));
    QCOMPARE(plan.value("training_required").toBool(), true);
    QCOMPARE(plan.value("execution_profile").toString(), QString("CAP-095"));
    QCOMPARE(plan.value("direct_provider_execution").toBool(), false);
    QCOMPARE(plan.value("direct_hardware_selection").toBool(), false);
    QCOMPARE(plan.value("silent_fallback").toBool(), false);
}

QTEST_MAIN(AIModuleFactoryServiceTest)
#include "test_service.moc"
