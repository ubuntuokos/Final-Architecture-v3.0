#pragma once

#include <QObject>
#include <QSettings>
#include <QVariant>

class PreferenceStore final : public QObject
{
    Q_OBJECT

public:
    explicit PreferenceStore(QObject *parent = nullptr);

    Q_INVOKABLE QVariant value(const QString &key, const QVariant &fallback = QVariant()) const;
    Q_INVOKABLE void setValue(const QString &key, const QVariant &value);
    Q_INVOKABLE void remove(const QString &key);
    Q_INVOKABLE QString normalizeShortcut(const QString &sequence) const;

signals:
    void preferenceChanged(const QString &key, const QVariant &value);

private:
    mutable QSettings m_settings;
};
