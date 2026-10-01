// SPDX-License-Identifier: Apache-2.0
#include "OfficeFabricService.h"

#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setOrganizationName(QStringLiteral("FA3"));
    QCoreApplication::setApplicationName(QStringLiteral("FA3 Office"));

    OfficeFabricService service;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty(QStringLiteral("fa3Office"), &service);
    engine.loadFromModule(QStringLiteral("FA3.Office"), QStringLiteral("Main"));
    if (engine.rootObjects().isEmpty())
        return 1;
    return app.exec();
}
