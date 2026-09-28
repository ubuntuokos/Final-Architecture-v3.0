#include "StudioBackend.h"

#include <QDateTime>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QtGlobal>
#include <QUuid>

namespace {
const QStringList kCapabilities = {
    QStringLiteral("IMAGE_T2I"),
    QStringLiteral("IMAGE_I2I"),
    QStringLiteral("VIDEO_T2V"),
    QStringLiteral("VIDEO_I2V"),
    QStringLiteral("VIDEO_TI2V"),
    QStringLiteral("VIDEO_S2V"),
    QStringLiteral("LIPSYNC"),
    QStringLiteral("CHARACTER_ANIMATE")
};

QString requestRoot()
{
    QString state = qEnvironmentVariable("XDG_STATE_HOME");
    if (state.trimmed().isEmpty())
        state = QDir::homePath() + QStringLiteral("/.local/state");
    return QDir::cleanPath(state + QStringLiteral("/fa3/generative-media-studio/requests"));
}
}

StudioBackend::StudioBackend(QObject *parent)
    : QObject(parent),
      m_statusText(QStringLiteral("Kész. A Studio provider-semleges kérést állít össze; közvetlen provider-hívást nem végez."))
{
}

QString StudioBackend::statusText() const { return m_statusText; }
QString StudioBackend::lastRequestPath() const { return m_lastRequestPath; }
QStringList StudioBackend::capabilities() const { return kCapabilities; }

bool StudioBackend::isVideoCapability(const QString &capability)
{
    return capability.startsWith(QStringLiteral("VIDEO_"))
        || capability == QStringLiteral("LIPSYNC")
        || capability == QStringLiteral("CHARACTER_ANIMATE");
}

bool StudioBackend::isKnownCapability(const QString &capability)
{
    return kCapabilities.contains(capability);
}

void StudioBackend::setStatusText(const QString &value)
{
    if (m_statusText == value) return;
    m_statusText = value;
    emit statusTextChanged();
}

void StudioBackend::setLastRequestPath(const QString &value)
{
    if (m_lastRequestPath == value) return;
    m_lastRequestPath = value;
    emit lastRequestPathChanged();
}

bool StudioBackend::compileRequest(
    const QString &capability,
    const QString &prompt,
    int durationSeconds,
    const QString &aspectRatio,
    const QString &referencesText)
{
    if (!isKnownCapability(capability)) {
        setStatusText(QStringLiteral("BLOCKED: ismeretlen capability."));
        return false;
    }
    if (prompt.trimmed().isEmpty()) {
        setStatusText(QStringLiteral("BLOCKED: a kreatív intent/prompt nem lehet üres."));
        return false;
    }
    if (isVideoCapability(capability) && (durationSeconds < 6 || durationSeconds > 20)) {
        setStatusText(QStringLiteral("BLOCKED: a Studio shot-hossz 6 és 20 másodperc között állítható."));
        return false;
    }

    QJsonArray refs;
    const QStringList lines = referencesText.split(QLatin1Char('\n'), Qt::SkipEmptyParts);
    for (const QString &line : lines) {
        const QString ref = line.trimmed();
        if (!ref.isEmpty()) refs.append(QJsonObject{{QStringLiteral("ref"), ref}});
    }

    const QString requestId = QUuid::createUuid().toString(QUuid::WithoutBraces);
    QJsonObject intent{
        {QStringLiteral("prompt"), prompt.trimmed()},
        {QStringLiteral("aspect_ratio"), aspectRatio.trimmed().isEmpty() ? QStringLiteral("AUTO") : aspectRatio.trimmed()},
        {QStringLiteral("references"), refs}
    };
    if (isVideoCapability(capability))
        intent.insert(QStringLiteral("duration_seconds"), durationSeconds);

    QJsonObject root{
        {QStringLiteral("schema"), QStringLiteral("fa3.generative-media-studio-request.v1")},
        {QStringLiteral("request_id"), requestId},
        {QStringLiteral("created_at"), QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {QStringLiteral("application_id"), QStringLiteral("FA3-GENERATIVE-MEDIA-STUDIO-001")},
        {QStringLiteral("capability"), capability},
        {QStringLiteral("intent"), intent},
        {QStringLiteral("route"), QJsonObject{
            {QStringLiteral("logical_route"), QStringLiteral("creative.generative-media")},
            {QStringLiteral("authority"), QStringLiteral("FA3-AUTH-MODEL-ROUTER-001")},
            {QStringLiteral("physical_provider_pin"), false},
            {QStringLiteral("physical_model_pin"), false}
        }},
        {QStringLiteral("authority_handoff"), QJsonObject{
            {QStringLiteral("action_execution"), QStringLiteral("FA3-UNIFIED-ACTION-FABRIC-001")},
            {QStringLiteral("host_resources"), QStringLiteral("FA3-AUTH-HOST-RESOURCE-BROKER-001")},
            {QStringLiteral("secrets"), QStringLiteral("FA3-SECRET-BROKER-001")},
            {QStringLiteral("evidence"), QStringLiteral("FA3-AUTH-OBS-EVIDENCE-001")}
        }},
        {QStringLiteral("hardware_audit"), QJsonObject{
            {QStringLiteral("vendor_neutral"), true},
            {QStringLiteral("cpu_only_architecture_supported"), true},
            {QStringLiteral("accelerator_cardinality"), QStringLiteral("0..N")},
            {QStringLiteral("placement"), QStringLiteral("HRB_DOWNSTREAM")}
        }},
        {QStringLiteral("state"), QStringLiteral("PENDING_ADMISSION")},
        {QStringLiteral("runtime_success_claim"), false}
    };

    QDir dir;
    const QString rootPath = requestRoot();
    if (!dir.mkpath(rootPath)) {
        setStatusText(QStringLiteral("ERROR: a request state könyvtár nem hozható létre."));
        return false;
    }

    const QString path = rootPath + QLatin1Char('/') + requestId + QStringLiteral(".json");
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        setStatusText(QStringLiteral("ERROR: a request fájl nem nyitható meg írásra."));
        return false;
    }
    file.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        setStatusText(QStringLiteral("ERROR: az atomikus request mentés sikertelen."));
        return false;
    }

    setLastRequestPath(path);
    setStatusText(QStringLiteral("PENDING_ADMISSION: a provider-semleges kérés elkészült. Model Router/HRB/UAF handoff szükséges."));
    return true;
}
