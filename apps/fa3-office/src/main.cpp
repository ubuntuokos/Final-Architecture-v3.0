// SPDX-License-Identifier: Apache-2.0
#include "OfficeFabricService.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QUrl>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setOrganizationName(QStringLiteral("FA3"));
    QCoreApplication::setApplicationName(QStringLiteral("FA3 Office"));

    OfficeFabricService service;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("fa3Office"), &service);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/Office/Main.qml")));
    return engine.rootObjects().isEmpty() ? 2 : app.exec();
}
