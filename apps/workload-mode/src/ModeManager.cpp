#include "ModeManager.h"

#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusInterface>
#include <QDBusReply>
#include <QVariant>

namespace {
constexpr auto kHrbAuthority = "FA3-AUTH-HOST-RESOURCE-BROKER-001";
constexpr auto kGameModeService = "com.feralinteractive.GameMode";
constexpr auto kGameModePath = "/com/feralinteractive/GameMode";
constexpr auto kGameModeInterface = "com.feralinteractive.GameMode";
}

ModeManager::ModeManager(QObject *parent) : QObject(parent) {}

QString ModeManager::normalizedDomain(const QString &value)
{
    const QString d = value.trimmed().toUpper();
    if (d == QStringLiteral("AI") || d == QStringLiteral("RENDER") || d == QStringLiteral("GAME"))
        return d;
    return {};
}

QVariantMap ModeManager::Hello(const QVariantMap &request)
{
    QVariantMap out = stateMap();
    if (request.value(QStringLiteral("protocol_major")).toInt() != 1) {
        out.insert(QStringLiteral("accepted"), false);
        out.insert(QStringLiteral("reason"), QStringLiteral("INCOMPATIBLE_PROTOCOL"));
        return out;
    }

    const QString peer = request.value(QStringLiteral("peer")).toString().trimmed().toUpper();
    if (peer == QStringLiteral("FA3")) {
        if (request.value(QStringLiteral("resource_authority")).toString() != QStringLiteral(kHrbAuthority)
            || request.value(QStringLiteral("capability_count")).toInt() != 175) {
            out.insert(QStringLiteral("accepted"), false);
            out.insert(QStringLiteral("reason"), QStringLiteral("FA3_AUTHORITY_OR_BASELINE_MISMATCH"));
            return out;
        }
        const QString sender = calledFromDBus() ? message().service() : QStringLiteral("local");
        m_fa3Peers.insert(sender);
        m_fa3State = QStringLiteral("CONNECTED");
        m_authority = QStringLiteral("FA3_HRB");
        publish();
    }

    out = stateMap();
    out.insert(QStringLiteral("accepted"), true);
    out.insert(QStringLiteral("protocol_major"), 1);
    out.insert(QStringLiteral("implementation"), QStringLiteral("workmoded"));
    out.insert(QStringLiteral("implementation_version"), QCoreApplication::applicationVersion());
    return out;
}

QVariantMap ModeManager::Status() const
{
    return stateMap();
}

QVariantMap ModeManager::RegisterWorkload(const QVariantMap &workload)
{
    const QString id = workload.value(QStringLiteral("workload_id")).toString().trimmed();
    const QString domain = normalizedDomain(workload.value(QStringLiteral("domain")).toString());
    const QString integration = workload.value(QStringLiteral("integration")).toString().trimmed().toUpper();
    if (id.isEmpty() || domain.isEmpty()
        || !QStringList{QStringLiteral("OBSERVED"),QStringLiteral("COORDINATED"),QStringLiteral("MANAGED")}.contains(integration)) {
        QVariantMap out = stateMap();
        out.insert(QStringLiteral("accepted"), false);
        out.insert(QStringLiteral("reason"), QStringLiteral("INVALID_WORKLOAD_DESCRIPTOR"));
        return out;
    }
    QVariantMap row = workload;
    row.insert(QStringLiteral("domain"), domain);
    row.insert(QStringLiteral("integration"), integration);
    m_workloads.insert(id, row);
    recompute();
    QVariantMap out = stateMap();
    out.insert(QStringLiteral("accepted"), true);
    return out;
}

QVariantMap ModeManager::ReleaseWorkload(const QString &workloadId)
{
    const bool removed = m_workloads.remove(workloadId.trimmed()) > 0;
    recompute();
    QVariantMap out = stateMap();
    out.insert(QStringLiteral("accepted"), removed);
    return out;
}

QVariantMap ModeManager::SetGameModeState(const QString &state)
{
    const QString s = state.trimmed().toUpper();
    if (!QStringList{QStringLiteral("UNAVAILABLE"),QStringLiteral("AVAILABLE"),QStringLiteral("ACTIVE")}.contains(s)) {
        QVariantMap out = stateMap();
        out.insert(QStringLiteral("accepted"), false);
        return out;
    }
    m_gameModeState = s;
    recompute();
    QVariantMap out = stateMap();
    out.insert(QStringLiteral("accepted"), true);
    return out;
}

void ModeManager::refreshGameMode()
{
    auto *iface = QDBusConnection::sessionBus().interface();
    if (!iface || !iface->isServiceRegistered(QStringLiteral(kGameModeService))) {
        if (m_gameModeState != QStringLiteral("UNAVAILABLE")) {
            m_gameModeState = QStringLiteral("UNAVAILABLE");
            recompute();
        }
        return;
    }

    QDBusInterface gm(QStringLiteral(kGameModeService), QStringLiteral(kGameModePath),
                      QStringLiteral(kGameModeInterface), QDBusConnection::sessionBus());
    const QDBusReply<int> reply = gm.call(QStringLiteral("QueryStatus"), 0);
    const QString next = (reply.isValid() && reply.value() > 0)
        ? QStringLiteral("ACTIVE") : QStringLiteral("AVAILABLE");
    if (next != m_gameModeState) {
        m_gameModeState = next;
        recompute();
    }
}

void ModeManager::serviceOwnerChanged(const QString &name, const QString &oldOwner, const QString &newOwner)
{
    Q_UNUSED(name)
    if (!oldOwner.isEmpty() && newOwner.isEmpty() && m_fa3Peers.remove(oldOwner) > 0) {
        if (m_fa3Peers.isEmpty()) {
            m_fa3State = QStringLiteral("DISCONNECTED");
            m_authority = QStringLiteral("WORKLOAD_MODE_LOCAL");
            publish();
        }
    }
}

void ModeManager::recompute()
{
    bool ai = false, render = false, game = (m_gameModeState == QStringLiteral("ACTIVE"));
    for (const QVariantMap &row : m_workloads) {
        const QString d = row.value(QStringLiteral("domain")).toString();
        ai |= d == QStringLiteral("AI");
        render |= d == QStringLiteral("RENDER");
        game |= d == QStringLiteral("GAME");
    }
    QStringList active;
    if (ai) active << QStringLiteral("AI");
    if (render) active << QStringLiteral("RENDER");
    if (game) active << QStringLiteral("GAME");
    m_effectiveMode = active.isEmpty() ? QStringLiteral("NORMAL") : active.join(QStringLiteral("+"));
    publish();
}

void ModeManager::publish()
{
    emit stateChanged();
    emit StateChanged(stateMap());
}

QVariantMap ModeManager::stateMap() const
{
    QVariantMap out;
    out.insert(QStringLiteral("effective_mode"), m_effectiveMode);
    out.insert(QStringLiteral("local_mode"), QStringLiteral("NORMAL"));
    QStringList domains;
    if (m_effectiveMode != QStringLiteral("NORMAL"))
        domains = m_effectiveMode.split(QLatin1Char('+'));
    out.insert(QStringLiteral("active_domains"), domains);
    out.insert(QStringLiteral("active_workload_count"), m_workloads.size());
    out.insert(QStringLiteral("authority"), m_authority);
    out.insert(QStringLiteral("fa3_state"), m_fa3State);
    out.insert(QStringLiteral("gamemode_state"), m_gameModeState);
    out.insert(QStringLiteral("resource_pressure"), m_resourcePressure);
    out.insert(QStringLiteral("safety_state"), m_safetyState);
    out.insert(QStringLiteral("conflict_state"), m_conflictState);
    out.insert(QStringLiteral("degraded_state"), false);
    out.insert(QStringLiteral("degraded_reason"), QString());
    bool external = false;
    for (const QVariantMap &row : m_workloads)
        external |= row.value(QStringLiteral("integration")).toString() != QStringLiteral("MANAGED");
    out.insert(QStringLiteral("external_workload_present"), external);
    out.insert(QStringLiteral("lease_health"), QStringLiteral("NOT_ACTIVE_REFERENCE_STATE_CORE"));
    out.insert(QStringLiteral("rollback_health"), QStringLiteral("NOT_ACTIVE_REFERENCE_STATE_CORE"));
    return out;
}
