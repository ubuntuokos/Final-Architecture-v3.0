#pragma once
// SPDX-License-Identifier: Apache-2.0

#include <QObject>
#include <QVariantList>

class ProductEntitlementService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList operatingLevels READ operatingLevels NOTIFY catalogChanged)
    Q_PROPERTY(QVariantList applications READ applications NOTIFY catalogChanged)
    Q_PROPERTY(QVariantList domainPacks READ domainPacks NOTIFY catalogChanged)
    Q_PROPERTY(QString status READ status NOTIFY catalogChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY catalogChanged)

public:
    explicit ProductEntitlementService(const QString &repoRoot, QObject *parent = nullptr);

    QVariantList operatingLevels() const { return m_operatingLevels; }
    QVariantList applications() const { return m_applications; }
    QVariantList domainPacks() const { return m_domainPacks; }
    QString status() const { return m_status; }
    QString lastError() const { return m_lastError; }

    Q_INVOKABLE void refresh();

signals:
    void catalogChanged();

private:
    QVariantMap readCanonical(const QString &fileName) const;
    QString m_repoRoot;
    QVariantList m_operatingLevels;
    QVariantList m_applications;
    QVariantList m_domainPacks;
    QString m_status;
    QString m_lastError;
};
