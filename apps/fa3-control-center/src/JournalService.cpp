#include "JournalService.h"

#include <QCryptographicHash>
#include <QDateTime>
#include <QDesktopServices>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QSaveFile>
#include <QSet>
#include <QStandardPaths>
#include <QUrl>
#include <QUuid>

namespace {
constexpr int kPolicyMaxActiveEvents = 5000;
constexpr int kPolicyMaxAgeDays = 30;

QString normalizeDomain(const QString &value)
{
    const auto domain = value.trimmed().toUpper();
    return domain.isEmpty() ? QStringLiteral("EVENT") : domain;
}

QString normalizeLifecycle(const QString &value)
{
    const auto lifecycle = value.trimmed().toUpper();
    return lifecycle.isEmpty() ? QStringLiteral("RECORDED") : lifecycle;
}
}

JournalService::JournalService(QObject *parent)
    : QObject(parent)
{
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    m_storageRoot = QDir(base).filePath(QStringLiteral("journal"));
    ensureLayout();
    refresh();
}

QString JournalService::activeLogPath() const
{
    return QDir(m_storageRoot).filePath(QStringLiteral("events/active.jsonl"));
}

QString JournalService::archivesPath() const
{
    return QDir(m_storageRoot).filePath(QStringLiteral("archives"));
}

QString JournalService::exportsPath() const
{
    return QDir(m_storageRoot).filePath(QStringLiteral("exports"));
}

QString JournalService::trashPath() const
{
    return QDir(m_storageRoot).filePath(QStringLiteral("trash"));
}

bool JournalService::ensureLayout()
{
    QDir root(m_storageRoot);
    if (!root.mkpath(QStringLiteral("events")) ||
        !root.mkpath(QStringLiteral("archives")) ||
        !root.mkpath(QStringLiteral("exports")) ||
        !root.mkpath(QStringLiteral("trash"))) {
        return false;
    }
    QFile file(activeLogPath());
    if (!file.exists()) {
        if (!file.open(QIODevice::WriteOnly)) return false;
        file.close();
    }
    return true;
}

bool JournalService::appendObject(const QJsonObject &object)
{
    if (!ensureLayout()) return false;
    QFile file(activeLogPath());
    if (!file.open(QIODevice::WriteOnly | QIODevice::Append | QIODevice::Text)) return false;
    const auto line = QJsonDocument(object).toJson(QJsonDocument::Compact) + '\n';
    return file.write(line) == line.size();
}

QJsonArray JournalService::activeObjects() const
{
    QJsonArray result;
    QFile file(activeLogPath());
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return result;
    while (!file.atEnd()) {
        const auto line = file.readLine().trimmed();
        if (line.isEmpty()) continue;
        QJsonParseError error;
        const auto doc = QJsonDocument::fromJson(line, &error);
        if (error.error == QJsonParseError::NoError && doc.isObject()) result.append(doc.object());
    }
    return result;
}

QByteArray JournalService::canonicalPayload(const QJsonArray &events)
{
    return QJsonDocument(events).toJson(QJsonDocument::Compact);
}

QString JournalService::digestFor(const QJsonArray &events)
{
    return QString::fromLatin1(QCryptographicHash::hash(canonicalPayload(events), QCryptographicHash::Sha256).toHex());
}

QString JournalService::archiveFileName(const QString &archiveId)
{
    return archiveId + QStringLiteral(".fa3journal.json");
}

QJsonObject JournalService::readArchive(const QString &fileName, QString *error) const
{
    const auto clean = QFileInfo(fileName).fileName();
    QFile file(QDir(archivesPath()).filePath(clean));
    if (!file.open(QIODevice::ReadOnly)) {
        if (error) *error = QStringLiteral("ARCHIVE_OPEN_FAILED");
        return {};
    }
    QJsonParseError parseError;
    const auto doc = QJsonDocument::fromJson(file.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
        if (error) *error = QStringLiteral("ARCHIVE_PARSE_FAILED");
        return {};
    }
    return doc.object();
}

QString JournalService::createArchive(const QJsonArray &events, const QString &reason, bool clearActive)
{
    if (events.isEmpty()) return QStringLiteral("NO_EVENTS_TO_ARCHIVE");
    if (!ensureLayout()) return QStringLiteral("STORAGE_LAYOUT_FAILED");

    const auto stamp = QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMddTHHmmsszzzZ"));
    const auto archiveId = QStringLiteral("FA3-JOURNAL-ARCHIVE-%1").arg(stamp);
    const auto digest = digestFor(events);
    const auto fileName = archiveFileName(archiveId);
    const auto path = QDir(archivesPath()).filePath(fileName);

    QJsonObject manifest{
        {QStringLiteral("schema"), QStringLiteral("fa3.journal-archive.v1")},
        {QStringLiteral("id"), archiveId},
        {QStringLiteral("status"), QStringLiteral("SEALED")},
        {QStringLiteral("created_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("reason"), reason.trimmed().toUpper()},
        {QStringLiteral("event_count"), events.size()},
        {QStringLiteral("digest_algorithm"), QStringLiteral("SHA-256")},
        {QStringLiteral("payload_sha256"), digest},
        {QStringLiteral("retention"), QStringLiteral("POLICY_CONTROLLED")},
        {QStringLiteral("purge_from_gui"), false},
        {QStringLiteral("restore_is_audited"), true},
        {QStringLiteral("events"), events}
    };

    QSaveFile archive(path);
    if (!archive.open(QIODevice::WriteOnly)) return QStringLiteral("ARCHIVE_WRITE_FAILED");
    archive.write(QJsonDocument(manifest).toJson(QJsonDocument::Indented));
    if (!archive.commit()) return QStringLiteral("ARCHIVE_COMMIT_FAILED");

    if (clearActive) {
        QSaveFile active(activeLogPath());
        if (!active.open(QIODevice::WriteOnly) || !active.commit()) return QStringLiteral("ARCHIVE_SEALED_ACTIVE_ROTATION_FAILED");
    }

    refresh();
    return QStringLiteral("ARCHIVED:%1:%2").arg(fileName, digest);
}

void JournalService::recomputeStatistics()
{
    m_systemCount = 0;
    m_conversationCount = 0;
    m_activeProjectCount = 0;
    m_closedProjectCount = 0;
    m_plannedProjectCount = 0;

    QMap<QString, QString> projectStates;
    for (const auto &value : m_events) {
        const auto map = value.toMap();
        const auto domain = map.value(QStringLiteral("domain")).toString();
        if (domain == QStringLiteral("SYSTEM")) ++m_systemCount;
        if (domain == QStringLiteral("CONVERSATION")) ++m_conversationCount;
        const auto projectId = map.value(QStringLiteral("project_id")).toString();
        if (!projectId.isEmpty()) projectStates[projectId] = map.value(QStringLiteral("lifecycle")).toString();
    }

    for (auto it = projectStates.cbegin(); it != projectStates.cend(); ++it) {
        const auto state = it.value().toUpper();
        if (state == QStringLiteral("COMPLETED") || state == QStringLiteral("ARCHIVED") || state == QStringLiteral("CLOSED")) ++m_closedProjectCount;
        else if (state == QStringLiteral("PROPOSED") || state == QStringLiteral("EVALUATING") || state == QStringLiteral("APPROVED") || state == QStringLiteral("PLANNED")) ++m_plannedProjectCount;
        else ++m_activeProjectCount;
    }
}

void JournalService::setResult(const QString &value)
{
    m_lastResult = value;
    emit changed();
}

void JournalService::refresh()
{
    ensureLayout();
    m_events.clear();
    m_archives.clear();

    const auto objects = activeObjects();
    QSet<QString> tombstoned;
    for (const auto &value : objects) {
        const auto object = value.toObject();
        if (object.value(QStringLiteral("event_type")).toString() == QStringLiteral("TOMBSTONE")) {
            tombstoned.insert(object.value(QStringLiteral("target_event_id")).toString());
        }
    }
    for (const auto &value : objects) {
        const auto object = value.toObject();
        const auto id = object.value(QStringLiteral("id")).toString();
        if (!tombstoned.contains(id) || object.value(QStringLiteral("event_type")).toString() == QStringLiteral("TOMBSTONE")) {
            m_events.append(object.toVariantMap());
        }
    }

    QDirIterator archives(archivesPath(), {QStringLiteral("*.fa3journal.json")}, QDir::Files, QDirIterator::NoIteratorFlags);
    while (archives.hasNext()) {
        const auto path = archives.next();
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) continue;
        QJsonParseError error;
        const auto doc = QJsonDocument::fromJson(file.readAll(), &error);
        if (error.error != QJsonParseError::NoError || !doc.isObject()) continue;
        const auto object = doc.object();
        QVariantMap row;
        row.insert(QStringLiteral("id"), object.value(QStringLiteral("id")).toString());
        row.insert(QStringLiteral("file_name"), QFileInfo(path).fileName());
        row.insert(QStringLiteral("created_at"), object.value(QStringLiteral("created_at")).toString());
        row.insert(QStringLiteral("reason"), object.value(QStringLiteral("reason")).toString());
        row.insert(QStringLiteral("event_count"), object.value(QStringLiteral("event_count")).toInt());
        row.insert(QStringLiteral("sha256"), object.value(QStringLiteral("payload_sha256")).toString());
        row.insert(QStringLiteral("status"), object.value(QStringLiteral("status")).toString());
        row.insert(QStringLiteral("bytes"), QFileInfo(path).size());
        m_archives.append(row);
    }

    recomputeStatistics();
    m_lastRefresh = QDateTime::currentDateTime().toString(Qt::ISODate);
    emit changed();
}

QVariantList JournalService::filteredEvents(const QString &domain, const QString &query) const
{
    const auto wantedDomain = domain.trimmed().toUpper();
    const auto needle = query.trimmed();
    QVariantList result;
    for (const auto &value : m_events) {
        const auto map = value.toMap();
        if (!wantedDomain.isEmpty() && wantedDomain != QStringLiteral("ALL") && map.value(QStringLiteral("domain")).toString() != wantedDomain) continue;
        const auto haystack = QStringLiteral("%1 %2 %3 %4 %5 %6")
            .arg(map.value(QStringLiteral("id")).toString(),
                 map.value(QStringLiteral("domain")).toString(),
                 map.value(QStringLiteral("source")).toString(),
                 map.value(QStringLiteral("project_id")).toString(),
                 map.value(QStringLiteral("summary")).toString(),
                 map.value(QStringLiteral("details")).toString());
        if (needle.isEmpty() || haystack.contains(needle, Qt::CaseInsensitive)) result.append(map);
    }
    return result;
}

QString JournalService::recordEvent(const QString &domain,
                                    const QString &source,
                                    const QString &projectId,
                                    const QString &lifecycle,
                                    const QString &summary,
                                    const QString &details)
{
    if (summary.trimmed().isEmpty()) return QStringLiteral("SUMMARY_REQUIRED");
    const auto id = QStringLiteral("FA3-EVT-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces).toUpper());
    QJsonObject object{
        {QStringLiteral("schema"), QStringLiteral("fa3.journal-event.v1")},
        {QStringLiteral("id"), id},
        {QStringLiteral("timestamp"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("event_type"), QStringLiteral("EVENT")},
        {QStringLiteral("domain"), normalizeDomain(domain)},
        {QStringLiteral("source"), source.trimmed().isEmpty() ? QStringLiteral("FA3 Control Center") : source.trimmed()},
        {QStringLiteral("project_id"), projectId.trimmed()},
        {QStringLiteral("lifecycle"), normalizeLifecycle(lifecycle)},
        {QStringLiteral("summary"), summary.trimmed()},
        {QStringLiteral("details"), details.trimmed()},
        {QStringLiteral("integrity"), QStringLiteral("APPEND_ONLY")}
    };
    if (!appendObject(object)) return QStringLiteral("EVENT_APPEND_FAILED");
    refresh();
    return QStringLiteral("RECORDED:%1").arg(id);
}

QString JournalService::archiveAll(const QString &reason)
{
    const auto result = createArchive(activeObjects(), reason.isEmpty() ? QStringLiteral("MANUAL") : reason, true);
    setResult(result);
    return result;
}

QString JournalService::archiveByPolicy()
{
    const auto events = activeObjects();
    if (events.isEmpty()) return QStringLiteral("POLICY_NO_EVENTS");

    bool ageExceeded = false;
    for (const auto &value : events) {
        const auto timestamp = QDateTime::fromString(value.toObject().value(QStringLiteral("timestamp")).toString(), Qt::ISODate);
        if (timestamp.isValid() && timestamp.daysTo(QDateTime::currentDateTimeUtc()) >= kPolicyMaxAgeDays) {
            ageExceeded = true;
            break;
        }
    }
    if (events.size() < kPolicyMaxActiveEvents && !ageExceeded) return QStringLiteral("POLICY_NOT_DUE");
    const auto reason = events.size() >= kPolicyMaxActiveEvents ? QStringLiteral("POLICY_SIZE") : QStringLiteral("POLICY_AGE");
    const auto result = createArchive(events, reason, true);
    setResult(result);
    return result;
}

QString JournalService::verifyArchive(const QString &fileName)
{
    QString error;
    const auto archive = readArchive(fileName, &error);
    if (archive.isEmpty()) return error;
    const auto events = archive.value(QStringLiteral("events")).toArray();
    const auto expected = archive.value(QStringLiteral("payload_sha256")).toString();
    const auto actual = digestFor(events);
    const auto result = expected == actual
        ? QStringLiteral("VERIFY_PASS:%1").arg(actual)
        : QStringLiteral("VERIFY_FAIL:EXPECTED=%1:ACTUAL=%2").arg(expected, actual);
    setResult(result);
    return result;
}

QString JournalService::restoreArchive(const QString &fileName)
{
    QString error;
    const auto archive = readArchive(fileName, &error);
    if (archive.isEmpty()) return error;
    const auto verify = verifyArchive(fileName);
    if (!verify.startsWith(QStringLiteral("VERIFY_PASS:"))) return QStringLiteral("RESTORE_BLOCKED_%1").arg(verify);

    const auto archiveId = archive.value(QStringLiteral("id")).toString();
    const auto events = archive.value(QStringLiteral("events")).toArray();
    int restored = 0;
    for (const auto &value : events) {
        if (!value.isObject()) continue;
        auto object = value.toObject();
        const auto originalId = object.value(QStringLiteral("id")).toString();
        object.insert(QStringLiteral("original_event_id"), originalId);
        object.insert(QStringLiteral("id"), QStringLiteral("FA3-EVT-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces).toUpper()));
        object.insert(QStringLiteral("restored_from"), archiveId);
        object.insert(QStringLiteral("restored_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
        if (appendObject(object)) ++restored;
    }
    recordEvent(QStringLiteral("AUDIT"), QStringLiteral("FA3 Journal Archive"), archiveId,
                QStringLiteral("RESTORED"), QStringLiteral("Journal archive restored"),
                QStringLiteral("Restored %1 events from %2 after SHA-256 verification.").arg(restored).arg(fileName));
    const auto result = QStringLiteral("RESTORE_PASS:%1:%2").arg(archiveId).arg(restored);
    setResult(result);
    return result;
}

QString JournalService::retireArchive(const QString &fileName)
{
    const auto clean = QFileInfo(fileName).fileName();
    const auto source = QDir(archivesPath()).filePath(clean);
    if (!QFileInfo::exists(source)) return QStringLiteral("ARCHIVE_NOT_FOUND");
    if (!ensureLayout()) return QStringLiteral("STORAGE_LAYOUT_FAILED");
    const auto retired = QStringLiteral("%1.%2.retired").arg(clean, QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMddTHHmmssZ")));
    const auto target = QDir(trashPath()).filePath(retired);
    if (!QFile::rename(source, target)) return QStringLiteral("ARCHIVE_RETIRE_FAILED");
    recordEvent(QStringLiteral("AUDIT"), QStringLiteral("FA3 Journal Archive"), QString(),
                QStringLiteral("RETIRED"), QStringLiteral("Archive moved to retention trash"), retired);
    refresh();
    const auto result = QStringLiteral("ARCHIVE_RETIRED:%1").arg(retired);
    setResult(result);
    return result;
}

QString JournalService::softDeleteEvent(const QString &eventId)
{
    if (eventId.trimmed().isEmpty()) return QStringLiteral("EVENT_ID_REQUIRED");
    QJsonObject tombstone{
        {QStringLiteral("schema"), QStringLiteral("fa3.journal-event.v1")},
        {QStringLiteral("id"), QStringLiteral("FA3-EVT-%1").arg(QUuid::createUuid().toString(QUuid::WithoutBraces).toUpper())},
        {QStringLiteral("timestamp"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("event_type"), QStringLiteral("TOMBSTONE")},
        {QStringLiteral("domain"), QStringLiteral("AUDIT")},
        {QStringLiteral("source"), QStringLiteral("FA3 Control Center")},
        {QStringLiteral("project_id"), QString()},
        {QStringLiteral("lifecycle"), QStringLiteral("SOFT_DELETED")},
        {QStringLiteral("summary"), QStringLiteral("Journal event soft-deleted")},
        {QStringLiteral("details"), QStringLiteral("Original event remains in append-only storage until retention archive/purge policy completes.")},
        {QStringLiteral("target_event_id"), eventId.trimmed()},
        {QStringLiteral("integrity"), QStringLiteral("APPEND_ONLY")}
    };
    if (!appendObject(tombstone)) return QStringLiteral("TOMBSTONE_APPEND_FAILED");
    refresh();
    const auto result = QStringLiteral("SOFT_DELETED:%1").arg(eventId.trimmed());
    setResult(result);
    return result;
}

QString JournalService::exportJournal(const QString &format, const QString &query)
{
    if (!ensureLayout()) return QStringLiteral("STORAGE_LAYOUT_FAILED");
    const auto filtered = filteredEvents(QStringLiteral("ALL"), query);
    QJsonArray events;
    for (const auto &value : filtered) events.append(QJsonObject::fromVariantMap(value.toMap()));
    const auto stamp = QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMddTHHmmssZ"));
    const auto normalized = format.trimmed().toLower();
    const auto extension = normalized == QStringLiteral("html") ? QStringLiteral("html") : normalized == QStringLiteral("json") ? QStringLiteral("json") : QStringLiteral("md");
    const auto path = QDir(exportsPath()).filePath(QStringLiteral("FA3-Journal-%1.%2").arg(stamp, extension));

    QByteArray output;
    if (extension == QStringLiteral("json")) {
        QJsonObject root{{QStringLiteral("schema"), QStringLiteral("fa3.journal-export.v1")},
                         {QStringLiteral("created_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
                         {QStringLiteral("query"), query},
                         {QStringLiteral("events"), events}};
        output = QJsonDocument(root).toJson(QJsonDocument::Indented);
    } else if (extension == QStringLiteral("html")) {
        QString html = QStringLiteral("<!doctype html><meta charset=\"utf-8\"><title>FA3 Journal</title><style>body{font-family:sans-serif;max-width:1100px;margin:2rem auto}article{border-bottom:1px solid #aaa;padding:1rem 0}small{color:#666}</style><h1>FA3 Journal</h1>");
        for (const auto &value : events) {
            const auto e = value.toObject();
            html += QStringLiteral("<article><small>%1 · %2 · %3</small><h3>%4</h3><p>%5</p></article>")
                .arg(e.value(QStringLiteral("timestamp")).toString().toHtmlEscaped(),
                     e.value(QStringLiteral("domain")).toString().toHtmlEscaped(),
                     e.value(QStringLiteral("lifecycle")).toString().toHtmlEscaped(),
                     e.value(QStringLiteral("summary")).toString().toHtmlEscaped(),
                     e.value(QStringLiteral("details")).toString().toHtmlEscaped());
        }
        output = html.toUtf8();
    } else {
        QString markdown = QStringLiteral("# FA3 Journal export\n\nCreated: %1\n\n").arg(QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs));
        for (const auto &value : events) {
            const auto e = value.toObject();
            markdown += QStringLiteral("## %1\n\n- Time: `%2`\n- Domain: `%3`\n- Lifecycle: `%4`\n- Project: `%5`\n\n%6\n\n")
                .arg(e.value(QStringLiteral("summary")).toString(),
                     e.value(QStringLiteral("timestamp")).toString(),
                     e.value(QStringLiteral("domain")).toString(),
                     e.value(QStringLiteral("lifecycle")).toString(),
                     e.value(QStringLiteral("project_id")).toString(),
                     e.value(QStringLiteral("details")).toString());
        }
        output = markdown.toUtf8();
    }

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) return QStringLiteral("EXPORT_WRITE_FAILED");
    file.write(output);
    if (!file.commit()) return QStringLiteral("EXPORT_COMMIT_FAILED");
    const auto result = QStringLiteral("EXPORTED:%1").arg(path);
    setResult(result);
    return path;
}

QString JournalService::printJournal(const QString &query)
{
    const auto path = exportJournal(QStringLiteral("html"), query);
    if (!QFileInfo::exists(path)) return path;
    const auto lp = QStandardPaths::findExecutable(QStringLiteral("lp"));
    if (!lp.isEmpty() && QProcess::startDetached(lp, {path})) {
        const auto result = QStringLiteral("PRINT_SUBMITTED:%1").arg(path);
        setResult(result);
        return result;
    }
    QDesktopServices::openUrl(QUrl::fromLocalFile(path));
    const auto result = QStringLiteral("PRINT_PREVIEW_OPENED:%1").arg(path);
    setResult(result);
    return result;
}

QString JournalService::shareJournal(const QString &channel, const QString &query)
{
    const auto path = exportJournal(QStringLiteral("md"), query);
    if (!QFileInfo::exists(path)) return path;
    const auto normalized = channel.trimmed().toUpper();
    if (normalized == QStringLiteral("EMAIL")) {
        const auto xdgEmail = QStandardPaths::findExecutable(QStringLiteral("xdg-email"));
        if (!xdgEmail.isEmpty() && QProcess::startDetached(xdgEmail,
            {QStringLiteral("--subject"), QStringLiteral("FA3 Journal export"),
             QStringLiteral("--body"), QStringLiteral("FA3 Journal export attached."),
             QStringLiteral("--attach"), path})) {
            const auto result = QStringLiteral("EMAIL_COMPOSER_OPENED:%1").arg(path);
            setResult(result);
            return result;
        }
    }
    if (normalized == QStringLiteral("CHAT")) {
        const auto chatUrl = qEnvironmentVariable("FA3_CHAT_SHARE_URL");
        if (!chatUrl.isEmpty() && QDesktopServices::openUrl(QUrl(chatUrl))) {
            const auto result = QStringLiteral("CHAT_ADAPTER_OPENED:%1").arg(path);
            setResult(result);
            return result;
        }
    }
    QDesktopServices::openUrl(QUrl::fromLocalFile(exportsPath()));
    const auto result = QStringLiteral("SHARE_BUNDLE_READY:%1:ADAPTER_REQUIRED").arg(path);
    setResult(result);
    return result;
}

bool JournalService::openStorageRoot() const
{
    return QDesktopServices::openUrl(QUrl::fromLocalFile(m_storageRoot));
}
