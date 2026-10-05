// SPDX-License-Identifier: Apache-2.0
#include "AIModuleFactoryService.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QUrl>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3 AI Module Factory");
    QCoreApplication::setApplicationVersion("0.1.0");
    QCoreApplication::setOrganizationName("FA3");
    QQuickStyle::setStyle(QStringLiteral("Basic"));

    AIModuleFactoryService factory;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3ModuleFactory", &factory);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/AIModuleFactory/Main.qml")));
    return engine.rootObjects().isEmpty() ? 2 : app.exec();
}
