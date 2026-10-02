#include <QCoreApplication>
#include <QDBusInterface>
#include <QDBusReply>
#include <QDBusServiceWatcher>
#include <QTimer>
#include <QVariantMap>
#include <iostream>

static bool hello()
{
    QDBusInterface iface(QStringLiteral("org.workloadmode.Manager1"),
                         QStringLiteral("/org/workloadmode/Manager1"),
                         QStringLiteral("org.workloadmode.Manager1"),
                         QDBusConnection::sessionBus());
    if (!iface.isValid()) return false;
    QVariantMap req;
    req.insert(QStringLiteral("peer"), QStringLiteral("FA3"));
    req.insert(QStringLiteral("protocol_major"), 1);
    req.insert(QStringLiteral("implementation_version"), QStringLiteral("3.x"));
    req.insert(QStringLiteral("instance_id"), QStringLiteral("fa3-session"));
    req.insert(QStringLiteral("resource_authority"), QStringLiteral("FA3-AUTH-HOST-RESOURCE-BROKER-001"));
    req.insert(QStringLiteral("capability_count"), 175);
    QDBusReply<QVariantMap> reply = iface.call(QStringLiteral("Hello"), req);
    return reply.isValid() && reply.value().value(QStringLiteral("accepted")).toBool();
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("fa3-workload-mode-bridge"));
    QDBusServiceWatcher watcher(QStringLiteral("org.workloadmode.Manager1"), QDBusConnection::sessionBus(),
                                QDBusServiceWatcher::WatchForRegistration | QDBusServiceWatcher::WatchForUnregistration);
    QObject::connect(&watcher, &QDBusServiceWatcher::serviceRegistered, &app, [](const QString &) { hello(); });
    QTimer retry;
    QObject::connect(&retry, &QTimer::timeout, &app, [] { hello(); });
    retry.start(5000);
    hello();
    return app.exec();
}
