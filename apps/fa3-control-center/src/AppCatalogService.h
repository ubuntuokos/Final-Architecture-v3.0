#pragma once

#include <QObject>
#include <QProcess>
#include <QStringList>
#include <QVariantList>

class AppCatalogService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList applications READ applications NOTIFY applicationsChanged)
    Q_PROPERTY(int pendingRequestCount READ pendingRequestCount NOTIFY requestQueueChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(bool installBusy READ installBusy NOTIFY installBusyChanged)

public:
    explicit AppCatalogService(QObject *parent = nullptr);

    QVariantList applications() const { return m_applications; }
    int pendingRequestCount() const { return m_pendingRequestCount; }
    QString lastError() const { return m_lastError; }
    bool installBusy() const { return m_process.state() != QProcess::NotRunning; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap application(const QString &appId) const;
    Q_INVOKABLE bool requestFirstUse(const QString &appId);
    Q_INVOKABLE bool installApproved(const QString &appId);
    Q_INVOKABLE bool launchInstalled(const QString &appId);
    Q_INVOKABLE QString submitApplicationRequest(const QString &sourceUrl,
                                                 const QString &category,
                                                 const QString &rationale);

signals:
    void applicationsChanged();
    void requestQueueChanged();
    void lastErrorChanged();
    void installBusyChanged();
    void installationConfirmationRequired(const QString &appId, const QString &name);
    void operationFinished(const QString &appId,
                           const QString &operation,
                           bool success,
                           const QString &message);
    void applicationRequestQueued(const QString &requestId, const QString &filePath);

private:
    QString discoverRepositoryRoot() const;
    QString requestDirectory() const;
    QString stateDirectory() const;
    bool loadCatalog();
    int indexOf(const QString &appId) const;
    void setRuntimeState(const QString &appId, const QString &state, const QString &message = {});
    void setLastError(const QString &message);
    void refreshPendingRequestCount();
    bool resolveProvisioner(QString *program, QStringList *prefixArguments) const;
    bool startProvisioner(const QString &operation, const QString &appId);
    bool isInstalledFromProbe(const QVariantMap &application) const;
    bool hasInstallMarker(const QString &appId) const;

    QString m_repoRoot;
    QVariantList m_applications;
    int m_pendingRequestCount = 0;
    QString m_lastError;
    QProcess m_process;
    QString m_activeAppId;
    QString m_activeOperation;
};
