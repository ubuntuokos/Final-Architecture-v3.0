#pragma once

#include <QObject>
#include <QUrl>
#include <QVariantMap>

class ChatFileService final : public QObject
{
    Q_OBJECT

public:
    explicit ChatFileService(QObject *parent = nullptr);

    Q_INVOKABLE QVariantMap inspectLocalFile(const QUrl &url) const;
    Q_INVOKABLE QVariantMap saveTextFile(const QUrl &destination, const QString &text) const;
    Q_INVOKABLE QVariantMap copyLocalFile(const QUrl &source, const QUrl &destination) const;

private:
    static QString analysisClassFor(const QString &mimeName, const QString &suffix);
    static QString humanReadableSize(qint64 bytes);
};
