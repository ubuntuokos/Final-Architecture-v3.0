#include <QGuiApplication>
#include <QQmlApplicationEngine>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QGuiApplication::setApplicationName(QStringLiteral("FA3 Communications Hub"));
    QGuiApplication::setOrganizationName(QStringLiteral("FA3"));

    QQmlApplicationEngine engine;
    engine.loadFromModule("FA3.CommunicationsHub", "Main");
    if (engine.rootObjects().isEmpty())
        return 1;
    return app.exec();
}
