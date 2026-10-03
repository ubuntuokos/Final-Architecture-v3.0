#pragma once

#include <QObject>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

class SCPSettingsService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString fabricState READ fabricState NOTIFY stateChanged)
    Q_PROPERTY(QVariantList components READ components NOTIFY stateChanged)
    Q_PROPERTY(QVariantList policyLayers READ policyLayers CONSTANT)
    Q_PROPERTY(QString lastDraftPath READ lastDraftPath NOTIFY draftCreated)

public:
    explicit SCPSettingsService(QObject *parent = nullptr);

    QString fabricState() const;
    QVariantList components() const;
    QVariantList policyLayers() const;
    QString lastDraftPath() const;

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap evaluateRequest(const QVariantMap &context) const;
    Q_INVOKABLE QString createDraftChange(const QString &scope,
                                           const QString &key,
                                           const QVariant &value);

signals:
    void stateChanged();
    void draftCreated();

private:
    QVariantMap componentRow(const QString &name,
                             const QString &role,
                             const QStringList &executables,
                             bool mandatory) const;

    QString m_fabricState;
    QVariantList m_components;
    QString m_lastDraftPath;
};
