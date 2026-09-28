#include "CoachService.h"

#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>

namespace {
constexpr int maxItems = 50;
constexpr int maxFileBytes = 256 * 1024;
QString clean(const QString &value, int limit = 600)
{
    return value.trimmed().left(limit);
}
bool validScope(const QString &scope)
{
    return scope == QLatin1String("USER_SELF")
        || scope == QLatin1String("FA3_PROJECT")
        || scope == QLatin1String("AI_AGENT_WORK");
}
bool localFile(const QUrl &url)
{
    return url.isLocalFile() && !url.toLocalFile().isEmpty();
}
} // namespace

CoachService::CoachService(QObject *parent) : QObject(parent) {}

int CoachService::selfReportedCount() const
{
    int count = 0;
    for (const auto &v : m_milestones)
        if (v.toMap().value(QStringLiteral("selfReported")).toBool()) ++count;
    return count;
}

bool CoachService::setGoal(const QString &goal, const QString &scope)
{
    const QString text = clean(goal);
    if (text.isEmpty() || !validScope(scope)) return false;
    m_goal = text;
    m_scope = scope;
    m_committed = false; // Changing the goal revokes the previous commitment.
    emit snapshotChanged();
    return true;
}
bool CoachService::addMilestone(const QString &text)
{
    const QString item = clean(text);
    if (m_goal.isEmpty() || item.isEmpty() || m_milestones.size() >= maxItems) return false;
    m_milestones.append(QVariantMap{{QStringLiteral("text"), item},
                                    {QStringLiteral("selfReported"), false},
                                    {QStringLiteral("evidenceState"), QStringLiteral("UNVERIFIED")}});
    emit snapshotChanged();
    return true;
}
bool CoachService::markMilestone(int index, bool selfReported)
{
    if (index < 0 || index >= m_milestones.size()) return false;
    QVariantMap record = m_milestones[index].toMap();
    record.insert(QStringLiteral("selfReported"), selfReported);
    // This state is an operator report, NOT canonical evidence or VERIFIED.
    record.insert(QStringLiteral("evidenceState"), QStringLiteral("UNVERIFIED"));
    m_milestones[index] = record;
    emit snapshotChanged();
    return true;
}
bool CoachService::removeMilestone(int index)
{
    if (index < 0 || index >= m_milestones.size()) return false;
    m_milestones.removeAt(index);
    emit snapshotChanged();
    return true;
}
bool CoachService::addBlocker(const QString &text)
{
    const QString item = clean(text);
    if (item.isEmpty() || m_blockers.size() >= maxItems) return false;
    m_blockers.append(QVariantMap{{QStringLiteral("text"), item},
                                 {QStringLiteral("resolved"), false}});
    emit snapshotChanged();
    return true;
}
bool CoachService::resolveBlocker(int index)
{
    if (index < 0 || index >= m_blockers.size()) return false;
    QVariantMap record = m_blockers[index].toMap();
    record.insert(QStringLiteral("resolved"), true);
    m_blockers[index] = record;
    emit snapshotChanged();
    return true;
}
void CoachService::setCommitment(bool explicitlyAccepted)
{
    m_committed = explicitlyAccepted;
    emit snapshotChanged();
}
QString CoachService::nextStep() const
{
    if (m_goal.isEmpty()) return QStringLiteral("Először határozd meg a célodat.");
    for (const auto &entry : m_blockers) {
        const auto blocker = entry.toMap();
        if (!blocker.value(QStringLiteral("resolved")).toBool())
            return QStringLiteral("Tekintsd át az akadályt: %1").arg(blocker.value(QStringLiteral("text")).toString());
    }
    for (const auto &entry : m_milestones) {
        const auto step = entry.toMap();
        if (!step.value(QStringLiteral("selfReported")).toBool())
            return QStringLiteral("Következő javasolt lépés: %1").arg(step.value(QStringLiteral("text")).toString());
    }
    return QStringLiteral("Minden lépés saját jelzésű; kérj független bizonyíték-ellenőrzést.");
}
QVariantMap CoachService::snapshot() const
{
    return {{QStringLiteral("schema"), QStringLiteral("fa3.coach-session-draft.v2")},
            {QStringLiteral("status"), QStringLiteral("LOCAL_DRAFT_UNVERIFIED")},
            {QStringLiteral("goalOwner"), QStringLiteral("USER")},
            {QStringLiteral("goal"), m_goal},
            {QStringLiteral("scope"), m_scope},
            {QStringLiteral("milestones"), m_milestones},
            {QStringLiteral("blockers"), m_blockers},
            {QStringLiteral("explicitCommitment"), m_committed},
            {QStringLiteral("verifiedCount"), 0},
            {QStringLiteral("adapterState"), adapterState()},
            {QStringLiteral("directExecutionAllowed"), false},
            {QStringLiteral("canonicalMemoryWriteAllowed"), false}};
}
QVariantMap CoachService::delegationProposal(const QString &kind, const QString &reason) const
{
    const QString target = kind == QLatin1String("MENTOR") ? QStringLiteral("FA3-MENTOR-001")
        : kind == QLatin1String("MANAGER") ? QStringLiteral("FA3-MANAGER-001")
        : kind == QLatin1String("EVIDENCE") ? QStringLiteral("FA3-AUTH-OBS-EVIDENCE-001")
        : QString();
    if (target.isEmpty() || m_goal.isEmpty() || clean(reason).isEmpty())
        return {{QStringLiteral("status"), QStringLiteral("REJECTED")}};
    return {{QStringLiteral("schema"), QStringLiteral("fa3.coach-delegation-proposal.v1")},
            {QStringLiteral("status"), QStringLiteral("LOCAL_PROPOSAL_NOT_SUBMITTED")},
            {QStringLiteral("kind"), kind},
            {QStringLiteral("target"), target},
            {QStringLiteral("goal"), m_goal},
            {QStringLiteral("reason"), clean(reason)},
            {QStringLiteral("directExecutionAllowed"), false}};
}
bool CoachService::saveDraft(const QUrl &explicitPath) const
{
    if (!localFile(explicitPath) || m_goal.isEmpty()) return false;
    // No automatic storage. The user explicitly chooses a local file.
    const QFileInfo info(explicitPath.toLocalFile());
    if (info.isSymLink() || info.exists() && !info.isFile()) return false;
    QSaveFile file(explicitPath.toLocalFile());
    if (!file.open(QIODevice::WriteOnly)) return false;
    const QJsonObject data = QJsonObject::fromVariantMap(snapshot());
    if (file.write(QJsonDocument(data).toJson(QJsonDocument::Indented)) < 0) {
        file.cancelWriting();
        return false;
    }
    return file.commit();
}
bool CoachService::loadDraft(const QUrl &explicitPath)
{
    if (!localFile(explicitPath)) return false;
    QFile file(explicitPath.toLocalFile());
    if (!file.open(QIODevice::ReadOnly) || file.size() > maxFileBytes) return false;
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) return false;
    const QJsonObject obj = document.object();
    if (obj.value(QStringLiteral("schema")).toString() != QLatin1String("fa3.coach-session-draft.v2")) return false;
    const QString goal = clean(obj.value(QStringLiteral("goal")).toString());
    const QString scope = obj.value(QStringLiteral("scope")).toString();
    if (goal.isEmpty() || !validScope(scope)) return false;
    const auto stages = obj.value(QStringLiteral("milestones")).toArray();
    const auto blockers = obj.value(QStringLiteral("blockers")).toArray();
    if (stages.size() > maxItems || blockers.size() > maxItems) return false;
    QVariantList safeStages, safeBlockers;
    for (const auto &v : stages) {
        if (!v.isObject() || clean(v.toObject().value(QStringLiteral("text")).toString()).isEmpty()) return false;
        const auto item = v.toObject();
        safeStages.append(QVariantMap{
            {QStringLiteral("text"), clean(item.value(QStringLiteral("text")).toString())},
            {QStringLiteral("selfReported"), item.value(QStringLiteral("selfReported")).toBool()},
            {QStringLiteral("evidenceState"), QStringLiteral("UNVERIFIED")}});
    }
    for (const auto &v : blockers) {
        if (!v.isObject() || clean(v.toObject().value(QStringLiteral("text")).toString()).isEmpty()) return false;
        const auto item = v.toObject();
        safeBlockers.append(QVariantMap{
            {QStringLiteral("text"), clean(item.value(QStringLiteral("text")).toString())},
            {QStringLiteral("resolved"), item.value(QStringLiteral("resolved")).toBool()}});
    }
    m_goal = goal;
    m_scope = scope;
    m_milestones = safeStages;
    m_blockers = safeBlockers;
    // Imported content cannot impersonate user authorization or authenticated evidence.
    m_committed = false;
    emit snapshotChanged();
    return true;
}
void CoachService::clearSession()
{
    m_goal.clear();
    m_scope = QStringLiteral("FA3_PROJECT");
    m_milestones.clear();
    m_blockers.clear();
    m_committed = false;
    emit snapshotChanged();
}