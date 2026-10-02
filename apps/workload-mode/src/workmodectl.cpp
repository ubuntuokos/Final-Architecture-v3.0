#include <QCoreApplication>
#include <QDBusInterface>
#include <QDBusReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QVariantMap>
#include <iostream>

static QDBusInterface manager()
{
    return QDBusInterface(QStringLiteral("org.workloadmode.Manager1"),
                          QStringLiteral("/org/workloadmode/Manager1"),
                          QStringLiteral("org.workloadmode.Manager1"),
                          QDBusConnection::sessionBus());
}
static void printMap(const QVariantMap &m)
{
    std::cout << QJsonDocument(QJsonObject::fromVariantMap(m)).toJson(QJsonDocument::Indented).constData();
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const QStringList a = app.arguments();
    if (a.size() < 2) {
        std::cerr << "usage: workmodectl status|doctor|register DOMAIN ID INTEGRATION [PID]|release ID\n";
        return 64;
    }
    auto iface = manager();
    if (!iface.isValid()) {
        std::cerr << "workmoded unavailable\n";
        return 69;
    }
    const QString op = a.at(1);
    if (op == QStringLiteral("status") || op == QStringLiteral("doctor")) {
        QDBusReply<QVariantMap> r = iface.call(QStringLiteral("Status"));
        if (!r.isValid()) return 70;
        printMap(r.value());
        return 0;
    }
    if (op == QStringLiteral("register") && a.size() >= 5) {
        QVariantMap w;
        w.insert(QStringLiteral("domain"), a.at(2));
        w.insert(QStringLiteral("workload_id"), a.at(3));
        w.insert(QStringLiteral("integration"), a.at(4).toUpper());
        if (a.size() > 5) w.insert(QStringLiteral("pid"), a.at(5).toLongLong());
        QDBusReply<QVariantMap> r = iface.call(QStringLiteral("RegisterWorkload"), w);
        if (!r.isValid()) return 70;
        printMap(r.value());
        return r.value().value(QStringLiteral("accepted")).toBool() ? 0 : 77;
    }
    if (op == QStringLiteral("release") && a.size() == 3) {
        QDBusReply<QVariantMap> r = iface.call(QStringLiteral("ReleaseWorkload"), a.at(2));
        if (!r.isValid()) return 70;
        printMap(r.value());
        return 0;
    }
    return 64;
}
