#include "PreferenceStore.h"

#include <QKeySequence>

PreferenceStore::PreferenceStore(QObject *parent)
    : QObject(parent), m_settings()
{
}

QVariant PreferenceStore::value(const QString &key, const QVariant &fallback) const
{
    return m_settings.value(key, fallback);
}

void PreferenceStore::setValue(const QString &key, const QVariant &value)
{
    const auto cleanKey = key.trimmed();
    if (cleanKey.isEmpty()) return;
    if (m_settings.value(cleanKey) == value) return;
    m_settings.setValue(cleanKey, value);
    m_settings.sync();
    emit preferenceChanged(cleanKey, value);
}

void PreferenceStore::remove(const QString &key)
{
    const auto cleanKey = key.trimmed();
    if (cleanKey.isEmpty()) return;
    m_settings.remove(cleanKey);
    m_settings.sync();
    emit preferenceChanged(cleanKey, QVariant());
}

QString PreferenceStore::normalizeShortcut(const QString &sequence) const
{
    const auto trimmed = sequence.trimmed();
    if (trimmed.isEmpty()) return {};
    const auto parsed = QKeySequence::fromString(trimmed, QKeySequence::PortableText);
    return parsed.toString(QKeySequence::PortableText);
}
