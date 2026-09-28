#include "../src/CoachService.h"
#include <QtTest/QTest>
#include <QTemporaryDir>
#include <QUrl>

class CoachServiceTest : public QObject {
    Q_OBJECT
private slots:
    void goalAndMilestones()
    {
        CoachService s;
        QVERIFY(!s.setGoal(QString(), QStringLiteral("FA3_PROJECT")));
        QVERIFY(s.setGoal(QStringLiteral("Implement Coach"), QStringLiteral("FA3_PROJECT")));
        QVERIFY(s.addMilestone(QStringLiteral("Create GUI")));
        QVERIFY(s.markMilestone(0, true));
        QCOMPARE(s.selfReportedCount(), 1);
        QCOMPARE(s.snapshot().value(QStringLiteral("verifiedCount")).toInt(), 0);
        QCOMPARE(s.milestones()[0].toMap().value(QStringLiteral("evidenceState")).toString(), QStringLiteral("UNVERIFIED"));
    }
    void cannotFabricateEvidenceOrApproval()
    {
        QTemporaryDir directory;
        QVERIFY(directory.isValid());
        CoachService s;
        QVERIFY(s.setGoal(QStringLiteral("Prototype"), QStringLiteral("AI_AGENT_WORK")));
        s.setCommitment(true);
        QVERIFY(s.addMilestone(QStringLiteral("Build")));
        QVERIFY(s.markMilestone(0,true));
        const QUrl target = QUrl::fromLocalFile(directory.filePath(QStringLiteral("draft.json")));
        QVERIFY(s.saveDraft(target));
        CoachService restored;
        QVERIFY(restored.loadDraft(target));
        QVERIFY(!restored.committed());
        QCOMPARE(restored.snapshot().value(QStringLiteral("verifiedCount")).toInt(), 0);
        QCOMPARE(restored.adapterState(), QStringLiteral("ADAPTER-GATED"));
    }
    void delegationsOnlyProposals()
    {
        CoachService s;
        QVERIFY(s.setGoal(QStringLiteral("Project"), QStringLiteral("FA3_PROJECT")));
        auto proposal = s.delegationProposal(QStringLiteral("MENTOR"), QStringLiteral("Learning gap"));
        QCOMPARE(proposal.value(QStringLiteral("status")).toString(),QStringLiteral("LOCAL_PROPOSAL_NOT_SUBMITTED"));
        QVERIFY(!proposal.value(QStringLiteral("directExecutionAllowed")).toBool());
        QCOMPARE(s.delegationProposal(QStringLiteral("RUN_SHELL"), QStringLiteral("test")).value(QStringLiteral("status")).toString(),QStringLiteral("REJECTED"));
        s.clearSession();
        QVERIFY(s.goal().isEmpty());
    }
};
QTEST_GUILESS_MAIN(CoachServiceTest)
#include "CoachServiceTest.moc"