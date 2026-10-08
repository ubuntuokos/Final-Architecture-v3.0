#include "SCPSettingsService.h"

#include <QColor>
#include <QGuiApplication>
#include <QPalette>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QUrl>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QCoreApplication::setApplicationName("FA3 SCP Manager");
    QCoreApplication::setApplicationVersion("0.1.0");
    QCoreApplication::setOrganizationName("Final Architecture");

    QQuickStyle::setStyle(QStringLiteral("Basic"));

    QPalette palette;
    palette.setColor(QPalette::Window, QColor("#07111f"));
    palette.setColor(QPalette::WindowText, QColor("#f5f8fc"));
    palette.setColor(QPalette::Base, QColor("#0b1728"));
    palette.setColor(QPalette::Text, QColor("#f5f8fc"));
    palette.setColor(QPalette::Button, QColor("#10243a"));
    palette.setColor(QPalette::ButtonText, QColor("#f5f8fc"));
    palette.setColor(QPalette::Highlight, QColor("#25a7ff"));
    palette.setColor(QPalette::HighlightedText, QColor("#ffffff"));
    app.setPalette(palette);

    SCPSettingsService scp;

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("fa3Scp", &scp);
    engine.load(QUrl(QStringLiteral("qrc:/qt/qml/FA3/SCPManager/Main.qml")));

    return engine.rootObjects().isEmpty() ? 2 : app.exec();
}
