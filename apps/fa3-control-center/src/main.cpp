#include "Fa3RepositoryModel.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3 Control Center");
    QCoreApplication::setApplicationVersion("0.1.0");
    QCoreApplication::setOrganizationName("Final Architecture");

    Fa3RepositoryModel repository;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.loadFromModule("FA3.ControlCenter", "Main");
    if (engine.rootObjects().isEmpty()) return 2;
    return app.exec();
}
