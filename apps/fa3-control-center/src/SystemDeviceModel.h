#pragma once

#include <QObject>
#include <QVariantList>

class SystemDeviceModel final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList inventory READ inventory NOTIFY inventoryChanged)
    Q_PROPERTY(QString lastRefresh READ lastRefresh NOTIFY inventoryChanged)

public:
    explicit SystemDeviceModel(QObject *parent = nullptr);

    QVariantList inventory() const { return m_inventory; }
    QString lastRefresh() const { return m_lastRefresh; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantList byKind(const QString &kind) const;

signals:
    void inventoryChanged();

private:
    void addRow(const QString &kind, const QString &id, const QString &title,
                const QString &detail, const QString &status);
    QString readTextFile(const QString &path) const;

    QVariantList m_inventory;
    QString m_lastRefresh;
};
