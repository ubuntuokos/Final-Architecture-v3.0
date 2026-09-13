#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class SearchIndexService final : public QObject
{
    Q_OBJECT
public:
    explicit SearchIndexService(QObject *parent = nullptr) : QObject(parent) {}

    Q_INVOKABLE QVariantList searchProjects(const QString &rootPath, const QString &query, int limit = 100) const;
    Q_INVOKABLE QVariantMap conversationIndexStatus() const;
};
