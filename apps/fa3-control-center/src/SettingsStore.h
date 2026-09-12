#pragma once

#include <QObject>
#include <QVariant>
#include <QVariantMap>

class SettingsStore final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(qreal uiScale READ uiScale WRITE setUiScale NOTIFY uiScaleChanged)
    Q_PROPERTY(int baseFontSize READ baseFontSize WRITE setBaseFontSize NOTIFY baseFontSizeChanged)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY languageChanged)
    Q_PROPERTY(QString themeMode READ themeMode WRITE setThemeMode NOTIFY themeModeChanged)
    Q_PROPERTY(QString configFilePath READ configFilePath CONSTANT)

public:
    explicit SettingsStore(QObject *parent = nullptr);

    qreal uiScale() const;
    int baseFontSize() const;
    QString language() const;
    QString themeMode() const;
    QString configFilePath() const;

    void setUiScale(qreal value);
    void setBaseFontSize(int value);
    void setLanguage(const QString &value);
    void setThemeMode(const QString &value);

    Q_INVOKABLE QVariant value(const QString &key, const QVariant &fallback = QVariant()) const;
    Q_INVOKABLE void setValue(const QString &key, const QVariant &value);
    Q_INVOKABLE QString chooseDirectory(const QString &title, const QString &initialPath = QString()) const;
    Q_INVOKABLE QVariantMap pathStatus(const QString &path) const;
    Q_INVOKABLE bool validShortcut(const QString &sequence) const;
    Q_INVOKABLE QString shortcutConflict(const QString &settingKey, const QString &sequence) const;
    Q_INVOKABLE void resetGroup(const QString &group);
    Q_INVOKABLE void resetAll();

signals:
    void uiScaleChanged();
    void baseFontSizeChanged();
    void languageChanged();
    void themeModeChanged();
    void settingChanged(const QString &key);
    void settingsReset();

private:
    QVariant defaultForKey(const QString &key) const;
    void persist(const QString &key, const QVariant &value);
};
