#include <QCoreApplication>
#include <QDBusInterface>
#include <QDBusReply>
#include <QProcess>
#include <QVariantMap>
#include <QUuid>
#include <iostream>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QStringList a = app.arguments();
    if (a.size() < 4 || a.at(1) != QStringLiteral("--domain")) {
        std::cerr << "usage: workmoderun --domain AI|RENDER|GAME command [args...]\n";
        return 64;
    }
    const QString domain = a.at(2).toUpper();
    if (!QStringList{QStringLiteral("AI"),QStringLiteral("RENDER"),QStringLiteral("GAME")}.contains(domain))
        return 64;
    const QString program = a.at(3);
    const QStringList programArgs = a.mid(4);

    QProcess child;
    child.setProgram(program);
    child.setArguments(programArgs);
    child.setProcessChannelMode(QProcess::ForwardedChannels);
    child.start();
    if (!child.waitForStarted())
        return 69;

    const QString id = QStringLiteral("workmoderun-") + QUuid::createUuid().toString(QUuid::WithoutBraces);
    QDBusInterface iface(QStringLiteral("org.workloadmode.Manager1"),
                         QStringLiteral("/org/workloadmode/Manager1"),
                         QStringLiteral("org.workloadmode.Manager1"),
                         QDBusConnection::sessionBus());
    if (!iface.isValid()) {
        child.terminate();
        child.waitForFinished(2000);
        return 70;
    }
    QVariantMap w;
    w.insert(QStringLiteral("domain"), domain);
    w.insert(QStringLiteral("workload_id"), id);
    w.insert(QStringLiteral("integration"), QStringLiteral("COORDINATED"));
    w.insert(QStringLiteral("pid"), child.processId());
    QDBusReply<QVariantMap> reg = iface.call(QStringLiteral("RegisterWorkload"), w);
    if (!reg.isValid() || !reg.value().value(QStringLiteral("accepted")).toBool()) {
        child.terminate();
        child.waitForFinished(2000);
        return 77;
    }
    child.waitForFinished(-1);
    iface.call(QStringLiteral("ReleaseWorkload"), id);
    if (child.exitStatus() != QProcess::NormalExit)
        return 128;
    return child.exitCode();
}
