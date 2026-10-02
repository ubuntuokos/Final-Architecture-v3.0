#include "ModeManager.h"
#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDBusError>
#include <QTimer>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("workmoded"));
    QCoreApplication::setApplicationVersion(QStringLiteral("0.1.0"));

    QDBusConnection bus = QDBusConnection::sessionBus();
    if (!bus.isConnected())
        return 3;

    ModeManager manager;
    if (!bus.registerObject(QStringLiteral("/org/workloadmode/Manager1"), &manager,
        QDBusConnection::ExportAllSlots | QDBusConnection::ExportAllSignals | QDBusConnection::ExportAllProperties))
        return 4;
    if (!bus.registerService(QStringLiteral("org.workloadmode.Manager1")))
        return 5;

    if (auto *iface = bus.interface()) {
        QObject::connect(iface, &QDBusConnectionInterface::serviceOwnerChanged,
                         &manager, &ModeManager::serviceOwnerChanged);
    }

    QTimer gameModeTimer;
    QObject::connect(&gameModeTimer, &QTimer::timeout, &manager, &ModeManager::refreshGameMode);
    gameModeTimer.start(2000);
    manager.refreshGameMode();

    return app.exec();
}
