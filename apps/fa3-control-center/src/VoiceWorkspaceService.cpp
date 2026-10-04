#include "VoiceWorkspaceService.h"

#include <QDateTime>
#include <QAudioDevice>
#include <QAudioSource>
#include <QDataStream>
#include <QMediaDevices>
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUuid>

namespace {
QString nowUtc()
{
    return QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
}

QString clean(const QString &value)
{
    return value.trimmed();
}

QVariantMap objectBucket(const QVariantMap &state, const QString &name)
{
    return state.value(name).toMap();
}
}

VoiceWorkspaceService::VoiceWorkspaceService(const QString &repoRoot, QObject *parent)
    : QObject(parent), m_repoRoot(QDir(repoRoot).absolutePath())
{
    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    QDir dir(base);
    dir.mkpath(QStringLiteral("voice"));
    m_statePath = dir.filePath(QStringLiteral("voice/workspace.json"));
    load();
}

QVariantMap VoiceWorkspaceService::baseState() const
{
    QVariantMap activity{
        {QStringLiteral("state"), QStringLiteral("IDLE")},
        {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
        {QStringLiteral("actor"), QString()},
        {QStringLiteral("voice_profile_id"), QString()},
        {QStringLiteral("job_id"), QString()},
        {QStringLiteral("visible"), false}
    };
    return {
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-workspace-state.v1")},
        {QStringLiteral("version"), 1},
        {QStringLiteral("voice_profiles"), QVariantMap{}},
        {QStringLiteral("captures"), QVariantMap{}},
        {QStringLiteral("jobs"), QVariantMap{}},
        {QStringLiteral("handoffs"), QVariantMap{}},
        {QStringLiteral("quick_dub_plans"), QVariantMap{}},
        {QStringLiteral("activity"), activity}
    };
}

void VoiceWorkspaceService::load()
{
    QFile file(m_statePath);
    if (!file.open(QIODevice::ReadOnly)) {
        m_state = baseState();
        save();
        emit stateChanged();
        return;
    }
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) {
        m_state = baseState();
        setError(QStringLiteral("Voice workspace state is invalid; using fail-closed empty state."));
        emit stateChanged();
        return;
    }
    const auto value = document.object().toVariantMap();
    if (value.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.voice-workspace-state.v1")) {
        m_state = baseState();
        setError(QStringLiteral("Voice workspace schema mismatch; state was not imported."));
        emit stateChanged();
        return;
    }
    m_state = value;
    emit stateChanged();
}

bool VoiceWorkspaceService::save()
{
    auto version = m_state.value(QStringLiteral("version")).toInt();
    m_state.insert(QStringLiteral("version"), version + 1);
    QSaveFile file(m_statePath);
    if (!file.open(QIODevice::WriteOnly)) {
        setError(QStringLiteral("Cannot open Voice workspace state for atomic write."));
        return false;
    }
    file.write(QJsonDocument::fromVariant(m_state).toJson(QJsonDocument::Indented));
    if (!file.commit()) {
        setError(QStringLiteral("Cannot commit Voice workspace state."));
        return false;
    }
    emit stateChanged();
    return true;
}

QString VoiceWorkspaceService::makeId(const QString &prefix)
{
    return prefix + QStringLiteral("-") + QUuid::createUuid().toString(QUuid::WithoutBraces);
}

QVariantList VoiceWorkspaceService::bucketValues(const QString &bucket) const
{
    QVariantList rows;
    const auto map = objectBucket(m_state, bucket);
    for (auto it = map.cbegin(); it != map.cend(); ++it) rows.append(it.value());
    return rows;
}

QVariantList VoiceWorkspaceService::voiceProfiles() const { return bucketValues(QStringLiteral("voice_profiles")); }
QVariantList VoiceWorkspaceService::jobs() const { return bucketValues(QStringLiteral("jobs")); }
QVariantList VoiceWorkspaceService::captures() const { return bucketValues(QStringLiteral("captures")); }
QVariantList VoiceWorkspaceService::handoffs() const { return bucketValues(QStringLiteral("handoffs")); }
QVariantMap VoiceWorkspaceService::activity() const { return m_state.value(QStringLiteral("activity")).toMap(); }

void VoiceWorkspaceService::setError(const QString &message)
{
    m_lastError = message;
    emit lastErrorChanged();
}

void VoiceWorkspaceService::setOperation(const QString &message)
{
    m_lastOperation = message;
    emit lastOperationChanged();
}

void VoiceWorkspaceService::refresh()
{
    m_lastError.clear();
    emit lastErrorChanged();
    load();
}

QVariantMap VoiceWorkspaceService::findObject(const QString &bucket, const QString &idKey, const QString &id) const
{
    const auto map = objectBucket(m_state, bucket);
    const auto direct = map.value(id).toMap();
    if (!direct.isEmpty()) return direct;
    for (auto it = map.cbegin(); it != map.cend(); ++it) {
        const auto row = it.value().toMap();
        if (row.value(idKey).toString() == id) return row;
    }
    return {};
}

QVariantMap VoiceWorkspaceService::upsertVoiceProfile(const QString &voiceProfileId,
                                                       const QString &name,
                                                       const QString &language,
                                                       const QString &identityKind,
                                                       const QString &consentStatus,
                                                       const QString &consentProofRef)
{
    const auto id = clean(voiceProfileId);
    const auto displayName = clean(name);
    const auto locale = clean(language);
    const auto kind = clean(identityKind).toUpper();
    const auto consent = clean(consentStatus).toUpper();
    if (id.isEmpty() || displayName.isEmpty() || locale.isEmpty()) {
        setError(QStringLiteral("Voice Profile id, name and language are required."));
        return {};
    }
    if (kind != QStringLiteral("SYNTHETIC") && kind != QStringLiteral("HUMAN_AUTHORIZED") && kind != QStringLiteral("PRESET")) {
        setError(QStringLiteral("Invalid Voice Profile identity kind."));
        return {};
    }
    if (kind == QStringLiteral("HUMAN_AUTHORIZED")
        && (consent != QStringLiteral("GRANTED") || clean(consentProofRef).isEmpty())) {
        setError(QStringLiteral("Human voice profile requires GRANTED consent proof."));
        return {};
    }

    auto profiles = objectBucket(m_state, QStringLiteral("voice_profiles"));
    const auto old = profiles.value(id).toMap();
    const auto now = nowUtc();
    QVariantMap row{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-profile-record.v1")},
        {QStringLiteral("voice_profile_id"), id},
        {QStringLiteral("name"), displayName},
        {QStringLiteral("languages"), QVariantList{locale}},
        {QStringLiteral("identity_kind"), kind},
        {QStringLiteral("consent_status"), consent.isEmpty() ? QStringLiteral("NOT_REQUIRED") : consent},
        {QStringLiteral("consent_proof_ref"), clean(consentProofRef)},
        {QStringLiteral("styles"), QVariantList{}},
        {QStringLiteral("effects_preset"), QStringLiteral("NONE")},
        {QStringLiteral("rights_status"), QStringLiteral("UNVERIFIED")},
        {QStringLiteral("created_at"), old.value(QStringLiteral("created_at"), now)},
        {QStringLiteral("updated_at"), now}
    };
    profiles.insert(id, row);
    m_state.insert(QStringLiteral("voice_profiles"), profiles);
    if (!save()) return {};
    setOperation(QStringLiteral("Voice Profile saved locally; canonical/provider authority unchanged."));
    return row;
}

bool VoiceWorkspaceService::writeWavHeader(QFile &file, const QAudioFormat &format, qint64 dataBytes)
{
    if (!file.isOpen() || format.sampleFormat() != QAudioFormat::Int16
        || format.sampleRate() <= 0 || format.channelCount() <= 0 || dataBytes < 0) return false;

    const quint16 channels = quint16(format.channelCount());
    const quint32 sampleRate = quint32(format.sampleRate());
    const quint16 bitsPerSample = 16;
    const quint16 blockAlign = quint16(channels * bitsPerSample / 8);
    const quint32 byteRate = sampleRate * blockAlign;
    const quint32 dataSize = quint32(qMin<qint64>(dataBytes, 0xffffffffLL));
    const quint32 riffSize = 36u + dataSize;

    if (!file.seek(0)) return false;
    QDataStream out(&file);
    out.setByteOrder(QDataStream::LittleEndian);
    out.writeRawData("RIFF", 4); out << riffSize;
    out.writeRawData("WAVE", 4);
    out.writeRawData("fmt ", 4); out << quint32(16) << quint16(1) << channels << sampleRate << byteRate << blockAlign << bitsPerSample;
    out.writeRawData("data", 4); out << dataSize;
    return out.status() == QDataStream::Ok;
}

bool VoiceWorkspaceService::startMicrophoneCapture(const QString &language)
{
    if (m_recording) {
        setError(QStringLiteral("Microphone capture is already active."));
        return false;
    }
    const auto locale = clean(language);
    if (locale.isEmpty()) {
        setError(QStringLiteral("Capture language is required."));
        return false;
    }
    const auto device = QMediaDevices::defaultAudioInput();
    if (device.isNull()) {
        setError(QStringLiteral("No default audio input device is available."));
        return false;
    }

    QAudioFormat format;
    format.setSampleRate(16000);
    format.setChannelCount(1);
    format.setSampleFormat(QAudioFormat::Int16);
    if (!device.isFormatSupported(format)) {
        setError(QStringLiteral("Default microphone does not support required 16 kHz mono Int16 capture; no silent format fallback."));
        return false;
    }

    const auto base = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    QDir dir(base);
    if (!dir.mkpath(QStringLiteral("voice/captures"))) {
        setError(QStringLiteral("Cannot create local voice capture directory."));
        return false;
    }
    m_recordingPath = dir.filePath(QStringLiteral("voice/captures/voice-capture-%1.wav")
        .arg(QDateTime::currentDateTimeUtc().toString(QStringLiteral("yyyyMMddTHHmmsszzzZ"))));
    m_recordFile = new QFile(m_recordingPath, this);
    if (!m_recordFile->open(QIODevice::WriteOnly)) {
        m_recordFile->deleteLater();
        m_recordFile = nullptr;
        m_recordingPath.clear();
        setError(QStringLiteral("Cannot open local microphone capture file."));
        emit recordingChanged();
        return false;
    }
    m_recordFile->write(QByteArray(44, '\0'));
    m_recordingFormat = format;
    m_recordingLanguage = locale;
    m_audioSource = new QAudioSource(device, format, this);
    m_audioSource->start(m_recordFile);
    m_recording = true;
    m_state.insert(QStringLiteral("activity"), QVariantMap{
        {QStringLiteral("state"), QStringLiteral("RECORDING")},
        {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
        {QStringLiteral("actor"), QStringLiteral("user")},
        {QStringLiteral("voice_profile_id"), QString()},
        {QStringLiteral("job_id"), QString()},
        {QStringLiteral("visible"), true}
    });
    save();
    setOperation(QStringLiteral("Local microphone capture started (16 kHz mono Int16 WAV)."));
    emit recordingChanged();
    return true;
}

QVariantMap VoiceWorkspaceService::stopMicrophoneCapture(const QString &transcript)
{
    if (!m_recording || !m_audioSource || !m_recordFile) {
        setError(QStringLiteral("No microphone capture is active."));
        return {};
    }
    m_audioSource->stop();
    m_recordFile->flush();
    const auto dataBytes = qMax<qint64>(0, m_recordFile->size() - 44);
    const bool headerOk = writeWavHeader(*m_recordFile, m_recordingFormat, dataBytes);
    m_recordFile->flush();
    m_recordFile->close();

    const auto sourcePath = m_recordingPath;
    const auto locale = m_recordingLanguage;
    m_audioSource->deleteLater();
    m_recordFile->deleteLater();
    m_audioSource = nullptr;
    m_recordFile = nullptr;
    m_recording = false;
    m_recordingLanguage.clear();
    emit recordingChanged();

    if (!headerOk) {
        QFile::remove(sourcePath);
        m_recordingPath.clear();
        setError(QStringLiteral("Failed to finalize WAV capture header; incomplete capture removed."));
        return {};
    }

    auto row = createCapture(locale, sourcePath, transcript);
    if (!row.isEmpty()) {
        row.insert(QStringLiteral("audio_format"), QVariantMap{
            {QStringLiteral("container"), QStringLiteral("WAV")},
            {QStringLiteral("sample_rate_hz"), m_recordingFormat.sampleRate()},
            {QStringLiteral("channels"), m_recordingFormat.channelCount()},
            {QStringLiteral("sample_format"), QStringLiteral("PCM_S16LE")}
        });
        auto capturesMap = objectBucket(m_state, QStringLiteral("captures"));
        capturesMap.insert(row.value(QStringLiteral("capture_id")).toString(), row);
        m_state.insert(QStringLiteral("captures"), capturesMap);
        m_state.insert(QStringLiteral("activity"), QVariantMap{
            {QStringLiteral("state"), QStringLiteral("IDLE")},
            {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
            {QStringLiteral("actor"), QStringLiteral("user")},
            {QStringLiteral("voice_profile_id"), QString()},
            {QStringLiteral("job_id"), QString()},
            {QStringLiteral("visible"), false}
        });
        save();
        setOperation(QStringLiteral("Local microphone capture finalized and added to Capture Inbox."));
    }
    m_recordingPath.clear();
    emit recordingChanged();
    return row;
}

QVariantMap VoiceWorkspaceService::stageTranscription(const QString &captureId,
                                                        const QString &language,
                                                        bool refine)
{
    auto capturesMap = objectBucket(m_state, QStringLiteral("captures"));
    auto capture = capturesMap.value(clean(captureId)).toMap();
    if (capture.isEmpty()) {
        setError(QStringLiteral("Unknown capture."));
        return {};
    }
    const auto locale = clean(language);
    if (locale.isEmpty()) {
        setError(QStringLiteral("Transcription language is required."));
        return {};
    }
    const auto requestId = makeId(QStringLiteral("stt-request"));
    capture.insert(QStringLiteral("transcription_request"), QVariantMap{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-transcription-stage.v1")},
        {QStringLiteral("request_id"), requestId},
        {QStringLiteral("action_id"), QStringLiteral("voice.transcribe")},
        {QStringLiteral("capture_id"), clean(captureId)},
        {QStringLiteral("language"), locale},
        {QStringLiteral("refine"), refine},
        {QStringLiteral("provider_profile"), QStringLiteral("FA3-STT-MEDIA-001")},
        {QStringLiteral("provider_id"), QStringLiteral("FA3-PROVIDER-WHISPER-001")},
        {QStringLiteral("model_router_authority"), QStringLiteral("FA3-AUTH-MODEL-ROUTER-001")},
        {QStringLiteral("uaf_authority"), QStringLiteral("FA3-UNIFIED-ACTION-FABRIC-001")},
        {QStringLiteral("execution_requested"), false}
    });
    capture.insert(QStringLiteral("status"), QStringLiteral("TRANSCRIPTION_STAGED_UAF"));
    capture.insert(QStringLiteral("updated_at"), nowUtc());
    capturesMap.insert(clean(captureId), capture);
    m_state.insert(QStringLiteral("captures"), capturesMap);
    m_state.insert(QStringLiteral("activity"), QVariantMap{
        {QStringLiteral("state"), QStringLiteral("TRANSCRIBING")},
        {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
        {QStringLiteral("actor"), QStringLiteral("user")},
        {QStringLiteral("voice_profile_id"), QString()},
        {QStringLiteral("job_id"), requestId},
        {QStringLiteral("visible"), true}
    });
    if (!save()) return {};
    setOperation(QStringLiteral("Transcription staged for UAF. Provider execution requires admitted Whisper current-host runtime."));
    return capture;
}

QVariantMap VoiceWorkspaceService::authorizeDispatch(const QString &jobId,
                                                      const QString &uafExecutionRef,
                                                      const QString &resourceAdmissionRef)
{
    auto jobsMap = objectBucket(m_state, QStringLiteral("jobs"));
    auto job = jobsMap.value(clean(jobId)).toMap();
    if (job.isEmpty()) {
        setError(QStringLiteral("Unknown voice job."));
        return {};
    }
    if (job.value(QStringLiteral("status")).toString() != QStringLiteral("ROUTE_READY")
        || job.value(QStringLiteral("provider_decision")).toMap().isEmpty()) {
        setError(QStringLiteral("Dispatch requires ROUTE_READY job and provider decision."));
        return {};
    }
    const auto uafRef = clean(uafExecutionRef);
    const auto resourceRef = clean(resourceAdmissionRef);
    if (uafRef.isEmpty() || resourceRef.isEmpty()) {
        setError(QStringLiteral("UAF execution and resource admission references are required."));
        return {};
    }
    const auto request = job.value(QStringLiteral("request")).toMap();
    QVariantMap temporal{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-temporal-dispatch.v1")},
        {QStringLiteral("workflow_type"), QStringLiteral("fa3.voice.generate")},
        {QStringLiteral("workflow_id"), QStringLiteral("voice-generation::") + clean(jobId)},
        {QStringLiteral("idempotency_key"), request.value(QStringLiteral("request_id"))},
        {QStringLiteral("job_id"), clean(jobId)},
        {QStringLiteral("uaf_execution_ref"), uafRef},
        {QStringLiteral("resource_admission_ref"), resourceRef},
        {QStringLiteral("provider_decision"), job.value(QStringLiteral("provider_decision"))},
        {QStringLiteral("execution_authority"), QStringLiteral("FA3-UNIFIED-ACTION-FABRIC-001")},
        {QStringLiteral("workflow_authority"), QStringLiteral("Temporal")}
    };
    job.insert(QStringLiteral("status"), QStringLiteral("DISPATCHED"));
    job.insert(QStringLiteral("execution_requested"), true);
    job.insert(QStringLiteral("runtime_execution_allowed"), true);
    job.insert(QStringLiteral("uaf_execution_ref"), uafRef);
    job.insert(QStringLiteral("resource_admission_ref"), resourceRef);
    job.insert(QStringLiteral("temporal_dispatch"), temporal);
    job.insert(QStringLiteral("updated_at"), nowUtc());
    jobsMap.insert(clean(jobId), job);
    m_state.insert(QStringLiteral("jobs"), jobsMap);
    m_state.insert(QStringLiteral("activity"), QVariantMap{
        {QStringLiteral("state"), QStringLiteral("GENERATING")},
        {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
        {QStringLiteral("actor"), QString()},
        {QStringLiteral("voice_profile_id"), request.value(QStringLiteral("voice_identity_ref"))},
        {QStringLiteral("job_id"), clean(jobId)},
        {QStringLiteral("visible"), true}
    });
    if (!save()) return {};
    setOperation(QStringLiteral("Voice job dispatched through UAF/resource receipt into Temporal workflow handoff."));
    return job;
}

QVariantMap VoiceWorkspaceService::createCapture(const QString &language,
                                                  const QString &sourceRef,
                                                  const QString &transcript)
{
    const auto locale = clean(language);
    const auto source = clean(sourceRef);
    if (locale.isEmpty() || source.isEmpty()) {
        setError(QStringLiteral("Capture language and source reference are required."));
        return {};
    }
    const auto id = makeId(QStringLiteral("capture"));
    QVariantMap provenance{
        {QStringLiteral("local_first"), true},
        {QStringLiteral("network_egress_authorized"), false}
    };
    QVariantMap row{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-capture-record.v1")},
        {QStringLiteral("capture_id"), id},
        {QStringLiteral("language"), locale},
        {QStringLiteral("source_ref"), source},
        {QStringLiteral("raw_transcript"), transcript},
        {QStringLiteral("refined_transcript"), QString()},
        {QStringLiteral("created_at"), nowUtc()},
        {QStringLiteral("status"), transcript.isEmpty() ? QStringLiteral("CAPTURED") : QStringLiteral("TRANSCRIBED")},
        {QStringLiteral("provenance"), provenance}
    };
    auto captures = objectBucket(m_state, QStringLiteral("captures"));
    captures.insert(id, row);
    m_state.insert(QStringLiteral("captures"), captures);
    if (!save()) return {};
    setOperation(QStringLiteral("Capture added to local Voice workspace."));
    return row;
}

QVariantMap VoiceWorkspaceService::admittedRoute(const QString &language, const QString &mode) const
{
    if (language != QStringLiteral("hu-HU")) return {};
    QFile file(QDir(m_repoRoot).filePath(QStringLiteral("canonical/FA3-VOICE-PROVIDER-ADMISSION-001.json")));
    if (!file.open(QIODevice::ReadOnly)) return {};
    QJsonParseError error;
    const auto doc = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !doc.isObject()) return {};
    const auto root = doc.object();
    const auto providers = root.value(QStringLiteral("providers")).toObject();
    QStringList candidates;
    if (mode == QStringLiteral("voice_clone") || mode == QStringLiteral("zero_shot"))
        candidates = {QStringLiteral("FA3-PROVIDER-XTTS-001")};
    else
        candidates = {QStringLiteral("FA3-PROVIDER-XTTS-001"), QStringLiteral("FA3-PROVIDER-PIPER-001")};

    for (const auto &providerId : candidates) {
        const auto row = providers.value(providerId).toObject();
        const auto status = row.value(QStringLiteral("production_status")).toString();
        if (status == QStringLiteral("PRODUCTION_ADMITTED") || status == QStringLiteral("CURRENT_HOST_PRODUCTION_ADMITTED")) {
            return {
                {QStringLiteral("schema"), QStringLiteral("fa3.voice-provider-decision-receipt.v1")},
                {QStringLiteral("selected_provider_id"), providerId},
                {QStringLiteral("selected_model_id"), QStringLiteral("RESOLVED_BY_MODEL_ROUTER_RUNTIME")},
                {QStringLiteral("language_status"), QStringLiteral("PRODUCTION_ADMITTED_LANGUAGE_MATCH")},
                {QStringLiteral("license_status"), QStringLiteral("REQUIRES_EXECUTION_TIME_ADMISSION")},
                {QStringLiteral("resource_admission_ref"), QStringLiteral("REQUIRED_AT_DISPATCH")},
                {QStringLiteral("fallback_chain"), candidates},
                {QStringLiteral("decision_reason"), QStringLiteral("CANONICAL_VOICE_POLICY_CANDIDATE_FILTER")},
                {QStringLiteral("silent_fallback"), false}
            };
        }
    }
    return {};
}

QVariantMap VoiceWorkspaceService::stageGeneration(const QString &text,
                                                    const QString &voiceProfileId,
                                                    const QString &language,
                                                    const QString &style,
                                                    const QString &durationMode,
                                                    int targetDurationMs,
                                                    bool generateCaptions,
                                                    bool duckBackgroundMusic)
{
    const auto script = clean(text);
    const auto profileId = clean(voiceProfileId);
    const auto locale = clean(language);
    if (script.isEmpty() || profileId.isEmpty() || locale.isEmpty()) {
        setError(QStringLiteral("Script, Voice Profile and language are required."));
        return {};
    }
    if (findObject(QStringLiteral("voice_profiles"), QStringLiteral("voice_profile_id"), profileId).isEmpty()) {
        setError(QStringLiteral("Selected Voice Profile does not exist."));
        return {};
    }

    const auto requestId = makeId(QStringLiteral("voice-request"));
    QVariantMap request{
        {QStringLiteral("request_id"), requestId},
        {QStringLiteral("text"), script},
        {QStringLiteral("language"), locale},
        {QStringLiteral("mode"), QStringLiteral("plain")},
        {QStringLiteral("voice_identity_ref"), profileId},
        {QStringLiteral("execution_mode"), QStringLiteral("OFFLINE_LOCAL")},
        {QStringLiteral("output_intent"), QStringLiteral("MEDIA_MEZZANINE")},
        {QStringLiteral("style_intent"), clean(style)},
        {QStringLiteral("silent_fallback"), false}
    };
    const auto decision = admittedRoute(locale, QStringLiteral("plain"));
    const bool ready = !decision.isEmpty();
    const auto jobId = makeId(QStringLiteral("voice-job"));
    QVariantMap context{
        {QStringLiteral("duration_mode"), clean(durationMode)},
        {QStringLiteral("target_duration_ms"), qMax(0, targetDurationMs)},
        {QStringLiteral("generate_captions"), generateCaptions},
        {QStringLiteral("duck_background_music"), duckBackgroundMusic}
    };
    QVariantMap bindings{
        {QStringLiteral("voice"), QStringLiteral("FA3-VOICE-001")},
        {QStringLiteral("model_router"), QStringLiteral("FA3-AUTH-MODEL-ROUTER-001")},
        {QStringLiteral("resource"), QStringLiteral("FA3-AUTH-HOST-RESOURCE-BROKER-001")},
        {QStringLiteral("uaf"), QStringLiteral("FA3-UNIFIED-ACTION-FABRIC-001")},
        {QStringLiteral("workflow"), QStringLiteral("Temporal")}
    };
    QVariantMap row{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-generation-job.v1")},
        {QStringLiteral("job_id"), jobId},
        {QStringLiteral("request"), request},
        {QStringLiteral("quickclip_context"), context},
        {QStringLiteral("status"), ready ? QStringLiteral("ROUTE_READY") : QStringLiteral("BLOCKED_NOT_ADMITTED")},
        {QStringLiteral("route_state"), ready ? QStringLiteral("ROUTE_READY") : QStringLiteral("BLOCKED_NOT_ADMITTED")},
        {QStringLiteral("provider_decision"), decision},
        {QStringLiteral("created_at"), nowUtc()},
        {QStringLiteral("updated_at"), nowUtc()},
        {QStringLiteral("execution_requested"), false},
        {QStringLiteral("runtime_execution_allowed"), ready},
        {QStringLiteral("authority_bindings"), bindings}
    };
    auto jobsMap = objectBucket(m_state, QStringLiteral("jobs"));
    jobsMap.insert(jobId, row);
    m_state.insert(QStringLiteral("jobs"), jobsMap);
    m_state.insert(QStringLiteral("activity"), QVariantMap{
        {QStringLiteral("state"), ready ? QStringLiteral("PAUSED") : QStringLiteral("BLOCKED")},
        {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
        {QStringLiteral("actor"), QString()},
        {QStringLiteral("voice_profile_id"), profileId},
        {QStringLiteral("job_id"), jobId},
        {QStringLiteral("visible"), !ready}
    });
    if (!save()) return {};
    setOperation(ready
        ? QStringLiteral("Voice job staged; UAF/runtime dispatch still requires fresh execution checks.")
        : QStringLiteral("Voice job staged but blocked: no production-admitted provider route."));
    return row;
}

QVariantMap VoiceWorkspaceService::fitToClip(int targetDurationMs, int generatedDurationMs) const
{
    if (targetDurationMs <= 0 || generatedDurationMs <= 0) return {};
    const double rate = double(generatedDurationMs) / double(targetDurationMs);
    QVariantList options;
    if (rate >= 0.85 && rate <= 1.15) {
        options.append(QVariantMap{
            {QStringLiteral("action"), QStringLiteral("BOUNDED_RATE_ADJUSTMENT")},
            {QStringLiteral("speech_rate"), rate},
            {QStringLiteral("requires_text_change"), false},
            {QStringLiteral("approval_required"), false}
        });
    }
    options.append(QVariantMap{
        {QStringLiteral("action"), QStringLiteral("SCRIPT_SHORTENING_PROPOSAL")},
        {QStringLiteral("requires_text_change"), true},
        {QStringLiteral("approval_required"), true},
        {QStringLiteral("silent_apply"), false}
    });
    options.append(QVariantMap{
        {QStringLiteral("action"), QStringLiteral("EXTEND_VIDEO")},
        {QStringLiteral("target_duration_ms"), generatedDurationMs},
        {QStringLiteral("approval_required"), true}
    });
    options.append(QVariantMap{
        {QStringLiteral("action"), QStringLiteral("KEEP_ORIGINAL_TIMING")},
        {QStringLiteral("approval_required"), false}
    });
    return {
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-fit-to-clip-plan.v1")},
        {QStringLiteral("target_duration_ms"), targetDurationMs},
        {QStringLiteral("generated_duration_ms"), generatedDurationMs},
        {QStringLiteral("measured_rate_ratio"), rate},
        {QStringLiteral("options"), options},
        {QStringLiteral("silent_text_rewrite"), false},
        {QStringLiteral("status"), QStringLiteral("READY")}
    };
}

QVariantMap VoiceWorkspaceService::stageQuickDub(const QString &sourceLanguage,
                                                  const QString &targetLanguage,
                                                  const QVariantList &speakerMappings,
                                                  bool translationEnabled)
{
    if (clean(sourceLanguage).isEmpty() || clean(targetLanguage).isEmpty() || speakerMappings.isEmpty()) {
        setError(QStringLiteral("Quick Dub requires source/target language and speaker mappings."));
        return {};
    }
    QVariantList normalized;
    for (const auto &value : speakerMappings) {
        const auto row = value.toMap();
        const auto speaker = clean(row.value(QStringLiteral("speaker")).toString());
        const auto profileId = clean(row.value(QStringLiteral("voice_profile_id")).toString());
        if (speaker.isEmpty() || profileId.isEmpty()
            || findObject(QStringLiteral("voice_profiles"), QStringLiteral("voice_profile_id"), profileId).isEmpty()) {
            setError(QStringLiteral("Quick Dub speaker mapping references an unknown Voice Profile."));
            return {};
        }
        normalized.append(QVariantMap{
            {QStringLiteral("speaker"), speaker},
            {QStringLiteral("voice_profile_id"), profileId}
        });
    }
    const auto planId = makeId(QStringLiteral("quick-dub"));
    QVariantList stages{
        QStringLiteral("STT"), QStringLiteral("SPEAKER_SEGMENTATION"),
        translationEnabled ? QStringLiteral("OPTIONAL_TRANSLATION") : QStringLiteral("TRANSLATION_SKIPPED"),
        QStringLiteral("VOICE_PROFILE_MAPPING"), QStringLiteral("TTS"),
        QStringLiteral("ALIGNMENT"), QStringLiteral("EDITABLE_MIX")
    };
    QVariantMap plan{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-quick-dub-plan.v1")},
        {QStringLiteral("plan_id"), planId},
        {QStringLiteral("source_language"), clean(sourceLanguage)},
        {QStringLiteral("target_language"), clean(targetLanguage)},
        {QStringLiteral("speaker_mappings"), normalized},
        {QStringLiteral("translation_enabled"), translationEnabled},
        {QStringLiteral("stages"), stages},
        {QStringLiteral("status"), QStringLiteral("PLAN_READY")},
        {QStringLiteral("created_at"), nowUtc()}
    };
    auto plans = objectBucket(m_state, QStringLiteral("quick_dub_plans"));
    plans.insert(planId, plan);
    m_state.insert(QStringLiteral("quick_dub_plans"), plans);
    if (!save()) return {};
    setOperation(QStringLiteral("Quick Dub plan staged; STT/translation/TTS execution remains UAF/provider gated."));
    return plan;
}

QVariantMap VoiceWorkspaceService::acceptProviderResult(const QString &jobId, const QVariantMap &result)
{
    auto jobsMap = objectBucket(m_state, QStringLiteral("jobs"));
    auto job = jobsMap.value(jobId).toMap();
    if (job.isEmpty()) {
        setError(QStringLiteral("Unknown voice job."));
        return {};
    }
    const auto state = job.value(QStringLiteral("status")).toString();
    if (state != QStringLiteral("DISPATCHED") && state != QStringLiteral("RUNNING")) {
        setError(QStringLiteral("Voice job must be DISPATCHED/RUNNING before accepting provider result."));
        return {};
    }
    const QStringList required{
        QStringLiteral("provider_id"), QStringLiteral("model_id"), QStringLiteral("model_revision"),
        QStringLiteral("audio_path"), QStringLiteral("audio_sha256"), QStringLiteral("sample_rate_hz"),
        QStringLiteral("channels"), QStringLiteral("voice_identity_ref"), QStringLiteral("language"),
        QStringLiteral("synthetic_disclosure"), QStringLiteral("license_and_rights_ref"),
        QStringLiteral("execution_evidence")
    };
    for (const auto &key : required) {
        if (!result.contains(key) || result.value(key).toString().isEmpty()) {
            if (key == QStringLiteral("sample_rate_hz") || key == QStringLiteral("channels")) {
                if (result.value(key).toInt() > 0) continue;
            }
            setError(QStringLiteral("Provider result missing required field: ") + key);
            return {};
        }
    }
    const auto decision = job.value(QStringLiteral("provider_decision")).toMap();
    if (!decision.value(QStringLiteral("selected_provider_id")).toString().isEmpty()
        && decision.value(QStringLiteral("selected_provider_id")).toString() != result.value(QStringLiteral("provider_id")).toString()) {
        setError(QStringLiteral("Provider result does not match routing decision."));
        return {};
    }
    const auto request = job.value(QStringLiteral("request")).toMap();
    if (request.value(QStringLiteral("voice_identity_ref")).toString()
        != result.value(QStringLiteral("voice_identity_ref")).toString()) {
        setError(QStringLiteral("Provider result voice identity mismatch."));
        return {};
    }
    job.insert(QStringLiteral("result"), result);
    job.insert(QStringLiteral("status"), QStringLiteral("COMPLETED"));
    job.insert(QStringLiteral("updated_at"), nowUtc());
    jobsMap.insert(jobId, job);
    m_state.insert(QStringLiteral("jobs"), jobsMap);
    m_state.insert(QStringLiteral("activity"), QVariantMap{
        {QStringLiteral("state"), QStringLiteral("IDLE")},
        {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
        {QStringLiteral("actor"), QString()},
        {QStringLiteral("voice_profile_id"), request.value(QStringLiteral("voice_identity_ref"))},
        {QStringLiteral("job_id"), jobId},
        {QStringLiteral("visible"), false}
    });
    if (!save()) return {};
    setOperation(QStringLiteral("Provider result accepted with route/identity binding."));
    return job;
}

QVariantMap VoiceWorkspaceService::stageTimelineHandoff(const QString &jobId,
                                                         const QString &clipId,
                                                         const QString &captionAlignmentRef,
                                                         bool musicDucking)
{
    const auto job = findObject(QStringLiteral("jobs"), QStringLiteral("job_id"), jobId);
    const auto result = job.value(QStringLiteral("result")).toMap();
    if (job.value(QStringLiteral("status")).toString() != QStringLiteral("COMPLETED") || result.isEmpty()) {
        setError(QStringLiteral("Timeline handoff requires a completed voice job."));
        return {};
    }
    if (clean(clipId).isEmpty()) {
        setError(QStringLiteral("Timeline handoff requires clip_id."));
        return {};
    }
    const auto id = makeId(QStringLiteral("voice-handoff"));
    QVariantMap tracks{
        {QStringLiteral("voice"), QVariantMap{
            {QStringLiteral("asset_ref"), result.value(QStringLiteral("audio_path"))},
            {QStringLiteral("editable"), true}
        }},
        {QStringLiteral("captions"), QVariantMap{
            {QStringLiteral("alignment_ref"), clean(captionAlignmentRef)},
            {QStringLiteral("editable"), true}
        }},
        {QStringLiteral("music_ducking"), QVariantMap{
            {QStringLiteral("enabled"), musicDucking},
            {QStringLiteral("editable"), true}
        }}
    };
    QVariantMap row{
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-timeline-handoff.v1")},
        {QStringLiteral("handoff_id"), id},
        {QStringLiteral("job_id"), jobId},
        {QStringLiteral("clip_id"), clean(clipId)},
        {QStringLiteral("audio_asset_ref"), result.value(QStringLiteral("audio_path"))},
        {QStringLiteral("tracks"), tracks},
        {QStringLiteral("editable"), true},
        {QStringLiteral("host_mutation_authorized"), false},
        {QStringLiteral("created_at"), nowUtc()}
    };
    auto handoffsMap = objectBucket(m_state, QStringLiteral("handoffs"));
    handoffsMap.insert(id, row);
    m_state.insert(QStringLiteral("handoffs"), handoffsMap);
    if (!save()) return {};
    setOperation(QStringLiteral("Editable timeline handoff staged; host mutation still requires host/UAF authorization."));
    return row;
}

QVariantMap VoiceWorkspaceService::cancelJob(const QString &jobId, const QString &reason)
{
    auto jobsMap = objectBucket(m_state, QStringLiteral("jobs"));
    auto job = jobsMap.value(jobId).toMap();
    if (job.isEmpty()) {
        setError(QStringLiteral("Unknown voice job."));
        return {};
    }
    const auto state = job.value(QStringLiteral("status")).toString();
    if (state != QStringLiteral("COMPLETED") && state != QStringLiteral("FAILED") && state != QStringLiteral("CANCELLED")) {
        job.insert(QStringLiteral("status"), QStringLiteral("CANCELLED"));
        job.insert(QStringLiteral("cancel_reason"), clean(reason));
        job.insert(QStringLiteral("updated_at"), nowUtc());
        jobsMap.insert(jobId, job);
        m_state.insert(QStringLiteral("jobs"), jobsMap);
        m_state.insert(QStringLiteral("activity"), QVariantMap{
            {QStringLiteral("state"), QStringLiteral("IDLE")},
            {QStringLiteral("application"), QStringLiteral("fa3.voice-studio")},
            {QStringLiteral("actor"), QString()},
            {QStringLiteral("voice_profile_id"), QString()},
            {QStringLiteral("job_id"), jobId},
            {QStringLiteral("visible"), false}
        });
        save();
    }
    setOperation(QStringLiteral("Voice job cancellation recorded."));
    return job;
}

QVariantMap VoiceWorkspaceService::status(const QString &jobId) const
{
    return {
        {QStringLiteral("schema"), QStringLiteral("fa3.voice-workspace-status.v1")},
        {QStringLiteral("status"), QStringLiteral("READY")},
        {QStringLiteral("activity"), activity()},
        {QStringLiteral("job"), jobId.trimmed().isEmpty() ? QVariantMap{} : findObject(QStringLiteral("jobs"), QStringLiteral("job_id"), jobId)},
        {QStringLiteral("profile_count"), voiceProfiles().size()},
        {QStringLiteral("capture_count"), captures().size()},
        {QStringLiteral("job_count"), jobs().size()},
        {QStringLiteral("handoff_count"), handoffs().size()}
    };
}
