#include "WorkloadModeStateService.h"

#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusReply>

namespace {
constexpr auto kService = "org.workloadmode.Manager1";
constexpr auto kPath = "/org/workloadmode/Manager1";
constexpr auto kInterface = "org.workloadmode.Manager1";
}

WorkloadModeStateService::WorkloadModeStateService(QObject *parent)
    : QObject(parent),
      m_watcher(QString::fromLatin1(kService), QDBusConnection::sessionBus(),
                QDBusServiceWatcher::WatchForRegistration | QDBusServiceWatcher::WatchForUnregistration, this)
{
    connect(&m_watcher, &QDBusServiceWatcher::serviceRegistered,
            this, &WorkloadModeStateService::onServiceRegistered);
    connect(&m_watcher, &QDBusServiceWatcher::serviceUnregistered,
            this, &WorkloadModeStateService::onServiceUnregistered);
    QDBusConnection::sessionBus().connect(QString::fromLatin1(kService), QString::fromLatin1(kPath),
                                          QString::fromLatin1(kInterface), QStringLiteral("StateChanged"),
                                          this, SLOT(onRemoteStateChanged(QVariantMap)));
    refresh();
}

void WorkloadModeStateService::markUnavailable(const QString &reason)
{
    m_effectiveMode = QStringLiteral("DEGRADED");
    m_localMode = QStringLiteral("NORMAL");
    m_authority = QStringLiteral("UNAVAILABLE");
    m_fa3State = QStringLiteral("DISCONNECTED");
    m_gameModeState = QStringLiteral("UNAVAILABLE");
    m_safetyState = QStringLiteral("PASS");
    m_conflictState = QStringLiteral("NONE");
    m_resourcePressure = QStringLiteral("UNKNOWN");
    m_activeWorkloadCount = 0;
    m_degraded = true;
    m_degradedReason = reason;
    m_serviceAvailable = false;
    emit stateChanged();
}

void WorkloadModeStateService::applyState(const QVariantMap &state)
{
    m_effectiveMode = state.value(QStringLiteral("effective_mode"), QStringLiteral("DEGRADED")).toString();
    m_localMode = state.value(QStringLiteral("local_mode"), QStringLiteral("NORMAL")).toString();
    m_authority = state.value(QStringLiteral("authority"), QStringLiteral("UNAVAILABLE")).toString();
    m_fa3State = state.value(QStringLiteral("fa3_state"), QStringLiteral("DISCONNECTED")).toString();
    m_gameModeState = state.value(QStringLiteral("gamemode_state"), QStringLiteral("UNAVAILABLE")).toString();
    m_safetyState = state.value(QStringLiteral("safety_state"), QStringLiteral("UNKNOWN")).toString();
    m_conflictState = state.value(QStringLiteral("conflict_state"), QStringLiteral("UNKNOWN")).toString();
    m_resourcePressure = state.value(QStringLiteral("resource_pressure"), QStringLiteral("UNKNOWN")).toString();
    m_activeWorkloadCount = state.value(QStringLiteral("active_workload_count"), 0).toInt();
    m_degraded = state.value(QStringLiteral("degraded_state"), false).toBool();
    m_degradedReason = state.value(QStringLiteral("degraded_reason")).toString();
    m_serviceAvailable = true;
    emit stateChanged();
}

void WorkloadModeStateService::refresh()
{
    QDBusInterface iface(QString::fromLatin1(kService), QString::fromLatin1(kPath), QString::fromLatin1(kInterface),
                         QDBusConnection::sessionBus());
    if (!iface.isValid()) {
        markUnavailable(QStringLiteral("WORKLOAD_MODE_REQUIRED_SERVICE_UNAVAILABLE"));
        return;
    }

    QVariantMap hello;
    hello.insert(QStringLiteral("peer"), QStringLiteral("FA3"));
    hello.insert(QStringLiteral("protocol_major"), 1);
    hello.insert(QStringLiteral("implementation_version"), QCoreApplication::applicationVersion());
    hello.insert(QStringLiteral("instance_id"), QString::number(QCoreApplication::applicationPid()));
    hello.insert(QStringLiteral("resource_authority"), QStringLiteral("FA3-AUTH-HOST-RESOURCE-BROKER-001"));
    hello.insert(QStringLiteral("capability_count"), 175);
    const QDBusReply<QVariantMap> accepted = iface.call(QStringLiteral("Hello"), hello);
    if (!accepted.isValid() || !accepted.value().value(QStringLiteral("accepted")).toBool()) {
        markUnavailable(QStringLiteral("WORKLOAD_MODE_PROTOCOL_OR_AUTHORITY_HANDSHAKE_DENIED"));
        return;
    }

    const QDBusReply<QVariantMap> status = iface.call(QStringLiteral("Status"));
    if (!status.isValid()) {
        markUnavailable(QStringLiteral("WORKLOAD_MODE_STATUS_UNAVAILABLE"));
        return;
    }
    applyState(status.value());
}

void WorkloadModeStateService::onRemoteStateChanged(const QVariantMap &state)
{
    applyState(state);
}

void WorkloadModeStateService::onServiceRegistered(const QString &service)
{
    Q_UNUSED(service)
    refresh();
}

void WorkloadModeStateService::onServiceUnregistered(const QString &service)
{
    Q_UNUSED(service)
    markUnavailable(QStringLiteral("WORKLOAD_MODE_REQUIRED_SERVICE_STOPPED"));
}
