#include "AppCatalogService.h"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcessEnvironment>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUrl>

namespace {
constexpr auto kCatalogResource = ":/fa3/canonical/FA3-AI-STUDIO-APP-CATALOG-001.json";
constexpr auto kCatalogRelative = "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json";
constexpr auto kRecipeRelative = "deployment/app-providers";

QString compactMessage(QProcess &process)
{
    auto output = QString::fromUtf8(process.readAllStandardOutput()).trimmed();
    const auto error = QString::fromUtf8(process.readAllStandardError()).trimmed();
    if (output.isEmpty()) output = error;
    if (output.size() > 1200) output = output.left(1200) + QStringLiteral("…");
    return output;
}
}

AppCatalogService::AppCatalogService(QObject *parent)
    : QObject(parent), m_repoRoot(discoverRepositoryRoot())
{
    connect(&m_process, &QProcess::stateChanged, this, [this] {
        emit installBusyChanged();
    });

    connect(&m_process, &QProcess::finished, this,
            [this](int exitCode, QProcess::ExitStatus exitStatus) {
        const auto appId = m_activeAppId;
        const auto operation = m_activeOperation;
        const bool success = exitStatus == QProcess::NormalExit && exitCode == 0;
        auto message = compactMessage(m_process);
        if (message.isEmpty()) {
            message = success ? QStringLiteral("Művelet befejezve.")
                              : QStringLiteral("A provider művelet hibával állt le.");
        }

        if (operation == QStringLiteral("install")) {
            setRuntimeState(appId,
                            success ? QStringLiteral("INSTALLED") : QStringLiteral("READY_TO_INSTALL"),
                            message);
        }
        if (!success) setLastError(message);

        m_activeAppId.clear();
        m_activeOperation.clear();
        emit operationFinished(appId, operation, success, message);
    });

    connect(&m_process, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
        if (error != QProcess::FailedToStart || m_activeAppId.isEmpty()) return;
        const auto appId = m_activeAppId;
        const auto operation = m_activeOperation;
        const auto message = QStringLiteral("Az FA3 app-provisioner nem indítható.");
        if (operation == QStringLiteral("install")) {
            setRuntimeState(appId, QStringLiteral("READY_TO_INSTALL"), message);
        }
        setLastError(message);
        m_activeAppId.clear();
        m_activeOperation.clear();
        emit operationFinished(appId, operation, false, message);
    });

    refresh();
}

QString AppCatalogService::discoverRepositoryRoot() const
{
    const auto envRoot = qEnvironmentVariable("FA3_REPO_ROOT");
    if (!envRoot.isEmpty() && QFileInfo::exists(QDir(envRoot).filePath(kCatalogRelative))) {
        return QDir(envRoot).absolutePath();
    }

    const QStringList candidates = {QDir::currentPath(), QCoreApplication::applicationDirPath()};
    for (const auto &candidate : candidates) {
        QDir dir(candidate);
        for (int depth = 0; depth < 8; ++depth) {
            if (QFileInfo::exists(dir.filePath(kCatalogRelative))) return dir.absolutePath();
            if (!dir.cdUp()) break;
        }
    }
    return {};
}

QString AppCatalogService::requestDirectory() const
{
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    return QDir(base).filePath(QStringLiteral("app-requests"));
}

QString AppCatalogService::stateDirectory() const
{
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    return QDir(base).filePath(QStringLiteral("app-state"));
}

void AppCatalogService::setLastError(const QString &message)
{
    if (m_lastError == message) return;
    m_lastError = message;
    emit lastErrorChanged();
}

int AppCatalogService::indexOf(const QString &appId) const
{
    for (int index = 0; index < m_applications.size(); ++index) {
        if (m_applications.at(index).toMap().value(QStringLiteral("id")).toString() == appId) return index;
    }
    return -1;
}

QVariantMap AppCatalogService::application(const QString &appId) const
{
    const auto index = indexOf(appId);
    return index >= 0 ? m_applications.at(index).toMap() : QVariantMap{};
}

bool AppCatalogService::isInstalledFromProbe(const QVariantMap &application) const
{
    const auto probes = application.value(QStringLiteral("probe_executables")).toStringList();
    for (const auto &probe : probes) {
        if (!probe.trimmed().isEmpty() && !QStandardPaths::findExecutable(probe.trimmed()).isEmpty()) return true;
    }
    return false;
}

bool AppCatalogService::hasInstallMarker(const QString &appId) const
{
    return QFileInfo::exists(QDir(stateDirectory()).filePath(appId + QStringLiteral(".json")));
}

bool AppCatalogService::loadCatalog()
{
    QFile file(QString::fromLatin1(kCatalogResource));
    if (!file.open(QIODevice::ReadOnly)) {
        if (m_repoRoot.isEmpty()) {
            setLastError(QStringLiteral("Az AI Studio canonical alkalmazáskatalógusa nem található."));
            return false;
        }
        file.setFileName(QDir(m_repoRoot).filePath(kCatalogRelative));
        if (!file.open(QIODevice::ReadOnly)) {
            setLastError(QStringLiteral("Az AI Studio canonical alkalmazáskatalógusa nem olvasható."));
            return false;
        }
    }

    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        setLastError(QStringLiteral("Az AI Studio alkalmazáskatalógusa érvénytelen JSON."));
        return false;
    }

    const auto root = document.object();
    if (root.value(QStringLiteral("catalog_mode")).toString() != QStringLiteral("ALLOWLIST") ||
        root.value(QStringLiteral("user_defined_entries_allowed")).toBool(true)) {
        setLastError(QStringLiteral("Az AI Studio katalógus fail-closed ellenőrzése sikertelen."));
        return false;
    }

    QVariantList next;
    const auto applications = root.value(QStringLiteral("applications")).toArray();
    for (const auto &value : applications) {
        if (!value.isObject()) continue;
        const auto object = value.toObject();
        auto row = object.toVariantMap();
        const auto appId = object.value(QStringLiteral("id")).toString().trimmed();
        const auto admission = object.value(QStringLiteral("admission")).toString();
        const auto installMode = object.value(QStringLiteral("install_mode")).toString();
        const bool directSource = object.value(QStringLiteral("direct_source_install_allowed")).toBool(true);
        if (appId.isEmpty() || admission != QStringLiteral("APPROVED") ||
            installMode != QStringLiteral("FIRST_USE") || directSource) {
            continue;
        }

        bool recipeAvailable = false;
        const auto recipe = object.value(QStringLiteral("provider_recipe")).toString();
        if (!recipe.isEmpty() && !m_repoRoot.isEmpty()) {
            recipeAvailable = QFileInfo::exists(QDir(m_repoRoot).filePath(
                QStringLiteral("%1/%2").arg(QString::fromLatin1(kRecipeRelative), recipe)));
        }
        const auto installedRecipe = QDir(QStringLiteral("/usr/share/fa3/app-providers")).filePath(recipe);
        if (!recipe.isEmpty() && QFileInfo::exists(installedRecipe)) recipeAvailable = true;

        row.insert(QStringLiteral("recipe_available"), recipeAvailable);
        QString runtimeState;
        if (isInstalledFromProbe(row) || hasInstallMarker(appId)) {
            runtimeState = QStringLiteral("INSTALLED");
        } else if (!object.value(QStringLiteral("installable")).toBool(false)) {
            runtimeState = QStringLiteral("INCOMPATIBLE");
        } else if (!recipeAvailable) {
            runtimeState = QStringLiteral("RECIPE_REQUIRED");
        } else {
            runtimeState = QStringLiteral("READY_TO_INSTALL");
        }
        row.insert(QStringLiteral("runtime_state"), runtimeState);
        row.insert(QStringLiteral("runtime_message"), QString());
        next.append(row);
    }

    m_applications = next;
    setLastError({});
    emit applicationsChanged();
    return true;
}

void AppCatalogService::refreshPendingRequestCount()
{
    const QDir dir(requestDirectory());
    const auto count = dir.exists() ? dir.entryList({QStringLiteral("*.json")}, QDir::Files).size() : 0;
    if (m_pendingRequestCount == count) return;
    m_pendingRequestCount = count;
    emit requestQueueChanged();
}

void AppCatalogService::refresh()
{
    const auto discovered = discoverRepositoryRoot();
    if (!discovered.isEmpty()) m_repoRoot = discovered;
    loadCatalog();
    refreshPendingRequestCount();
}

void AppCatalogService::setRuntimeState(const QString &appId, const QString &state, const QString &message)
{
    const auto index = indexOf(appId);
    if (index < 0) return;
    auto row = m_applications.at(index).toMap();
    row.insert(QStringLiteral("runtime_state"), state);
    row.insert(QStringLiteral("runtime_message"), message);
    m_applications[index] = row;
    emit applicationsChanged();
}

bool AppCatalogService::requestFirstUse(const QString &appId)
{
    const auto row = application(appId);
    if (row.isEmpty()) {
        setLastError(QStringLiteral("Ismeretlen alkalmazás: telepítés megtagadva."));
        return false;
    }
    if (row.value(QStringLiteral("runtime_state")).toString() == QStringLiteral("INSTALLED")) {
        return launchInstalled(appId);
    }
    if (!row.value(QStringLiteral("recipe_available")).toBool()) {
        setLastError(QStringLiteral("A jóváhagyott provider telepítési receptje még nincs materializálva."));
        emit operationFinished(appId, QStringLiteral("install"), false, m_lastError);
        return false;
    }
    emit installationConfirmationRequired(appId, row.value(QStringLiteral("name")).toString());
    return true;
}

bool AppCatalogService::installApproved(const QString &appId)
{
    const auto row = application(appId);
    const bool directSourceAllowed =
        !row.contains(QStringLiteral("direct_source_install_allowed")) ||
        row.value(QStringLiteral("direct_source_install_allowed")).toBool();
    const bool installable =
        row.contains(QStringLiteral("installable")) &&
        row.value(QStringLiteral("installable")).toBool();
    if (row.isEmpty() || row.value(QStringLiteral("admission")).toString() != QStringLiteral("APPROVED") ||
        row.value(QStringLiteral("install_mode")).toString() != QStringLiteral("FIRST_USE") ||
        directSourceAllowed || !installable ||
        !row.value(QStringLiteral("recipe_available")).toBool()) {
        setLastError(QStringLiteral("Az alkalmazás nem jogosult first-use materializációra."));
        return false;
    }
    if (installBusy()) {
        setLastError(QStringLiteral("Egy másik provider művelet már fut."));
        return false;
    }

    setRuntimeState(appId, QStringLiteral("INSTALLING"), QStringLiteral("Materializáció folyamatban…"));
    if (!startProvisioner(QStringLiteral("install"), appId)) {
        setRuntimeState(appId, QStringLiteral("READY_TO_INSTALL"), m_lastError);
        return false;
    }
    return true;
}

bool AppCatalogService::launchInstalled(const QString &appId)
{
    const auto row = application(appId);
    if (row.isEmpty() || row.value(QStringLiteral("runtime_state")).toString() != QStringLiteral("INSTALLED")) {
        setLastError(QStringLiteral("Az alkalmazás nincs telepített állapotban."));
        return false;
    }
    if (installBusy()) {
        setLastError(QStringLiteral("Egy másik provider művelet már fut."));
        return false;
    }
    return startProvisioner(QStringLiteral("launch"), appId);
}

bool AppCatalogService::resolveProvisioner(QString *program, QStringList *prefixArguments) const
{
    if (!program || !prefixArguments) return false;
    program->clear();
    prefixArguments->clear();

    QStringList candidates;
    const auto envProvisioner = qEnvironmentVariable("FA3_APP_PROVISIONER");
    if (!envProvisioner.isEmpty()) candidates << envProvisioner;
    if (!m_repoRoot.isEmpty()) candidates << QDir(m_repoRoot).filePath(QStringLiteral("scripts/fa3-app-provisioner.py"));
    candidates << QDir(QCoreApplication::applicationDirPath()).filePath(QStringLiteral("fa3-app-provisioner.py"));
    candidates << QStringLiteral("/usr/libexec/fa3-app-provisioner.py");
    candidates << QStringLiteral("/usr/local/libexec/fa3-app-provisioner.py");

    for (const auto &candidate : candidates) {
        const QFileInfo info(candidate);
        if (!info.exists() || !info.isFile()) continue;
        if (candidate.endsWith(QStringLiteral(".py"), Qt::CaseInsensitive)) {
            const auto python = QStandardPaths::findExecutable(QStringLiteral("python3"));
            if (python.isEmpty()) continue;
            *program = python;
            *prefixArguments = {info.absoluteFilePath()};
            return true;
        }
        if (info.isExecutable()) {
            *program = info.absoluteFilePath();
            return true;
        }
    }
    return false;
}

bool AppCatalogService::startProvisioner(const QString &operation, const QString &appId)
{
    QString program;
    QStringList arguments;
    if (!resolveProvisioner(&program, &arguments)) {
        setLastError(QStringLiteral("Az FA3 app-provisioner nem található."));
        return false;
    }

    if (!m_repoRoot.isEmpty()) arguments << QStringLiteral("--repo-root") << m_repoRoot;
    arguments << operation << appId;

    QDir().mkpath(stateDirectory());
    auto environment = QProcessEnvironment::systemEnvironment();
    environment.insert(QStringLiteral("FA3_APP_STATE_DIR"), stateDirectory());
    m_process.setProcessEnvironment(environment);
    m_process.setProgram(program);
    m_process.setArguments(arguments);
    m_process.setProcessChannelMode(QProcess::SeparateChannels);
    m_activeAppId = appId;
    m_activeOperation = operation;
    m_process.start();
    if (!m_process.waitForStarted(1500)) {
        setLastError(QStringLiteral("Az FA3 app-provisioner indítása sikertelen."));
        m_activeAppId.clear();
        m_activeOperation.clear();
        return false;
    }
    return true;
}

QString AppCatalogService::submitApplicationRequest(const QString &sourceUrl,
                                                    const QString &category,
                                                    const QString &rationale)
{
    const auto raw = sourceUrl.trimmed();
    if (raw.isEmpty() || raw.size() > 2048) {
        setLastError(QStringLiteral("Adj meg egy érvényes HTTPS forrás URL-t."));
        return {};
    }

    const QUrl parsed(raw, QUrl::StrictMode);
    const auto host = parsed.host().toLower();
    if (!parsed.isValid() || parsed.scheme().toLower() != QStringLiteral("https") || host.isEmpty() ||
        !parsed.userInfo().isEmpty() || host == QStringLiteral("localhost") || host == QStringLiteral("127.0.0.1") ||
        host == QStringLiteral("::1") || host.endsWith(QStringLiteral(".local"))) {
        setLastError(QStringLiteral("Csak publikus HTTPS projektforrás küldhető review-ra."));
        return {};
    }

    const QStringList allowedCategories = {
        QStringLiteral("Image"), QStringLiteral("Video"), QStringLiteral("Animation"),
        QStringLiteral("3D / VFX"), QStringLiteral("Audio"), QStringLiteral("Music"),
        QStringLiteral("Story / Screenplay"), QStringLiteral("Office"), QStringLiteral("Marketing"),
        QStringLiteral("Weboldal"), QStringLiteral("Prezentáció"), QStringLiteral("Other")
    };
    const auto safeCategory = allowedCategories.contains(category) ? category : QStringLiteral("Other");
    const auto safeRationale = rationale.trimmed().left(4000);
    const auto normalizedUrl = parsed.adjusted(QUrl::RemoveFragment | QUrl::StripTrailingSlash).toString(QUrl::FullyEncoded);
    const auto digest = QCryptographicHash::hash(normalizedUrl.toUtf8(), QCryptographicHash::Sha256).toHex().left(12);
    const auto stamp = QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMddTHHmmsszzzZ"));
    const auto requestId = QStringLiteral("FA3-APP-REQUEST-%1-%2").arg(stamp, QString::fromLatin1(digest));

    QDir dir(requestDirectory());
    if (!dir.mkpath(QStringLiteral("."))) {
        setLastError(QStringLiteral("Az alkalmazásigény kimenő sora nem hozható létre."));
        return {};
    }

    QJsonObject object{
        {QStringLiteral("schema"), QStringLiteral("fa3.application-request-instance.v1")},
        {QStringLiteral("id"), requestId},
        {QStringLiteral("policy"), QStringLiteral("FA3-APP-REQUEST-001")},
        {QStringLiteral("status"), QStringLiteral("PENDING_REVIEW")},
        {QStringLiteral("created_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("created_by"), QStringLiteral("FA3 Control Center")},
        {QStringLiteral("source_url"), normalizedUrl},
        {QStringLiteral("category"), safeCategory},
        {QStringLiteral("rationale"), safeRationale},
        {QStringLiteral("transport"), QStringLiteral("FA3_REVIEW_OUTBOX")},
        {QStringLiteral("executable"), false},
        {QStringLiteral("install_authority_granted"), false},
        {QStringLiteral("catalog_membership_granted"), false},
        {QStringLiteral("automatic_clone_allowed"), false}
    };

    const auto filePath = dir.filePath(requestId + QStringLiteral(".json"));
    QSaveFile file(filePath);
    if (!file.open(QIODevice::WriteOnly)) {
        setLastError(QStringLiteral("Az alkalmazásigény nem írható a kimenő sorba."));
        return {};
    }
    file.write(QJsonDocument(object).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        setLastError(QStringLiteral("Az alkalmazásigény mentése sikertelen."));
        return {};
    }

    setLastError({});
    refreshPendingRequestCount();
    emit applicationRequestQueued(requestId, filePath);
    return requestId;
}
