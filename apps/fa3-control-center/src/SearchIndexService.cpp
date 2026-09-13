#include "SearchIndexService.h"

#include <QDir>
#include <QDirIterator>
#include <QFileInfo>

QVariantList SearchIndexService::searchProjects(const QString &rootPath, const QString &query, int limit) const
{
    QVariantList out;
    const QString root = QDir::cleanPath(QDir::fromNativeSeparators(rootPath));
    const QFileInfo rootInfo(root);
    if (!rootInfo.exists() || !rootInfo.isDir()) return out;

    const QString needle = query.trimmed();
    const int boundedLimit = qBound(1, limit, 250);
    int scanned = 0;
    QDirIterator it(root, QDir::AllEntries | QDir::NoDotAndDotDot, QDirIterator::Subdirectories);
    while (it.hasNext() && out.size() < boundedLimit && scanned < 5000) {
        const QString path = it.next();
        ++scanned;
        const QFileInfo info(path);
        if (info.isSymLink()) continue;
        if (!needle.isEmpty() && !info.fileName().contains(needle, Qt::CaseInsensitive)
            && !path.contains(needle, Qt::CaseInsensitive)) continue;
        QVariantMap row;
        row.insert(QStringLiteral("name"), info.fileName());
        row.insert(QStringLiteral("path"), path);
        row.insert(QStringLiteral("type"), info.isDir() ? QStringLiteral("directory") : QStringLiteral("file"));
        out.push_back(row);
    }
    return out;
}

QVariantMap SearchIndexService::conversationIndexStatus() const
{
    return {
        {QStringLiteral("available"), false},
        {QStringLiteral("reason"), QStringLiteral("NO_CANONICAL_CONVERSATION_INDEX_ADAPTER")},
        {QStringLiteral("detail"), QStringLiteral("Conversation search remains unavailable until a canonical read-only conversation index adapter is materialized.")}
    };
}
