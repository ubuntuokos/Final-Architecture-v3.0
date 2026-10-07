#include "ModelLibraryService.h"

#include <QCoreApplication>
#include <QDesktopServices>
#include <QDir>
#include <QDirIterator>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QRegularExpression>
#include <QSaveFile>
#include <QSettings>
#include <QStandardPaths>
#include <QUrlQuery>

#include <filesystem>

namespace {
const QStringList kCategories = {
    QStringLiteral("checkpoints"),
    QStringLiteral("loras"),
    QStringLiteral("vae"),
    QStringLiteral("embeddings"),
    QStringLiteral("controlnet"),
    QStringLiteral("clip"),
    QStringLiteral("unet"),
    QStringLiteral("diffusion_models"),
    QStringLiteral("upscale_models"),
    QStringLiteral("other")
};

QString expandHome(const QString &path)
{
    if (path == QStringLiteral("~"))
        return QDir::homePath();
    if (path.startsWith(QStringLiteral("~/")))
        return QDir::homePath() + path.mid(1);
    return path;
}
}

ModelLibraryService::ModelLibraryService(QObject *parent)
    : QObject(parent)
{
    QSettings settings;
    m_sharedRoot = settings.value(QStringLiteral("models/sharedRoot"), defaultSharedRoot()).toString();
    ensureSharedLayout();
    refresh();
}

ModelLibraryService::~ModelLibraryService()
{
    cancelDownload();
    delete m_downloadFile;
}

QStringList ModelLibraryService::modelExtensions()
{
    return {QStringLiteral("safetensors"), QStringLiteral("ckpt"), QStringLiteral("pt"), QStringLiteral("pth"),
            QStringLiteral("bin"), QStringLiteral("gguf"), QStringLiteral("onnx")};
}

QStringList ModelLibraryService::previewExtensions()
{
    return {QStringLiteral("png"), QStringLiteral("jpg"), QStringLiteral("jpeg"), QStringLiteral("webp")};
}

QString ModelLibraryService::categoryLabel(const QString &category)
{
    if (category == QStringLiteral("checkpoints")) return QStringLiteral("Checkpoint");
    if (category == QStringLiteral("loras")) return QStringLiteral("LoRA");
    if (category == QStringLiteral("vae")) return QStringLiteral("VAE");
    if (category == QStringLiteral("embeddings")) return QStringLiteral("Embedding");
    if (category == QStringLiteral("controlnet")) return QStringLiteral("ControlNet");
    if (category == QStringLiteral("clip")) return QStringLiteral("CLIP");
    if (category == QStringLiteral("unet")) return QStringLiteral("UNet");
    if (category == QStringLiteral("diffusion_models")) return QStringLiteral("Diffusion / Video");
    if (category == QStringLiteral("upscale_models")) return QStringLiteral("Upscaler");
    return QStringLiteral("Other");
}

QString ModelLibraryService::humanReadableSize(qint64 bytes)
{
    static const char *units[] = {"B", "KiB", "MiB", "GiB", "TiB"};
    double value = static_cast<double>(bytes);
    int unit = 0;
    while (value >= 1024.0 && unit < 4) {
        value /= 1024.0;
        ++unit;
    }
    return unit == 0
        ? QStringLiteral("%1 %2").arg(bytes).arg(QString::fromLatin1(units[unit]))
        : QStringLiteral("%1 %2").arg(value, 0, 'f', value < 10.0 ? 1 : 0).arg(QString::fromLatin1(units[unit]));
}

QString ModelLibraryService::cleanFileName(const QString &name)
{
    QString result = QFileInfo(name).fileName().trimmed();
    result.replace(QRegularExpression(QStringLiteral("[^A-Za-z0-9._()\- +\[\]]")), QStringLiteral("_"));
    while (result.startsWith('.')) result.remove(0, 1);
    return result.left(240);
}

bool ModelLibraryService::isInside(const QString &childPath, const QString &parentPath)
{
    const QString child = QDir::cleanPath(QFileInfo(childPath).absoluteFilePath());
    QString parent = QDir::cleanPath(QFileInfo(parentPath).absoluteFilePath());
    if (!parent.endsWith(QDir::separator())) parent += QDir::separator();
    return child.startsWith(parent);
}

QString ModelLibraryService::metadataPathFor(const QString &modelPath)
{
    return modelPath + QStringLiteral(".fa3.json");
}

QString ModelLibraryService::previewPathFor(const QString &modelPath)
{
    for (const QString &ext : previewExtensions()) {
        const QString candidate = modelPath + QStringLiteral(".preview.") + ext;
        if (QFileInfo::exists(candidate)) return candidate;
    }
    const QFileInfo info(modelPath);
    for (const QString &ext : previewExtensions()) {
        const QString candidate = info.dir().absoluteFilePath(info.completeBaseName() + QStringLiteral(".") + ext);
        if (QFileInfo::exists(candidate)) return candidate;
    }
    return QString();
}

QString ModelLibraryService::defaultSharedRoot() const
{
    const QString data = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation);
    return QDir(data).absoluteFilePath(QStringLiteral("fa3/models"));
}

QString ModelLibraryService::categoryDirectory(const QString &category) const
{
    const QString normalized = kCategories.contains(category) ? category : QStringLiteral("other");
    return QDir(m_sharedRoot).absoluteFilePath(normalized);
}

void ModelLibraryService::ensureSharedLayout()
{
    QDir root;
    root.mkpath(m_sharedRoot);
    for (const QString &category : kCategories)
        root.mkpath(categoryDirectory(category));
}

QList<ModelLibraryService::ClientDefinition> ModelLibraryService::clientDefinitions() const
{
    return {
        {QStringLiteral("comfyui"), QStringLiteral("ComfyUI"),
         {QStringLiteral("~/ComfyUI/models"), QStringLiteral("~/comfyui/models")},
         {{QStringLiteral("checkpoints"), QStringLiteral("checkpoints")},
          {QStringLiteral("loras"), QStringLiteral("loras")},
          {QStringLiteral("vae"), QStringLiteral("vae")},
          {QStringLiteral("embeddings"), QStringLiteral("embeddings")},
          {QStringLiteral("controlnet"), QStringLiteral("controlnet")},
          {QStringLiteral("clip"), QStringLiteral("clip")},
          {QStringLiteral("diffusion_models"), QStringLiteral("diffusion_models")},
          {QStringLiteral("upscale_models"), QStringLiteral("upscale_models")}}},
        {QStringLiteral("automatic1111"), QStringLiteral("Automatic1111"),
         {QStringLiteral("~/stable-diffusion-webui/models")},
         {{QStringLiteral("checkpoints"), QStringLiteral("Stable-diffusion")},
          {QStringLiteral("loras"), QStringLiteral("Lora")},
          {QStringLiteral("vae"), QStringLiteral("VAE")},
          {QStringLiteral("embeddings"), QStringLiteral("../embeddings")}}},
        {QStringLiteral("forge"), QStringLiteral("Forge"),
         {QStringLiteral("~/stable-diffusion-webui-forge/models"), QStringLiteral("~/webui-forge/models")},
         {{QStringLiteral("checkpoints"), QStringLiteral("Stable-diffusion")},
          {QStringLiteral("loras"), QStringLiteral("Lora")},
          {QStringLiteral("vae"), QStringLiteral("VAE")},
          {QStringLiteral("embeddings"), QStringLiteral("../embeddings")}}},
        {QStringLiteral("fooocus"), QStringLiteral("Fooocus"),
         {QStringLiteral("~/Fooocus/models"), QStringLiteral("~/fooocus/models")},
         {{QStringLiteral("checkpoints"), QStringLiteral("checkpoints")},
          {QStringLiteral("loras"), QStringLiteral("loras")},
          {QStringLiteral("vae"), QStringLiteral("vae")},
          {QStringLiteral("embeddings"), QStringLiteral("embeddings")}}}
    };
}

QString ModelLibraryService::clientRootFor(const ClientDefinition &definition) const
{
    QSettings settings;
    const QString configured = settings.value(QStringLiteral("models/clients/") + definition.key + QStringLiteral("/root")).toString();
    if (!configured.isEmpty()) return configured;
    for (const QString &candidate : definition.candidates) {
        const QString expanded = expandHome(candidate);
        if (QFileInfo::exists(expanded)) return expanded;
    }
    return QString();
}

QString ModelLibraryService::linkStateFor(const ClientDefinition &definition, const QString &rootPath) const
{
    if (rootPath.isEmpty()) return QStringLiteral("NOT CONFIGURED");
    if (!QFileInfo::exists(rootPath)) return QStringLiteral("PATH MISSING");

    bool allLinked = true;
    bool needsMigration = false;
    for (const auto &mapping : definition.links) {
        const QString target = QDir::cleanPath(categoryDirectory(mapping.first));
        const QString linkPath = QDir(rootPath).absoluteFilePath(mapping.second);
        const QFileInfo info(linkPath);
        if (info.isSymLink()) {
            const QString resolved = QDir::cleanPath(info.symLinkTarget());
            if (resolved != target) {
                allLinked = false;
                needsMigration = true;
            }
        } else if (info.exists()) {
            allLinked = false;
            QDir dir(linkPath);
            if (!dir.isEmpty(QDir::NoDotAndDotDot | QDir::AllEntries)) needsMigration = true;
        } else {
            allLinked = false;
        }
    }
    if (allLinked) return QStringLiteral("LINKED");
    if (needsMigration) return QStringLiteral("NEEDS MIGRATION");
    return QStringLiteral("READY TO LINK");
}

QVariantMap ModelLibraryService::itemFromFile(const QString &absolutePath) const
{
    const QFileInfo info(absolutePath);
    const QString relative = QDir(m_sharedRoot).relativeFilePath(absolutePath);
    const QString category = relative.section('/', 0, 0);

    QVariantMap metadata;
    QFile metadataFile(metadataPathFor(absolutePath));
    if (metadataFile.open(QIODevice::ReadOnly)) {
        const QJsonDocument doc = QJsonDocument::fromJson(metadataFile.readAll());
        if (doc.isObject()) metadata = doc.object().toVariantMap();
    }

    const QString previewPath = previewPathFor(absolutePath);
    QVariantMap item;
    item.insert(QStringLiteral("name"), metadata.value(QStringLiteral("displayName"), info.completeBaseName()));
    item.insert(QStringLiteral("fileName"), info.fileName());
    item.insert(QStringLiteral("path"), info.absoluteFilePath());
    item.insert(QStringLiteral("fileUrl"), QUrl::fromLocalFile(info.absoluteFilePath()));
    item.insert(QStringLiteral("category"), kCategories.contains(category) ? category : QStringLiteral("other"));
    item.insert(QStringLiteral("categoryLabel"), categoryLabel(kCategories.contains(category) ? category : QStringLiteral("other")));
    item.insert(QStringLiteral("extension"), info.suffix().toLower());
    item.insert(QStringLiteral("size"), info.size());
    item.insert(QStringLiteral("sizeLabel"), humanReadableSize(info.size()));
    item.insert(QStringLiteral("modified"), info.lastModified().toString(Qt::ISODate));
    item.insert(QStringLiteral("previewUrl"), previewPath.isEmpty() ? QUrl() : QUrl::fromLocalFile(previewPath));
    item.insert(QStringLiteral("sourceUrl"), metadata.value(QStringLiteral("sourceUrl"), QString()));
    item.insert(QStringLiteral("baseModel"), metadata.value(QStringLiteral("baseModel"), QString()));
    item.insert(QStringLiteral("triggerWords"), metadata.value(QStringLiteral("triggerWords"), QString()));
    item.insert(QStringLiteral("notes"), metadata.value(QStringLiteral("notes"), QString()));
    item.insert(QStringLiteral("metadataPresent"), QFileInfo::exists(metadataPathFor(absolutePath)));
    return item;
}

void ModelLibraryService::scanItems()
{
    QVariantList rows;
    QDirIterator it(m_sharedRoot, QDir::Files | QDir::Readable, QDirIterator::Subdirectories);
    const QStringList extensions = modelExtensions();
    while (it.hasNext()) {
        const QString path = it.next();
        const QFileInfo info(path);
        if (!extensions.contains(info.suffix().toLower())) continue;
        rows.push_back(itemFromFile(path));
    }
    std::sort(rows.begin(), rows.end(), [](const QVariant &a, const QVariant &b) {
        const QVariantMap am = a.toMap();
        const QVariantMap bm = b.toMap();
        return am.value(QStringLiteral("name")).toString().compare(bm.value(QStringLiteral("name")).toString(), Qt::CaseInsensitive) < 0;
    });
    m_items = rows;
    emit itemsChanged();
}

void ModelLibraryService::scanClients()
{
    QVariantList rows;
    for (const ClientDefinition &definition : clientDefinitions()) {
        const QString path = clientRootFor(definition);
        QVariantMap row;
        row.insert(QStringLiteral("key"), definition.key);
        row.insert(QStringLiteral("name"), definition.name);
        row.insert(QStringLiteral("path"), path);
        row.insert(QStringLiteral("detected"), !path.isEmpty() && QFileInfo::exists(path));
        row.insert(QStringLiteral("state"), linkStateFor(definition, path));
        rows.push_back(row);
    }
    m_clients = rows;
    emit clientsChanged();
}

void ModelLibraryService::refresh()
{
    ensureSharedLayout();
    scanItems();
    scanClients();
}

QVariantMap ModelLibraryService::result(bool ok, const QString &message) const
{
    return {{QStringLiteral("ok"), ok}, {QStringLiteral("message"), message}};
}

QVariantMap ModelLibraryService::setSharedRoot(const QUrl &directory)
{
    if (!directory.isValid() || !directory.isLocalFile())
        return result(false, QStringLiteral("A Shared Storage helyének lokális mappának kell lennie."));
    const QString path = QDir::cleanPath(directory.toLocalFile());
    if (path.isEmpty()) return result(false, QStringLiteral("Érvénytelen mappa."));
    if (!QDir().mkpath(path)) return result(false, QStringLiteral("A megadott mappa nem hozható létre."));

    m_sharedRoot = path;
    QSettings settings;
    settings.setValue(QStringLiteral("models/sharedRoot"), m_sharedRoot);
    ensureSharedLayout();
    emit sharedRootChanged();
    refresh();
    return result(true, QStringLiteral("Shared Storage beállítva: %1").arg(m_sharedRoot));
}

QVariantMap ModelLibraryService::copyIntoCategory(const QString &sourcePath, const QString &category)
{
    const QFileInfo source(sourcePath);
    if (!source.exists() || !source.isFile() || !source.isReadable())
        return result(false, QStringLiteral("A forrásfájl nem olvasható."));
    if (!modelExtensions().contains(source.suffix().toLower()))
        return result(false, QStringLiteral("Nem támogatott modellfájl-kiterjesztés: %1").arg(source.suffix()));

    const QString destination = QDir(categoryDirectory(category)).absoluteFilePath(source.fileName());
    if (QDir::cleanPath(destination) == QDir::cleanPath(source.absoluteFilePath()))
        return result(true, QStringLiteral("A modell már ebben a mappában van."));
    if (QFileInfo::exists(destination))
        return result(false, QStringLiteral("Már létezik ilyen nevű modell: %1").arg(QFileInfo(destination).fileName()));
    if (!QFile::copy(source.absoluteFilePath(), destination))
        return result(false, QStringLiteral("A modell másolása sikertelen."));
    return result(true, QStringLiteral("Importálva: %1").arg(QFileInfo(destination).fileName()));
}

QVariantMap ModelLibraryService::importFiles(const QVariantList &urls, const QString &category)
{
    int imported = 0;
    QStringList failures;
    for (const QVariant &value : urls) {
        const QUrl url = value.canConvert<QUrl>() ? value.toUrl() : QUrl(value.toString());
        if (!url.isLocalFile()) {
            failures << QStringLiteral("nem lokális fájl");
            continue;
        }
        const QVariantMap r = copyIntoCategory(url.toLocalFile(), category);
        if (r.value(QStringLiteral("ok")).toBool()) ++imported;
        else failures << r.value(QStringLiteral("message")).toString();
    }
    refresh();
    if (!failures.isEmpty())
        return result(imported > 0, QStringLiteral("%1 fájl importálva; %2").arg(imported).arg(failures.join(QStringLiteral(" | "))));
    return result(true, QStringLiteral("%1 modell importálva a közös tárhelyre.").arg(imported));
}

QVariantMap ModelLibraryService::moveModel(const QUrl &source, const QString &category)
{
    if (!source.isLocalFile()) return result(false, QStringLiteral("Csak lokális modell mozgatható."));
    const QString sourcePath = QDir::cleanPath(source.toLocalFile());
    if (!isInside(sourcePath, m_sharedRoot))
        return result(false, QStringLiteral("Külső fájlt drag-and-drop importtal másolunk; közvetlen mozgatás csak Shared Storage-on belül engedélyezett."));

    const QFileInfo sourceInfo(sourcePath);
    const QString destination = QDir(categoryDirectory(category)).absoluteFilePath(sourceInfo.fileName());
    if (QDir::cleanPath(destination) == sourcePath) return result(true, QStringLiteral("A modell már ebben a kategóriában van."));
    if (QFileInfo::exists(destination)) return result(false, QStringLiteral("A célkategóriában már van ilyen nevű fájl."));
    if (!QFile::rename(sourcePath, destination)) return result(false, QStringLiteral("A modell áthelyezése sikertelen."));

    const QString oldMetadata = metadataPathFor(sourcePath);
    if (QFileInfo::exists(oldMetadata)) QFile::rename(oldMetadata, metadataPathFor(destination));
    for (const QString &ext : previewExtensions()) {
        const QString oldPreview = sourcePath + QStringLiteral(".preview.") + ext;
        if (QFileInfo::exists(oldPreview)) QFile::rename(oldPreview, destination + QStringLiteral(".preview.") + ext);
    }
    refresh();
    return result(true, QStringLiteral("Áthelyezve: %1 → %2").arg(sourceInfo.fileName(), categoryLabel(category)));
}

QVariantMap ModelLibraryService::saveMetadata(const QUrl &modelUrl, const QVariantMap &metadata)
{
    if (!modelUrl.isLocalFile()) return result(false, QStringLiteral("Érvénytelen modellfájl."));
    const QString modelPath = QDir::cleanPath(modelUrl.toLocalFile());
    if (!isInside(modelPath, m_sharedRoot) || !QFileInfo::exists(modelPath))
        return result(false, QStringLiteral("Metaadat csak a Shared Storage modelljeihez menthető."));

    QJsonObject object;
    for (auto it = metadata.constBegin(); it != metadata.constEnd(); ++it)
        object.insert(it.key(), QJsonValue::fromVariant(it.value()));
    object.insert(QStringLiteral("modelFile"), QFileInfo(modelPath).fileName());
    object.insert(QStringLiteral("updatedBy"), QStringLiteral("FA3 Control Center"));

    QSaveFile file(metadataPathFor(modelPath));
    if (!file.open(QIODevice::WriteOnly)) return result(false, file.errorString());
    file.write(QJsonDocument(object).toJson(QJsonDocument::Indented));
    if (!file.commit()) return result(false, file.errorString());
    refresh();
    return result(true, QStringLiteral("Metaadat mentve."));
}

QVariantMap ModelLibraryService::setPreview(const QUrl &modelUrl, const QUrl &previewUrl)
{
    if (!modelUrl.isLocalFile() || !previewUrl.isLocalFile()) return result(false, QStringLiteral("Érvénytelen fájl."));
    const QString modelPath = QDir::cleanPath(modelUrl.toLocalFile());
    const QString previewPath = QDir::cleanPath(previewUrl.toLocalFile());
    if (!isInside(modelPath, m_sharedRoot) || !QFileInfo::exists(modelPath))
        return result(false, QStringLiteral("A modell nincs a Shared Storage-ban."));
    const QFileInfo previewInfo(previewPath);
    const QString ext = previewInfo.suffix().toLower();
    if (!previewExtensions().contains(ext)) return result(false, QStringLiteral("Az előnézet PNG/JPG/JPEG/WebP lehet."));

    for (const QString &oldExt : previewExtensions()) QFile::remove(modelPath + QStringLiteral(".preview.") + oldExt);
    const QString destination = modelPath + QStringLiteral(".preview.") + ext;
    if (!QFile::copy(previewPath, destination)) return result(false, QStringLiteral("Az előnézeti kép másolása sikertelen."));
    refresh();
    return result(true, QStringLiteral("Előnézeti kép frissítve."));
}

QVariantMap ModelLibraryService::setClientRoot(const QString &clientKey, const QUrl &directory)
{
    if (!directory.isValid() || !directory.isLocalFile()) return result(false, QStringLiteral("A kliens modellmappájának lokális mappának kell lennie."));
    const QString path = QDir::cleanPath(directory.toLocalFile());
    QSettings settings;
    settings.setValue(QStringLiteral("models/clients/") + clientKey + QStringLiteral("/root"), path);
    scanClients();
    return result(true, QStringLiteral("Kliens modellútvonal mentve."));
}

QVariantMap ModelLibraryService::linkClient(const QString &clientKey)
{
    const auto definitions = clientDefinitions();
    const auto it = std::find_if(definitions.begin(), definitions.end(), [&](const ClientDefinition &d) { return d.key == clientKey; });
    if (it == definitions.end()) return result(false, QStringLiteral("Ismeretlen kliens."));
    const QString rootPath = clientRootFor(*it);
    if (rootPath.isEmpty()) return result(false, QStringLiteral("Előbb állítsd be a kliens model mappáját."));
    if (!QDir().mkpath(rootPath)) return result(false, QStringLiteral("A kliens model mappa nem érhető el."));

    QStringList blocked;
    QStringList linked;
    for (const auto &mapping : it->links) {
        const QString target = QDir::cleanPath(categoryDirectory(mapping.first));
        const QString linkPath = QDir(rootPath).absoluteFilePath(mapping.second);
        const QFileInfo existing(linkPath);
        if (existing.isSymLink()) {
            if (QDir::cleanPath(existing.symLinkTarget()) == target) continue;
            blocked << QStringLiteral("%1 (másik link)").arg(mapping.second);
            continue;
        }
        if (existing.exists()) {
            QDir existingDir(linkPath);
            if (!existingDir.isEmpty(QDir::NoDotAndDotDot | QDir::AllEntries)) {
                blocked << QStringLiteral("%1 (nem üres; import/migráció szükséges)").arg(mapping.second);
                continue;
            }
            if (!QDir().rmdir(linkPath)) {
                blocked << QStringLiteral("%1 (nem távolítható el)").arg(mapping.second);
                continue;
            }
        }
        QDir().mkpath(QFileInfo(linkPath).dir().absolutePath());
        std::error_code ec;
        std::filesystem::create_directory_symlink(target.toStdString(), linkPath.toStdString(), ec);
        if (ec) blocked << QStringLiteral("%1 (%2)").arg(mapping.second, QString::fromStdString(ec.message()));
        else linked << mapping.second;
    }
    scanClients();
    if (!blocked.isEmpty())
        return result(false, QStringLiteral("Linkelt: %1. Blokkolt: %2").arg(linked.join(QStringLiteral(", ")), blocked.join(QStringLiteral(" | "))));
    return result(true, QStringLiteral("%1 model mappái a Shared Storage-ra vannak linkelve.").arg(it->name));
}

bool ModelLibraryService::urlContainsCredentialMaterial(const QUrl &url) const
{
    if (!url.userInfo().isEmpty()) return true;
    const QUrlQuery query(url);
    const QStringList suspicious = {QStringLiteral("token"), QStringLiteral("access_token"), QStringLiteral("api_key"), QStringLiteral("apikey"), QStringLiteral("key")};
    for (const auto &pair : query.queryItems()) {
        if (suspicious.contains(pair.first.toLower())) return true;
    }
    return false;
}

QString ModelLibraryService::chooseDownloadFileName() const
{
    QString name = cleanFileName(m_downloadRequestedName);
    if (!name.isEmpty()) return name;

    if (m_reply) {
        const QString disposition = m_reply->header(QNetworkRequest::ContentDispositionHeader).toString();
        const QRegularExpression re(QStringLiteral("filename\\*?=(?:UTF-8''|\")?([^\";]+)"), QRegularExpression::CaseInsensitiveOption);
        const auto match = re.match(disposition);
        if (match.hasMatch()) name = cleanFileName(QUrl::fromPercentEncoding(match.captured(1).trimmed().toUtf8()));
    }
    if (name.isEmpty()) name = cleanFileName(m_downloadUrl.fileName());
    return name;
}

bool ModelLibraryService::prepareDownloadFile()
{
    if (m_downloadFile) return true;
    const QString name = chooseDownloadFileName();
    if (name.isEmpty()) {
        resetDownloadState(QStringLiteral("A letöltéshez nem állapítható meg fájlnév; adj meg fájlnevet."), false, 0);
        if (m_reply) m_reply->abort();
        return false;
    }
    const QString destination = QDir(categoryDirectory(m_downloadCategory)).absoluteFilePath(name);
    if (QFileInfo::exists(destination)) {
        resetDownloadState(QStringLiteral("A célfájl már létezik: %1").arg(name), false, 0);
        if (m_reply) m_reply->abort();
        return false;
    }
    m_downloadDestination = destination;
    m_downloadFile = new QSaveFile(destination);
    if (!m_downloadFile->open(QIODevice::WriteOnly)) {
        resetDownloadState(m_downloadFile->errorString(), false, 0);
        delete m_downloadFile;
        m_downloadFile = nullptr;
        if (m_reply) m_reply->abort();
        return false;
    }
    return true;
}

void ModelLibraryService::resetDownloadState(const QString &status, bool active, int progress)
{
    m_downloadStatus = status;
    m_downloadActive = active;
    m_downloadProgress = progress;
    emit downloadStateChanged();
}

QVariantMap ModelLibraryService::startDownload(const QUrl &url, const QString &category, const QString &fileName)
{
    if (m_downloadActive) return result(false, QStringLiteral("Már fut letöltés."));
    if (!url.isValid() || url.scheme().toLower() != QStringLiteral("https"))
        return result(false, QStringLiteral("Csak HTTPS modell-letöltés engedélyezett."));
    if (urlContainsCredentialMaterial(url))
        return result(false, QStringLiteral("Credential/token nem kerülhet URL-be. Hitelesített CivitAI/Hugging Face letöltéshez a Token Control Center / SecretRef broker integráció szükséges."));

    m_downloadUrl = url;
    m_downloadCategory = kCategories.contains(category) ? category : QStringLiteral("checkpoints");
    m_downloadRequestedName = fileName;
    m_downloadDestination.clear();
    delete m_downloadFile;
    m_downloadFile = nullptr;

    QNetworkRequest request(url);
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    request.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("FA3-Control-Center/0.3"));
    m_reply = m_network.get(request);
    resetDownloadState(QStringLiteral("Kapcsolódás…"), true, 0);

    connect(m_reply, &QNetworkReply::metaDataChanged, this, [this]() {
        if (!m_downloadActive || !m_reply) return;
        prepareDownloadFile();
    });
    connect(m_reply, &QIODevice::readyRead, this, [this]() {
        if (!m_reply || !m_downloadActive) return;
        if (!prepareDownloadFile()) return;
        const QByteArray data = m_reply->readAll();
        if (!data.isEmpty() && m_downloadFile->write(data) != data.size()) {
            resetDownloadState(QStringLiteral("Írási hiba: %1").arg(m_downloadFile->errorString()), false, m_downloadProgress);
            m_reply->abort();
        }
    });
    connect(m_reply, &QNetworkReply::downloadProgress, this, [this](qint64 received, qint64 total) {
        if (total > 0) m_downloadProgress = static_cast<int>((received * 100) / total);
        else m_downloadProgress = 0;
        m_downloadStatus = total > 0
            ? QStringLiteral("Letöltés: %1 / %2").arg(humanReadableSize(received), humanReadableSize(total))
            : QStringLiteral("Letöltés: %1").arg(humanReadableSize(received));
        emit downloadStateChanged();
    });
    connect(m_reply, &QNetworkReply::finished, this, [this]() {
        const bool networkOk = m_reply && m_reply->error() == QNetworkReply::NoError;
        QString finalStatus;
        bool commitOk = false;
        if (networkOk && prepareDownloadFile() && m_downloadFile) {
            const QByteArray tail = m_reply->readAll();
            if (!tail.isEmpty()) m_downloadFile->write(tail);
            commitOk = m_downloadFile->commit();
            finalStatus = commitOk
                ? QStringLiteral("Letöltve: %1").arg(QFileInfo(m_downloadDestination).fileName())
                : QStringLiteral("A fájl véglegesítése sikertelen: %1").arg(m_downloadFile->errorString());
        } else {
            if (m_downloadFile) m_downloadFile->cancelWriting();
            finalStatus = m_reply ? QStringLiteral("Letöltési hiba: %1").arg(m_reply->errorString()) : QStringLiteral("Letöltés megszakítva.");
        }
        delete m_downloadFile;
        m_downloadFile = nullptr;
        if (m_reply) m_reply->deleteLater();
        m_reply = nullptr;
        resetDownloadState(finalStatus, false, commitOk ? 100 : 0);
        if (commitOk) refresh();
    });

    return result(true, QStringLiteral("Letöltés elindítva."));
}

void ModelLibraryService::cancelDownload()
{
    if (m_reply) {
        m_reply->abort();
        m_reply->deleteLater();
        m_reply = nullptr;
    }
    if (m_downloadFile) {
        m_downloadFile->cancelWriting();
        delete m_downloadFile;
        m_downloadFile = nullptr;
    }
    if (m_downloadActive) resetDownloadState(QStringLiteral("Letöltés megszakítva."), false, 0);
}

bool ModelLibraryService::openLocalPath(const QUrl &url) const
{
    if (!url.isValid()) return false;
    return QDesktopServices::openUrl(url);
}
