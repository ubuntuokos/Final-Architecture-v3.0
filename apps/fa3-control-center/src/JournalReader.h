#pragma once

#include <QObject>
#include <QVariantList>

class JournalReader final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList entries READ entries NOTIFY entriesChanged)
    Q_PROPERTY(QString statusText READ statusText NOTIFY entriesChanged)
public:
    explicit JournalReader(QObject *parent=nullptr);
    QVariantList entries() const { return m_entries; }
    QString statusText() const { return m_statusText; }
    Q_INVOKABLE void refresh(int maxEntries=300);
signals:
    void entriesChanged();
private:
    QVariantList m_entries;
    QString m_statusText;
};
