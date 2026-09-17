#include "OpenModelDbService.h"

#include <QCryptographicHash>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QUrl>
#include <QUuid>

#include <algorithm>

namespace {
constexpr auto kCatalogUrl = "https://www.openmodeldb.info/api/v1/models";
constexpr auto kOpenModelDbUrl = "https://openmodeldb.info/";
}

OpenModelDbService::OpenModelDbService(QObject *parent)
    : QObject(parent)
    , m_network(new QNetworkAccessManager(this))
{
    m_stagingRoot = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)
        + QStringLiteral("/model-staging/openmodeldb");
    QDir().mkpath(m_stagingRoot);
}

OpenModelDbService::~OpenModelDbService()
{
    const auto values = m_activeDownloads.values();
    for (ActiveDownload *active : values) {
        if (!active) {
            continue;
        }
        if (active->reply) {
            active->reply->abort();
        }
        if (active->file) {
            active->file->close();
            QFile::remove(active->partPath);
            delete active->file;
        }
        delete active->hash;
        delete active;
    }
}

QString OpenModelDbService::scalarToString(const QVariant &value)
{
    if (!value.isValid() || value.isNull()) {
        return {};
    }
    return value.toString().trimmed();
}

QString OpenModelDbService::safeSegment(const QString &value)
{
    QString out = value.trimmed();
    if (out.isEmpty()) {
        out = QStringLiteral("unnamed");
    }
    out.replace(QRegularExpression(QStringLiteral("[^A-Za-z0-9._-]+")), QStringLiteral("_"));
    while (out.startsWith('.')) {
        out.remove(0, 1);
    }
    return out.left(180);
}

QString OpenModelDbService::resourceFileName(const QString &modelName, const QVariantMap &resource)
{
    const QUrl url(resource.value(QStringLiteral("url")).toString());
    QString fileName = QFileInfo(url.path()).fileName();
    if (fileName.isEmpty()) {
        fileName = safeSegment(modelName) + QStringLiteral("-")
            + safeSegment(resource.value(QStringLiteral("name")).toString());
        const QString format = resource.value(QStringLiteral("format")).toString().toLower();
        if (!format.isEmpty()) {
            fileName += QStringLiteral(".") + safeSegment(format);
        }
    }
    return safeSegment(fileName);
}

int OpenModelDbService::scaleFromName(const QString &value)
{
    static const QRegularExpression pattern(QStringLiteral("(?:^|[^0-9])x(\\d{1,2})(?:[^0-9]|$)"),
                                            QRegularExpression::CaseInsensitiveOption);
    const auto match = pattern.match(value);
    if (!match.hasMatch()) {
        return 0;
    }
    bool ok = false;
    const int scale = match.captured(1).toInt(&ok);
    return ok && scale > 0 && scale <= 32 ? scale : 0;
}

bool OpenModelDbService::validSha256(const QString &value)
{
    static const QRegularExpression pattern(QStringLiteral("^[0-9A-Fa-f]{64}$"));
    return pattern.match(value.trimmed()).hasMatch();
}

bool OpenModelDbService::dangerousFormat(const QString &format)
{
    const QString lowered = format.trimmed().toLower();
    return lowered == QStringLiteral("pth") || lowered == QStringLiteral("pt")
        || lowered == QStringLiteral("ckpt") || lowered == QStringLiteral("pickle")
        || lowered == QStringLiteral("pkl") || lowered == QStringLiteral("bin");
}

QVariantMap OpenModelDbService::parseTag(const QVariantMap &raw) const
{
    QVariantMap tag;
    tag.insert(QStringLiteral("id"), scalarToString(raw.value(QStringLiteral("id"))));
    tag.insert(QStringLiteral("name"), scalarToString(raw.value(QStringLiteral("name"))));
    tag.insert(QStringLiteral("category"), scalarToString(raw.value(QStringLiteral("category"))));
    tag.insert(QStringLiteral("color"), scalarToString(raw.value(QStringLiteral("color"))));
    return tag;
}

QVariantMap OpenModelDbService::parseResource(const QVariantMap &raw) const
{
    QVariantMap resource;
    const QString name = scalarToString(raw.value(QStringLiteral("name")));
    QString url = scalarToString(raw.value(QStringLiteral("url")));
    if (url.isEmpty()) {
        const QVariantList urls = raw.value(QStringLiteral("urls")).toList();
        for (const QVariant &entry : urls) {
            if (entry.metaType().id() == QMetaType::QVariantMap) {
                const QVariantMap map = entry.toMap();
                url = scalarToString(map.value(QStringLiteral("url")));
            } else {
                url = scalarToString(entry);
            }
            if (!url.isEmpty()) {
                break;
            }
        }
    }

    const QString format = scalarToString(raw.value(QStringLiteral("format")));
    const QString platform = scalarToString(raw.value(QStringLiteral("platform")));
    const QString architecture = scalarToString(raw.value(QStringLiteral("architecture")));
    int scale = raw.value(QStringLiteral("scale")).toInt();
    if (scale <= 0) {
        scale = scaleFromName(name);
    }

    QStringList labelParts;
    if (scale > 0) {
        labelParts << QString::number(scale) + QStringLiteral("x");
    }
    if (!platform.isEmpty()) {
        labelParts << platform;
    }
    if (!architecture.isEmpty() && architecture.compare(platform, Qt::CaseInsensitive) != 0) {
        labelParts << architecture;
    }
    if (!format.isEmpty()) {
        labelParts << format;
    }

    resource.insert(QStringLiteral("id"), scalarToString(raw.value(QStringLiteral("id"))));
    resource.insert(QStringLiteral("name"), name);
    resource.insert(QStringLiteral("url"), url);
    resource.insert(QStringLiteral("sha256"), scalarToString(raw.value(QStringLiteral("sha256"))).toLower());
    resource.insert(QStringLiteral("format"), format);
    resource.insert(QStringLiteral("platform"), platform);
    resource.insert(QStringLiteral("architecture"), architecture);
    resource.insert(QStringLiteral("size"), raw.value(QStringLiteral("size")));
    resource.insert(QStringLiteral("scale"), scale);
    resource.insert(QStringLiteral("scale_label"), scale > 0 ? QString::number(scale) + QStringLiteral("x") : QString());
    resource.insert(QStringLiteral("label"), labelParts.isEmpty() ? name : labelParts.join(QStringLiteral(" · ")));
    return resource;
}

QVariantMap OpenModelDbService::parseModel(const QString &key, const QVariantMap &raw) const
{
    QVariantMap model;
    QString id = scalarToString(raw.value(QStringLiteral("id")));
    if (id.isEmpty()) {
        id = key;
    }
    QString author;
    const QVariant authorValue = raw.value(QStringLiteral("author"));
    if (authorValue.metaType().id() == QMetaType::QVariantMap) {
        author = scalarToString(authorValue.toMap().value(QStringLiteral("name")));
    } else {
        author = scalarToString(authorValue);
    }

    QVariantList tags;
    for (const QVariant &entry : raw.value(QStringLiteral("tags")).toList()) {
        const QVariantMap parsed = parseTag(entry.toMap());
        if (!parsed.value(QStringLiteral("name")).toString().isEmpty()) {
            tags.push_back(parsed);
        }
    }

    QVariantList resources;
    for (const QVariant &entry : raw.value(QStringLiteral("resources")).toList()) {
        const QVariantMap parsed = parseResource(entry.toMap());
        if (!parsed.value(QStringLiteral("name")).toString().isEmpty()
            || !parsed.value(QStringLiteral("url")).toString().isEmpty()) {
            resources.push_back(parsed);
        }
    }

    const QString license = scalarToString(raw.value(QStringLiteral("license")));
    const QString name = scalarToString(raw.value(QStringLiteral("name")));
    model.insert(QStringLiteral("id"), id);
    model.insert(QStringLiteral("name"), name.isEmpty() ? id : name);
    model.insert(QStringLiteral("author"), author.isEmpty() ? QStringLiteral("Unknown") : author);
    model.insert(QStringLiteral("license"), license.isEmpty() ? QStringLiteral("UNKNOWN") : license);
    model.insert(QStringLiteral("description"), scalarToString(raw.value(QStringLiteral("description"))));
    model.insert(QStringLiteral("tags"), tags);
    model.insert(QStringLiteral("resources"), resources);
    model.insert(QStringLiteral("model_url"), QStringLiteral("https://openmodeldb.info/models/") + id);
    return model;
}

void OpenModelDbService::setCatalogState(const QString &status, bool busy)
{
    if (m_catalogStatus == status && m_catalogBusy == busy) {
        return;
    }
    m_catalogStatus = status;
    m_catalogBusy = busy;
    emit catalogStatusChanged();
}

void OpenModelDbService::refreshCatalog()
{
    if (m_catalogBusy) {
        return;
    }
    setCatalogState(QStringLiteral("LOADING"), true);

    QNetworkRequest request(QUrl(QString::fromLatin1(kCatalogUrl)));
    request.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("FA3-Control-Center/0.2 OpenModelDB-Catalog"));
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    QNetworkReply *reply = m_network->get(request);

    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        const QByteArray payload = reply->readAll();
        if (reply->error() != QNetworkReply::NoError) {
            setCatalogState(QStringLiteral("ERROR: ") + reply->errorString(), false);
            reply->deleteLater();
            return;
        }

        QJsonParseError parseError;
        const QJsonDocument document = QJsonDocument::fromJson(payload, &parseError);
        if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
            setCatalogState(QStringLiteral("ERROR: INVALID_OPENMODELDB_JSON"), false);
            reply->deleteLater();
            return;
        }

        QVariantMap root = document.toVariant().toMap();
        QVariantMap catalog = root;
        if (root.value(QStringLiteral("models")).metaType().id() == QMetaType::QVariantMap) {
            catalog = root.value(QStringLiteral("models")).toMap();
        }

        QVariantList parsedModels;
        for (auto it = catalog.cbegin(); it != catalog.cend(); ++it) {
            const QVariantMap raw = it.value().toMap();
            if (raw.isEmpty()) {
                continue;
            }
            const QVariantMap parsed = parseModel(it.key(), raw);
            if (!parsed.value(QStringLiteral("resources")).toList().isEmpty()) {
                parsedModels.push_back(parsed);
            }
        }
        std::sort(parsedModels.begin(), parsedModels.end(), [](const QVariant &a, const QVariant &b) {
            return a.toMap().value(QStringLiteral("name")).toString().compare(
                       b.toMap().value(QStringLiteral("name")).toString(), Qt::CaseInsensitive)
                < 0;
        });

        m_models = parsedModels;
        rebuildFacetLists();
        emit modelsChanged();
        setCatalogState(QStringLiteral("READY · %1 models").arg(m_models.size()), false);
        reply->deleteLater();
    });
}

void OpenModelDbService::rebuildFacetLists()
{
    QHash<QString, QVariantMap> uniqueTags;
    QSet<QString> scales;
    QSet<QString> architectures;
    QSet<QString> platforms;

    for (const QVariant &modelValue : m_models) {
        const QVariantMap model = modelValue.toMap();
        for (const QVariant &tagValue : model.value(QStringLiteral("tags")).toList()) {
            const QVariantMap tag = tagValue.toMap();
            QString key = tag.value(QStringLiteral("id")).toString();
            if (key.isEmpty()) {
                key = tag.value(QStringLiteral("category")).toString() + QStringLiteral("/")
                    + tag.value(QStringLiteral("name")).toString();
            }
            uniqueTags.insert(key, tag);
        }
        for (const QVariant &resourceValue : model.value(QStringLiteral("resources")).toList()) {
            const QVariantMap resource = resourceValue.toMap();
            const QString scale = resource.value(QStringLiteral("scale_label")).toString();
            const QString architecture = resource.value(QStringLiteral("architecture")).toString();
            const QString platform = resource.value(QStringLiteral("platform")).toString();
            if (!scale.isEmpty()) scales.insert(scale);
            if (!architecture.isEmpty()) architectures.insert(architecture);
            if (!platform.isEmpty()) platforms.insert(platform);
        }
    }

    m_tags = uniqueTags.values();
    std::sort(m_tags.begin(), m_tags.end(), [](const QVariant &a, const QVariant &b) {
        const QVariantMap am = a.toMap();
        const QVariantMap bm = b.toMap();
        const QString ak = am.value(QStringLiteral("category")).toString() + QStringLiteral("/") + am.value(QStringLiteral("name")).toString();
        const QString bk = bm.value(QStringLiteral("category")).toString() + QStringLiteral("/") + bm.value(QStringLiteral("name")).toString();
        return ak.compare(bk, Qt::CaseInsensitive) < 0;
    });

    m_scales = scales.values();
    std::sort(m_scales.begin(), m_scales.end(), [](const QString &a, const QString &b) {
        return a.left(a.size() - 1).toInt() < b.left(b.size() - 1).toInt();
    });
    m_architectures = architectures.values();
    m_architectures.sort(Qt::CaseInsensitive);
    m_platforms = platforms.values();
    m_platforms.sort(Qt::CaseInsensitive);
}

bool OpenModelDbService::openExternalUrl(const QString &url) const
{
    const QUrl parsed(url);
    if (!parsed.isValid() || (parsed.scheme() != QStringLiteral("https") && parsed.scheme() != QStringLiteral("http"))) {
        return false;
    }
    return QDesktopServices::openUrl(parsed);
}

bool OpenModelDbService::openStagingFolder() const
{
    QDir().mkpath(m_stagingRoot);
    return QDesktopServices::openUrl(QUrl::fromLocalFile(m_stagingRoot));
}

int OpenModelDbService::downloadIndex(const QString &id) const
{
    for (qsizetype i = 0; i < m_downloads.size(); ++i) {
        if (m_downloads.at(i).toMap().value(QStringLiteral("id")).toString() == id) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

void OpenModelDbService::updateDownload(const QString &id, const QVariantMap &changes)
{
    const int index = downloadIndex(id);
    if (index < 0) {
        return;
    }
    QVariantMap item = m_downloads.at(index).toMap();
    for (auto it = changes.cbegin(); it != changes.cend(); ++it) {
        item.insert(it.key(), it.value());
    }
    m_downloads[index] = item;
    emit downloadsChanged();
}

QString OpenModelDbService::queueDownload(const QString &modelId,
                                          const QString &modelName,
                                          const QString &licenseId,
                                          const QVariantMap &resource)
{
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QString urlString = resource.value(QStringLiteral("url")).toString().trimmed();
    const QUrl url(urlString);
    const QString expectedSha = resource.value(QStringLiteral("sha256")).toString().trimmed().toLower();
    const QString fileName = resourceFileName(modelName, resource);

    QVariantMap item;
    item.insert(QStringLiteral("id"), id);
    item.insert(QStringLiteral("model_id"), modelId);
    item.insert(QStringLiteral("model_name"), modelName);
    item.insert(QStringLiteral("license"), licenseId.isEmpty() ? QStringLiteral("UNKNOWN") : licenseId);
    item.insert(QStringLiteral("resource"), resource);
    item.insert(QStringLiteral("resource_name"), resource.value(QStringLiteral("name")));
    item.insert(QStringLiteral("format"), resource.value(QStringLiteral("format")));
    item.insert(QStringLiteral("url"), urlString);
    item.insert(QStringLiteral("expected_sha256"), expectedSha);
    item.insert(QStringLiteral("filename"), fileName);
    item.insert(QStringLiteral("progress"), 0.0);
    item.insert(QStringLiteral("bytes_received"), 0);
    item.insert(QStringLiteral("bytes_total"), 0);
    item.insert(QStringLiteral("security_admitted"), false);
    item.insert(QStringLiteral("runtime_verified"), false);

    if (!url.isValid() || url.scheme() != QStringLiteral("https")) {
        item.insert(QStringLiteral("status"), QStringLiteral("BLOCKED_INVALID_OR_INSECURE_URL"));
        item.insert(QStringLiteral("detail"), QStringLiteral("Only HTTPS transport is accepted for staged model acquisition."));
    } else if (!validSha256(expectedSha)) {
        item.insert(QStringLiteral("status"), QStringLiteral("BLOCKED_MISSING_OR_INVALID_SHA256"));
        item.insert(QStringLiteral("detail"), QStringLiteral("OpenModelDB SHA-256 is required before FA3 will acquire the artifact."));
    } else {
        item.insert(QStringLiteral("status"), QStringLiteral("QUEUED"));
        item.insert(QStringLiteral("detail"), QStringLiteral("Waiting for the mediated staging download slot."));
    }

    m_downloads.push_front(item);
    emit downloadsChanged();
    startNextDownload();
    return id;
}

void OpenModelDbService::startNextDownload()
{
    if (!m_activeId.isEmpty()) {
        return;
    }
    for (const QVariant &value : m_downloads) {
        const QVariantMap item = value.toMap();
        if (item.value(QStringLiteral("status")).toString() == QStringLiteral("QUEUED")) {
            startDownload(item.value(QStringLiteral("id")).toString());
            return;
        }
    }
}

void OpenModelDbService::startDownload(const QString &id)
{
    const int index = downloadIndex(id);
    if (index < 0 || !m_activeId.isEmpty()) {
        return;
    }
    const QVariantMap item = m_downloads.at(index).toMap();
    const QUrl url(item.value(QStringLiteral("url")).toString());
    const QString modelDirectory = m_stagingRoot + QStringLiteral("/")
        + safeSegment(item.value(QStringLiteral("model_id")).toString());
    if (!QDir().mkpath(modelDirectory)) {
        updateDownload(id, {{QStringLiteral("status"), QStringLiteral("FAILED_STAGING_DIRECTORY")}});
        startNextDownload();
        return;
    }

    auto *active = new ActiveDownload;
    active->id = id;
    active->expectedSha256 = item.value(QStringLiteral("expected_sha256")).toString();
    active->finalPath = modelDirectory + QStringLiteral("/") + item.value(QStringLiteral("filename")).toString();
    active->partPath = active->finalPath + QStringLiteral(".part");
    QFile::remove(active->partPath);
    active->file = new QFile(active->partPath);
    active->hash = new QCryptographicHash(QCryptographicHash::Sha256);
    if (!active->file->open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        updateDownload(id, {{QStringLiteral("status"), QStringLiteral("FAILED_OPEN_STAGING_FILE")},
                            {QStringLiteral("detail"), active->file->errorString()}});
        delete active->file;
        delete active->hash;
        delete active;
        startNextDownload();
        return;
    }

    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("FA3-Control-Center/0.2 OpenModelDB-Downloader"));
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    active->reply = m_network->get(request);
    m_activeId = id;
    m_activeDownloads.insert(id, active);
    updateDownload(id, {{QStringLiteral("status"), QStringLiteral("DOWNLOADING")},
                        {QStringLiteral("detail"), QStringLiteral("Streaming to FA3 staging; runtime directories are not modified.")},
                        {QStringLiteral("staging_path"), active->finalPath}});

    connect(active->reply, &QNetworkReply::readyRead, this, [this, id]() {
        ActiveDownload *current = m_activeDownloads.value(id, nullptr);
        if (!current || current->cancelled || current->ioFailed) {
            return;
        }
        const QByteArray chunk = current->reply->readAll();
        if (chunk.isEmpty()) {
            return;
        }
        if (current->file->write(chunk) != chunk.size()) {
            current->ioFailed = true;
            current->reply->abort();
            return;
        }
        current->hash->addData(chunk);
    });

    connect(active->reply, &QNetworkReply::downloadProgress, this,
            [this, id](qint64 received, qint64 total) {
                const double progress = total > 0 ? static_cast<double>(received) / static_cast<double>(total) : 0.0;
                updateDownload(id, {{QStringLiteral("progress"), progress},
                                    {QStringLiteral("bytes_received"), received},
                                    {QStringLiteral("bytes_total"), total}});
            });

    connect(active->reply, &QNetworkReply::finished, this, [this, id]() {
        if (m_activeId == id) {
            finishActiveDownload();
        }
    });
}

void OpenModelDbService::finishActiveDownload()
{
    const QString id = m_activeId;
    ActiveDownload *active = m_activeDownloads.value(id, nullptr);
    if (!active) {
        m_activeId.clear();
        startNextDownload();
        return;
    }

    if (!active->cancelled && !active->ioFailed) {
        const QByteArray tail = active->reply->readAll();
        if (!tail.isEmpty()) {
            if (active->file->write(tail) != tail.size()) {
                active->ioFailed = true;
            } else {
                active->hash->addData(tail);
            }
        }
    }
    active->file->close();

    const int index = downloadIndex(id);
    const QVariantMap item = index >= 0 ? m_downloads.at(index).toMap() : QVariantMap{};
    const QString license = item.value(QStringLiteral("license")).toString();
    const QString format = item.value(QStringLiteral("format")).toString();

    if (active->cancelled) {
        QFile::remove(active->partPath);
        updateDownload(id, {{QStringLiteral("status"), QStringLiteral("CANCELLED")},
                            {QStringLiteral("detail"), QStringLiteral("Download cancelled; partial staging artifact removed.")}});
    } else if (active->ioFailed) {
        QFile::remove(active->partPath);
        updateDownload(id, {{QStringLiteral("status"), QStringLiteral("FAILED_IO")},
                            {QStringLiteral("detail"), QStringLiteral("Failed while writing staged artifact.")}});
    } else if (active->reply->error() != QNetworkReply::NoError) {
        QFile::remove(active->partPath);
        updateDownload(id, {{QStringLiteral("status"), QStringLiteral("FAILED_NETWORK")},
                            {QStringLiteral("detail"), active->reply->errorString()}});
    } else {
        const QString observedSha = QString::fromLatin1(active->hash->result().toHex());
        if (observedSha.compare(active->expectedSha256, Qt::CaseInsensitive) != 0) {
            QFile::remove(active->partPath);
            updateDownload(id, {{QStringLiteral("status"), QStringLiteral("BLOCKED_CHECKSUM_MISMATCH")},
                                {QStringLiteral("observed_sha256"), observedSha},
                                {QStringLiteral("detail"), QStringLiteral("SHA-256 mismatch: staged bytes quarantined by deletion and cannot be imported.")}});
        } else {
            QFile::remove(active->finalPath);
            QFile staged(active->partPath);
            if (!staged.rename(active->finalPath)) {
                QFile::remove(active->partPath);
                updateDownload(id, {{QStringLiteral("status"), QStringLiteral("FAILED_MOVE_TO_STAGING")},
                                    {QStringLiteral("detail"), staged.errorString()}});
            } else {
                QString detail = QStringLiteral("SHA-256 verified. Awaiting Model Artifact Security admission and executable runtime evidence before promotion.");
                if (license.isEmpty() || license == QStringLiteral("UNKNOWN")) {
                    detail += QStringLiteral(" License is unknown, so promotion remains blocked.");
                }
                if (dangerousFormat(format)) {
                    detail += QStringLiteral(" Dangerous serialization requires explicit security admission.");
                }
                updateDownload(id, {{QStringLiteral("status"), QStringLiteral("VERIFIED_STAGED_AWAITING_SECURITY_ADMISSION")},
                                    {QStringLiteral("progress"), 1.0},
                                    {QStringLiteral("observed_sha256"), observedSha},
                                    {QStringLiteral("staging_path"), active->finalPath},
                                    {QStringLiteral("detail"), detail}});
            }
        }
    }

    active->reply->deleteLater();
    delete active->file;
    delete active->hash;
    m_activeDownloads.remove(id);
    delete active;
    m_activeId.clear();
    startNextDownload();
}

bool OpenModelDbService::cancelDownload(const QString &downloadId)
{
    const int index = downloadIndex(downloadId);
    if (index < 0) {
        return false;
    }
    const QString status = m_downloads.at(index).toMap().value(QStringLiteral("status")).toString();
    if (status == QStringLiteral("QUEUED")) {
        updateDownload(downloadId, {{QStringLiteral("status"), QStringLiteral("CANCELLED")},
                                    {QStringLiteral("detail"), QStringLiteral("Queued download cancelled.")}});
        return true;
    }
    ActiveDownload *active = m_activeDownloads.value(downloadId, nullptr);
    if (!active) {
        return false;
    }
    active->cancelled = true;
    active->reply->abort();
    return true;
}

bool OpenModelDbService::retryDownload(const QString &downloadId)
{
    const int index = downloadIndex(downloadId);
    if (index < 0 || m_activeDownloads.contains(downloadId)) {
        return false;
    }
    QVariantMap item = m_downloads.at(index).toMap();
    const QString sha = item.value(QStringLiteral("expected_sha256")).toString();
    const QUrl url(item.value(QStringLiteral("url")).toString());
    if (!validSha256(sha) || !url.isValid() || url.scheme() != QStringLiteral("https")) {
        return false;
    }
    item.insert(QStringLiteral("status"), QStringLiteral("QUEUED"));
    item.insert(QStringLiteral("detail"), QStringLiteral("Retry queued."));
    item.insert(QStringLiteral("progress"), 0.0);
    item.remove(QStringLiteral("observed_sha256"));
    m_downloads[index] = item;
    emit downloadsChanged();
    startNextDownload();
    return true;
}
