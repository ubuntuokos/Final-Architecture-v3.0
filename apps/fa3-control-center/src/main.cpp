#include "Fa3RepositoryModel.h"
#include "SettingsStore.h"
#include "ResourceTelemetry.h"
#include "LlmfitClient.h"
#include "JournalReader.h"
#include "SecretBrokerService.h"
#include "OpenModelDbService.h"
#include "CivitaiClient.h"
#include "SearchIndexService.h"

#include <QApplication>
#include <QCoreApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QUrl>
#include <QtWebEngineQuick/qtwebenginequickglobal.h>

int main(int argc, char *argv[])
{
    QCoreApplication::setAttribute(Qt::AA_ShareOpenGLContexts);
    QtWebEngineQuick::initialize();

    QApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3ControlCenter");
    QCoreApplication::setApplicationVersion("0.4.0");
    QCoreApplication::setOrganizationName("FinalArchitecture");
    QCoreApplication::setOrganizationDomain("fa3.local");
    QApplication::setApplicationDisplayName("FA3 Control Center");

    Fa3RepositoryModel repository;
    SettingsStore settings;
    ResourceTelemetry telemetry;
    LlmfitClient llmfit;
    JournalReader journal;
    SecretBrokerService secretBroker;
    OpenModelDbService openModelDb;
    CivitaiClient civitai(&secretBroker);
    SearchIndexService searchIndex;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3Settings", &settings);
    engine.rootContext()->setContextProperty("fa3ResourceTelemetry", &telemetry);
    engine.rootContext()->setContextProperty("llmfitClient", &llmfit);
    engine.rootContext()->setContextProperty("fa3Journal", &journal);
    engine.rootContext()->setContextProperty("fa3SecretBroker", &secretBroker);
    engine.rootContext()->setContextProperty("openModelDbService", &openModelDb);
    engine.rootContext()->setContextProperty("civitaiClient", &civitai);
    engine.rootContext()->setContextProperty("fa3SearchIndex", &searchIndex);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/StudioAwareOperationsShell.qml")));

    if (engine.rootObjects().isEmpty()) return 2;
    return app.exec();
}
