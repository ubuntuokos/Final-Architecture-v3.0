#include "AppCatalogService.h"
#include "ChatFileService.h"
#include "DecisionFabricService.h"
#include "ExternalLlmCatalogModel.h"\n#include "EngineSelectorService.h"
#include "Fa3RepositoryModel.h"
#include "JournalService.h"
#include "ModelLibraryService.h"
#include "OrchestrationMonitorService.h"
#include "McpControlService.h"
#include "McpGatewayService.h"
#include "PreferenceStore.h"
#include "SystemDeviceModel.h"
#include "WorkloadModeStateService.h"
#include "SessionVaultService.h"

#include <QColor>
#include <QGuiApplication>
#include <QPalette>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QUrl>
#include <QtWebEngineQuick/qtwebenginequickglobal.h>

int main(int argc, char *argv[])
{
    QtWebEngineQuick::initialize();
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3 Control Center");
    QCoreApplication::setApplicationVersion("0.3.0");
    QCoreApplication::setOrganizationName("Final Architecture");

    QQuickStyle::setStyle(QStringLiteral("Basic"));

    QPalette palette;
    palette.setColor(QPalette::Window, QColor("#07111f"));
    palette.setColor(QPalette::WindowText, QColor("#f5f8fc"));
    palette.setColor(QPalette::Base, QColor("#0b1728"));
    palette.setColor(QPalette::AlternateBase, QColor("#0f2035"));
    palette.setColor(QPalette::Text, QColor("#f5f8fc"));
    palette.setColor(QPalette::Button, QColor("#10243a"));
    palette.setColor(QPalette::ButtonText, QColor("#f5f8fc"));
    palette.setColor(QPalette::Highlight, QColor("#25a7ff"));
    palette.setColor(QPalette::HighlightedText, QColor("#ffffff"));
    palette.setColor(QPalette::PlaceholderText, QColor("#6f849a"));
    palette.setColor(QPalette::ToolTipBase, QColor("#10243a"));
    palette.setColor(QPalette::ToolTipText, QColor("#f5f8fc"));
    app.setPalette(palette);

    Fa3RepositoryModel repository;
    JournalService journal;
    PreferenceStore preferences;
    SystemDeviceModel devices;
    ChatFileService chatFiles;
    ModelLibraryService modelLibrary;
    OrchestrationMonitorService orchestrationMonitor;
    McpControlService mcpControl;
    McpGatewayService mcpGateway;
    AppCatalogService appCatalog;
    SessionVaultService sessionVault;
    DecisionFabricService decisionFabric;
    ExternalLlmCatalogModel externalLlmCatalog;
    WorkloadModeStateService workloadMode;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3Journal", &journal);
    engine.rootContext()->setContextProperty("fa3Preferences", &preferences);
    engine.rootContext()->setContextProperty("fa3Devices", &devices);
    engine.rootContext()->setContextProperty("fa3ChatFiles", &chatFiles);
    engine.rootContext()->setContextProperty("fa3ModelLibrary", &modelLibrary);
    engine.rootContext()->setContextProperty("fa3OrchestrationMonitor", &orchestrationMonitor);
    engine.rootContext()->setContextProperty("fa3McpControl", &mcpControl);
    engine.rootContext()->setContextProperty("fa3McpGateway", &mcpGateway);
    engine.rootContext()->setContextProperty("fa3AppCatalog", &appCatalog);
    engine.rootContext()->setContextProperty("fa3SessionVault", &sessionVault);
    engine.rootContext()->setContextProperty("fa3DecisionFabric", &decisionFabric);
    engine.rootContext()->setContextProperty("fa3ExternalLlmCatalog", &externalLlmCatalog);\n    engine.rootContext()->setContextProperty("fa3EngineSelector", &engineSelector);
    engine.rootContext()->setContextProperty("fa3WorkloadMode", &workloadMode);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }
    return app.exec();
}
