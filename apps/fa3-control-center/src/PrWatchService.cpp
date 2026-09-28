#include "PrWatchService.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>

PrWatchService::PrWatchService(QObject *parent) : QObject(parent)
{
    const QString xdgState = qEnvironmentVariable("XDG_STATE_HOME");
    const QString base = xdgState.isEmpty()
        ? QDir::homePath() + QStringLiteral("/.local/state")
        : xdgState;
    if (!QDir::isAbsolutePath(base)) {
        m_status = QStringLiteral("BLOCKED_STATE_ROOT_INVALID");
        return;
    }
    m_stateDir = QDir(base).filePath(QStringLiteral("fa3/pr-watch"));
    m_stateFile = QDir(m_stateDir).filePath(QStringLiteral("projection.json"));
    QObject::connect(&m_watcher, &QFileSystemWatcher::fileChanged,
                     this, [this](const QString &) { refresh(); });
    QObject::connect(&m_watcher, &QFileSystemWatcher::directoryChanged,
                     this, [this](const QString &) { refresh(); });
    refresh();
}

void PrWatchService::refresh()
{
    // Never fetch GitHub content or spin up a runner in the GUI.
    m_items.clear();
    m_lastObservedAt.clear();
    const QFileInfo dir(m_stateDir);
    const QFileInfo file(m_stateFile);
    if (dir.exists() && (dir.isSymLink() || !dir.isDir() ||
                         dir.permissions() & (QFile::ReadGroup | QFile::WriteGroup |
                         QFile::ExeGroup | QFile::ReadOther | QFile::WriteOther | QFile::ExeOther))) {
        m_status = QStringLiteral("BLOCKED_UNSAFE_STATE_DIRECTORY");
        emit changed();
        return;
    }
    if (!file.exists()) {
        m_status = QStringLiteral("PENDING_NO_OBSERVATIONS");
        if (dir.exists() && !m_watcher.directories().contains(m_stateDir))
            m_watcher.addPath(m_stateDir);
        emit changed();
        return;
    }
    if (file.isSymLink() || !file.isFile() ||
        file.permissions() & (QFile::ReadGroup | QFile::WriteGroup | QFile::ExeGroup |
                              QFile::ReadOther | QFile::WriteOther | QFile::ExeOther)) {
        m_status = QStringLiteral("BLOCKED_UNSAFE_STATE_FILE");
        emit changed();
        return;
    }
    QFile in(m_stateFile);
    if (!in.open(QIODevice::ReadOnly)) {
        m_status = QStringLiteral("BLOCKED_STATE_UNREADABLE");
        emit changed();
        return;
    }
    QJsonParseError error;
    const auto data = QJsonDocument::fromJson(in.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !data.isObject()) {
        m_status = QStringLiteral("BLOCKED_STATE_INVALID");
        emit changed();
        return;
    }
    const QJsonObject doc = data.object();
    if (doc.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.pr-watch-projection.v1") ||
        doc.value(QStringLiteral("status")).toString() != QStringLiteral("OBSERVATION_ONLY") ||
        doc.value(QStringLiteral("authority")).toBool(true) ||
        doc.value(QStringLiteral("execution_enabled")).toBool(true) ||
        !doc.value(QStringLiteral("items")).isObject()) {
        m_status = QStringLiteral("BLOCKED_AUTHORITY_OR_SCHEMA_DRIFT");
        emit changed();
        return;
    }
    const QJsonObject objects = doc.value(QStringLiteral("items")).toObject();
    for (auto it = objects.cbegin(); it != objects.cend(); ++it) {
        if (!it.value().isObject()) {
            m_status = QStringLiteral("BLOCKED_ITEM_INVALID");
            m_items.clear();
            emit changed();
            return;
        }
        const QJsonObject item = it.value().toObject();
        const QString key = item.value(QStringLiteral("external_key")).toString();
        const QString repo = item.value(QStringLiteral("repository")).toString();
        if (key != it.key() || repo.isEmpty() ||
            item.value(QStringLiteral("canonical_work_item_id")).isString()) {
            // This cache cannot claim a canonical work-item mapping by itself.
            m_status = QStringLiteral("BLOCKED_ITEM_IDENTITY_DRIFT");
            m_items.clear();
            emit changed();
            return;
        }
        m_items.append(item.toVariantMap());
    }
    m_lastObservedAt = doc.value(QStringLiteral("last_observed_at")).toString();
    m_status = QStringLiteral("LOCAL_OBSERVATION_ONLY");
    if (!m_watcher.files().contains(m_stateFile))
        m_watcher.addPath(m_stateFile);
    if (!m_watcher.directories().contains(m_stateDir))
        m_watcher.addPath(m_stateDir);
    emit changed();
}
