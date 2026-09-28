#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>
#include <QUrl>

class CoachService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString goal READ goal NOTIFY snapshotChanged)
    Q_PROPERTY(QString scope READ scope NOTIFY snapshotChanged)
    Q_PROPERTY(QVariantList milestones READ milestones NOTIFY snapshotChanged)
    Q_PROPERTY(QVariantList blockers READ blockers NOTIFY snapshotChanged)
    Q_PROPERTY(bool committed READ committed NOTIFY snapshotChanged)
    Q_PROPERTY(int selfReportedCount READ selfReportedCount NOTIFY snapshotChanged)
    Q_PROPERTY(QString adapterState READ adapterState CONSTANT)
public:
    explicit CoachService(QObject *parent = nullptr);
    QString goal() const { return m_goal; }
    QString scope() const { return m_scope; }
    QVariantList milestones() const { return m_milestones; }
    QVariantList blockers() const { return m_blockers; }
    bool committed() const { return m_committed; }
    int selfReportedCount() const;
    QString adapterState() const { return QStringLiteral("ADAPTER-GATED"); }

    Q_INVOKABLE bool setGoal(const QString &goal, const QString &scope);
    Q_INVOKABLE bool addMilestone(const QString &text);
    Q_INVOKABLE bool markMilestone(int index, bool selfReported);
    Q_INVOKABLE bool removeMilestone(int index);
    Q_INVOKABLE bool addBlocker(const QString &text);
    Q_INVOKABLE bool resolveBlocker(int index);
    Q_INVOKABLE void setCommitment(bool explicitlyAccepted);
    Q_INVOKABLE QString nextStep() const;
    Q_INVOKABLE QVariantMap snapshot() const;
    Q_INVOKABLE QVariantMap delegationProposal(const QString &kind, const QString &reason) const;
    Q_INVOKABLE bool saveDraft(const QUrl &explicitPath) const;
    Q_INVOKABLE bool loadDraft(const QUrl &explicitPath);
    Q_INVOKABLE void clearSession();

signals:
    void snapshotChanged();

private:
    QString m_goal;
    QString m_scope = QStringLiteral("FA3_PROJECT");
    QVariantList m_milestones;
    QVariantList m_blockers;
    bool m_committed = false;
};