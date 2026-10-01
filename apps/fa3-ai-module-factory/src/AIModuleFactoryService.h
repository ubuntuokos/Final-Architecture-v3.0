// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <QObject>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

class AIModuleFactoryService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString fabricState READ fabricState CONSTANT)
    Q_PROPERTY(QVariantList moduleTypes READ moduleTypes CONSTANT)
    Q_PROPERTY(QVariantList sourceApplications READ sourceApplications CONSTANT)
    Q_PROPERTY(QVariantMap lastPlan READ lastPlan NOTIFY planChanged)
    Q_PROPERTY(QString lastDraftPath READ lastDraftPath NOTIFY draftCreated)

public:
    explicit AIModuleFactoryService(QObject *parent = nullptr);

    QString fabricState() const;
    QVariantList moduleTypes() const;
    QVariantList sourceApplications() const;
    QVariantMap lastPlan() const;
    QString lastDraftPath() const;

    Q_INVOKABLE QVariantMap qualifyArtifact(const QVariantMap &artifact,
                                            const QString &moduleType) const;
    Q_INVOKABLE QVariantMap preparePlan(const QString &moduleName,
                                        const QString &moduleType,
                                        const QVariantList &artifacts,
                                        bool aiEnabled);
    Q_INVOKABLE QString saveLastPlanDraft();

signals:
    void planChanged();
    void draftCreated();

private:
    static bool trainingRequired(const QString &moduleType);
    static bool supportedModuleType(const QString &moduleType);
    static QString safeName(QString value);

    QVariantMap m_lastPlan;
    QString m_lastDraftPath;
};
