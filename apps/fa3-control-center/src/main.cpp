#include "AppCatalogService.h"
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
#include <QQmlComponent>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickStyle>
#include <QQuickWindow>
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

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3Journal", &journal);
    engine.rootContext()->setContextProperty("fa3Preferences", &preferences);
    engine.rootContext()->setContextProperty("fa3Devices", &devices);
    engine.rootContext()->setContextProperty("fa3ChatFiles", &chatFiles);
    engine.rootContext()->setContextProperty("fa3ModelLibrary", &modelLibrary);
    engine.rootContext()->setContextProperty("fa3McpControl", &mcpControl);
    engine.rootContext()->setContextProperty("fa3AppCatalog", &appCatalog);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }

    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().constFirst());
    if (!window) {
        return 3;
    }

    QQmlComponent toolsComponent(
        &engine,
        QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/ToolsOverlay.qml")));
    if (toolsComponent.status() != QQmlComponent::Ready) {
        return 4;
    }
    QObject *toolsObject = toolsComponent.create(engine.rootContext());
    auto *toolsItem = qobject_cast<QQuickItem *>(toolsObject);
    if (!toolsItem) {
        delete toolsObject;
        return 5;
    }
    toolsItem->setParent(window->contentItem());
    toolsItem->setParentItem(window->contentItem());

    return app.exec();
}
