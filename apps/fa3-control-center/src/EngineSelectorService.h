#pragma once

#include <QObject>
#include <QSet>
#include <QVariantList>
#include <QVariantMap>

class EngineSelectorService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList engines READ engines NOTIFY catalogChanged)
    Q_PROPERTY(QString lastRefresh READ lastRefresh NOTIFY catalogChanged)

public:
    explicit EngineSelectorService(const QString &repoRoot, QObject *parent = nullptr);

    QVariantList engines() const { return m_engines; }
    QString lastRefresh() const { return m_lastRefresh; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantList filterEngines(const QString &query,
                                            const QString &engineClass,
                                            bool localAllowed,
                                            bool lanAllowed,
                                            bool cloudAllowed,
                                            bool showUnavailable) const;
    Q_INVOKABLE QVariantMap prepareSelection(const QString &engineId,
                                             const QString &scope,
                                             const QString &fallbackMode) const;
    Q_INVOKABLE void toggleCompare(const QString &engineId, bool enabled);
    Q_INVOKABLE QVariantList prepareComparison() const;

signals:
    void catalogChanged();

private:
    QVariantMap readObject(const QString &relativePath) const;
    QVariant resolvePointer(const QVariantMap &object, const QString &pointer) const;
    static QStringList strings(const QVariant &value);
    static QString healthFromProvider(const QVariantMap &provider);
    static QStringList executionModes(const QVariantMap &provider, const QStringList &defaults);
    QVariantMap engineById(const QString &engineId) const;

    QString m_repoRoot;
    QVariantList m_engines;
    QSet<QString> m_compareIds;
    QString m_lastRefresh;
};
