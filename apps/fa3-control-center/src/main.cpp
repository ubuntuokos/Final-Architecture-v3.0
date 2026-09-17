#include "AppCatalogService.h"
#include "LanguageInterpreterService.h"
#include "LlmfitClient.h"
#include "OpenModelDbService.h"
#include "ResourceTelemetry.h"
#include "ChatFileService.h"
#include "Fa3RepositoryModel.h"
#include "JournalService.h"
#include "ModelLibraryService.h"
#include "McpControlService.h"
#include "PreferenceStore.h"
#include "SystemDeviceModel.h"

#include <QColor>
#include <QGuiApplication>
#include <QPalette>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QQuickItem>
#include <QQmlComponent>
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
    McpControlService mcpControl;
    AppCatalogService appCatalog;
    ResourceTelemetry resourceTelemetry;
    OpenModelDbService openModelDb;
    LlmfitClient llmfitClient;
    LanguageInterpreterService interpreter;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3Journal", &journal);
    engine.rootContext()->setContextProperty("fa3Preferences", &preferences);
    engine.rootContext()->setContextProperty("fa3Devices", &devices);
    engine.rootContext()->setContextProperty("fa3ChatFiles", &chatFiles);
    engine.rootContext()->setContextProperty("fa3ModelLibrary", &modelLibrary);
    engine.rootContext()->setContextProperty("fa3McpControl", &mcpControl);
    engine.rootContext()->setContextProperty("fa3AppCatalog", &appCatalog);
    engine.rootContext()->setContextProperty("fa3ResourceTelemetry", &resourceTelemetry);
    engine.rootContext()->setContextProperty("fa3OpenModelDb", &openModelDb);
    engine.rootContext()->setContextProperty("llmfitClient", &llmfitClient);
    engine.rootContext()->setContextProperty("fa3Interpreter", &interpreter);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }
    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().constFirst());
    if (!window) {
        return 3;
    }

    auto attachOverlay = [&](const QString &qmlFile) -> bool {
        QQmlComponent component(
            &engine,
            QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/") + qmlFile));
        if (component.status() != QQmlComponent::Ready) {
            return false;
        }
        QObject *object = component.create(engine.rootContext());
        auto *item = qobject_cast<QQuickItem *>(object);
        if (!item) {
            delete object;
            return false;
        }
        item->setParent(window->contentItem());
        item->setParentItem(window->contentItem());
        return true;
    };

    if (!attachOverlay(QStringLiteral("ResourceStatusStrip.qml"))) {
        return 4;
    }
    if (!attachOverlay(QStringLiteral("ToolsOverlay.qml"))) {
        return 5;
    }
    if (!attachOverlay(QStringLiteral("OperationsExtensionsOverlay.qml"))) {
        return 6;
    }

    return app.exec();
}
