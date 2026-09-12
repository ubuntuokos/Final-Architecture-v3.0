#include "Fa3RepositoryModel.h"
#include "SettingsStore.h"

#include <QApplication>
#include <QCoreApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QUrl>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3ControlCenter");
    QCoreApplication::setApplicationVersion("0.2.0");
    QCoreApplication::setOrganizationName("FinalArchitecture");
    QCoreApplication::setOrganizationDomain("fa3.local");
    QApplication::setApplicationDisplayName("FA3 Control Center");

    Fa3RepositoryModel repository;
    SettingsStore settings;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3Settings", &settings);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/AppShell.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }
    return app.exec();
}
