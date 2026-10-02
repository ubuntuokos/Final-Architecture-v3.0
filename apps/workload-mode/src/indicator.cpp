#include <QApplication>
#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusReply>
#include <QIcon>
#include <QMenu>
#include <QSystemTrayIcon>
#include <QVariantMap>

class Tray final : public QSystemTrayIcon
{
    Q_OBJECT
public:
    Tray() : QSystemTrayIcon(QIcon::fromTheme(QStringLiteral("applications-system")))
    {
        m_menu.addAction(QStringLiteral("Workload Mode"));
        m_menu.addSeparator();
        m_mode = m_menu.addAction(QStringLiteral("Mode: DEGRADED"));
        m_authority = m_menu.addAction(QStringLiteral("Authority: UNAVAILABLE"));
        m_peers = m_menu.addAction(QStringLiteral("Coexistence: none"));
        auto *quit = m_menu.addAction(QStringLiteral("Quit indicator"));
        connect(quit, &QAction::triggered, qApp, &QCoreApplication::quit);
        setContextMenu(&m_menu);
        setToolTip(QStringLiteral("Workload Mode: DEGRADED"));
        QDBusConnection::sessionBus().connect(QStringLiteral("org.workloadmode.Manager1"),
            QStringLiteral("/org/workloadmode/Manager1"), QStringLiteral("org.workloadmode.Manager1"),
            QStringLiteral("StateChanged"), this, SLOT(updateState(QVariantMap)));
        refresh();
    }
public slots:
    void updateState(const QVariantMap &s)
    {
        const QString mode=s.value(QStringLiteral("effective_mode"),QStringLiteral("DEGRADED")).toString();
        const QString authority=s.value(QStringLiteral("authority"),QStringLiteral("UNAVAILABLE")).toString();
        const QStringList peers=s.value(QStringLiteral("coexistence_peers")).toStringList();
        m_mode->setText(QStringLiteral("Mode: ")+mode);
        m_authority->setText(QStringLiteral("Authority: ")+authority);
        m_peers->setText(QStringLiteral("Coexistence: ")+(peers.isEmpty()?QStringLiteral("none"):peers.join(QStringLiteral(", "))));
        setToolTip(QStringLiteral("Workload Mode: ")+mode+QStringLiteral(" · ")+authority);
    }
private:
    void refresh()
    {
        QDBusInterface i(QStringLiteral("org.workloadmode.Manager1"),QStringLiteral("/org/workloadmode/Manager1"),
                         QStringLiteral("org.workloadmode.Manager1"),QDBusConnection::sessionBus());
        QDBusReply<QVariantMap> r=i.call(QStringLiteral("Status"));
        if(r.isValid()) updateState(r.value());
    }
    QMenu m_menu;
    QAction *m_mode=nullptr,*m_authority=nullptr,*m_peers=nullptr;
};

#include "indicator.moc"

int main(int argc,char **argv)
{
    QApplication app(argc,argv);
    app.setQuitOnLastWindowClosed(false);
    if(!QSystemTrayIcon::isSystemTrayAvailable()) return 0;
    Tray tray;
    tray.show();
    return app.exec();
}
