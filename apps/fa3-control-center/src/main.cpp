#include "Fa3RepositoryModel.h"
#include "ResourceTelemetry.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQuickItem>
#include <QQuickWindow>
#include <QUrl>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3 Control Center");
    QCoreApplication::setApplicationVersion("0.2.0");
    QCoreApplication::setOrganizationName("Final Architecture");

    Fa3RepositoryModel repository;
    ResourceTelemetry resourceTelemetry;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Repository", &repository);
    engine.rootContext()->setContextProperty("fa3ResourceTelemetry", &resourceTelemetry);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/Main.qml")));

    if (engine.rootObjects().isEmpty()) {
        return 2;
    }

    auto *window = qobject_cast<QQuickWindow *>(engine.rootObjects().constFirst());
    if (!window) {
        return 3;
    }

    QQmlComponent statusStripComponent(
        &engine,
        QUrl(QStringLiteral("qrc:/qt/qml/FA3/ControlCenter/ResourceStatusStrip.qml")));
    if (statusStripComponent.isError()) {
        qCritical().noquote() << statusStripComponent.errorString();
        return 4;
    }

    QObject *statusStripObject = statusStripComponent.create(engine.rootContext());
    if (!statusStripObject) {
        qCritical().noquote() << statusStripComponent.errorString();
        return 5;
    }
    auto *statusStripItem = qobject_cast<QQuickItem *>(statusStripObject);
    if (!statusStripItem) {
        delete statusStripObject;
        return 6;
    }
    statusStripItem->setParentItem(window->contentItem());
    statusStripItem->setParent(window->contentItem());

    return app.exec();
}
