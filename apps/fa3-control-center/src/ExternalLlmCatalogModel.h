#pragma once

#include <QObject>
#include <QString>
#include <QVariantList>

class ExternalLlmCatalogModel final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList providers READ providers NOTIFY catalogChanged)
    Q_PROPERTY(QString status READ status NOTIFY catalogChanged)
    Q_PROPERTY(QString sourceCommit READ sourceCommit NOTIFY catalogChanged)
    Q_PROPERTY(QString catalogPath READ catalogPath CONSTANT)

public:
    explicit ExternalLlmCatalogModel(QObject *parent = nullptr);

    QVariantList providers() const;
    QString status() const;
    QString sourceCommit() const;
    QString catalogPath() const;

    Q_INVOKABLE bool reload();

signals:
    void catalogChanged();

private:
    QVariantList m_providers;
    QString m_status = QStringLiteral("NOT_LOADED");
    QString m_sourceCommit;
    QString m_catalogPath;
};
