#include "Fa3RepositoryModel.h"
#include "LlmfitClient.h"

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
    LlmfitClient llmfit;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("llmfitClient", &llmfit);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }
    return app.exec();
}
