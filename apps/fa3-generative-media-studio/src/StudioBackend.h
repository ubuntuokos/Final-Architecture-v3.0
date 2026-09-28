#pragma once

#include <QObject>
#include <QStringList>

class StudioBackend final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString statusText READ statusText NOTIFY statusTextChanged)
    Q_PROPERTY(QString lastRequestPath READ lastRequestPath NOTIFY lastRequestPathChanged)
    Q_PROPERTY(QStringList capabilities READ capabilities CONSTANT)

public:
    explicit StudioBackend(QObject *parent = nullptr);
    QString statusText() const;
    QString lastRequestPath() const;
    QStringList capabilities() const;

    Q_INVOKABLE bool compileRequest(
        const QString &capability,
        const QString &prompt,
        int durationSeconds,
        const QString &aspectRatio,
        const QString &referencesText);

signals:
    void statusTextChanged();
    void lastRequestPathChanged();

private:
    void setStatusText(const QString &value);
    void setLastRequestPath(const QString &value);
    static bool isVideoCapability(const QString &capability);
    static bool isKnownCapability(const QString &capability);

    QString m_statusText;
    QString m_lastRequestPath;
};
