#pragma once

#include <QObject>
#include <QJsonObject>
#include <QUrl>
#include <QVariantMap>
#include <QStringList>

// Native FA3 Control Center projection over the governed local screenplay CLI.
// No direct model calls, no independent project authority or production publish.
class ScreenplayService final : public QObject {
    Q_OBJECT
    Q_PROPERTY(QVariantMap document READ document NOTIFY documentChanged)
    Q_PROPERTY(QVariantMap breakdown READ breakdown NOTIFY breakdownChanged)
    Q_PROPERTY(QVariantMap handoff READ handoff NOTIFY handoffChanged)
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)
    Q_PROPERTY(QString receipt READ receipt NOTIFY receiptChanged)
public:
    explicit ScreenplayService(QObject *parent = nullptr);
    QVariantMap document() const { return m_document.toVariantMap(); }
    QVariantMap breakdown() const { return m_breakdown.toVariantMap(); }
    QVariantMap handoff() const { return m_handoff.toVariantMap(); }
    QString error() const { return m_error; }
    QString receipt() const { return m_receipt; }
    Q_INVOKABLE bool importText(const QString &text, const QString &format, const QString &profile);
    Q_INVOKABLE bool importFile(const QUrl &url, const QString &format, const QString &profile);
    Q_INVOKABLE bool loadCanonical(const QUrl &url);
    Q_INVOKABLE bool saveCanonical(const QUrl &url, bool replace = false);
    Q_INVOKABLE bool exportSource(const QUrl &url, const QString &format, bool replace = false);
    Q_INVOKABLE bool derive(bool refreshAffected = false);
    Q_INVOKABLE bool review(const QString &id, const QString &decision, const QString &actor);
    Q_INVOKABLE bool fork(const QString &branchId);
    Q_INVOKABLE bool editHeading(const QString &sceneId, const QString &heading);
    Q_INVOKABLE bool buildHandoffPreview();
signals:
    void documentChanged();
    void breakdownChanged();
    void handoffChanged();
    void errorChanged();
    void receiptChanged();
private:
    bool run(const QStringList &args, const QString &resultFile, QJsonObject &result, bool acceptBlocker = false);
    bool saveTemp(const QString &path, const QByteArray &data);
    bool importSource(const QString &text, const QString &format, const QString &profile);
    bool writeCanonical(const QString &path, bool replace);
    QString cliPath() const;
    void setError(const QString &message);
    void clearDerived();
    QJsonObject m_document;
    QJsonObject m_breakdown;
    QJsonObject m_handoff;
    QString m_error;
    QString m_receipt;
};
