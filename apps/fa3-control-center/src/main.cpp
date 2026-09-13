#include "Fa3RepositoryModel.h"
#include "JournalService.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QUrl>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3 Control Center");
    QCoreApplication::setApplicationVersion("0.2.0");
    QCoreApplication::setOrganizationName("Final Architecture");

    Fa3RepositoryModel repository;
    JournalService journal;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3Journal", &journal);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }
    return app.exec();
}
