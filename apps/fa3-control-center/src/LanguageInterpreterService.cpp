#include "LanguageInterpreterService.h"

#include <QCoreApplication>
#include <QCryptographicHash>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>
#include <QStandardPaths>
#include <QTimer>
#include <QUuid>

namespace {
constexpr int kCaptureSeconds = 4;

QString sha256File(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    QCryptographicHash hash(QCryptographicHash::Sha256);
    if (!hash.addData(&file)) return {};
    return QString::fromLatin1(hash.result().toHex());
}

bool writeJson(const QString &path, const QJsonObject &object)
{
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
    file.write(QJsonDocument(object).toJson(QJsonDocument::Indented));
    return file.commit();
}

QJsonObject readJsonObject(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) return {};
    QJsonParseError error;
    const auto document = QJsonDocument::fromJson(file.readAll(), &error);
    if (error.error != QJsonParseError::NoError || !document.isObject()) return {};
    return document.object();
}

QString normalizedLanguage(QString value)
{
    value = value.trimmed().toLower();
    return value.isEmpty() ? QStringLiteral("auto") : value;
}
}

LanguageInterpreterService::LanguageInterpreterService(QObject *parent)
    : QObject(parent),
      m_recorder(new QProcess(this)),
      m_stt(new QProcess(this)),
      m_translation(new QProcess(this)),
      m_repoRoot(discoverRepositoryRoot())
{
    m_recorder->setProcessChannelMode(QProcess::SeparateChannels);
    m_stt->setProcessChannelMode(QProcess::SeparateChannels);
    m_translation->setProcessChannelMode(QProcess::SeparateChannels);

    connect(m_recorder, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, &LanguageInterpreterService::recorderFinished);
    connect(m_recorder, &QProcess::errorOccurred,
            this, &LanguageInterpreterService::recorderError);
    connect(m_stt, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, &LanguageInterpreterService::sttFinished);
    connect(m_translation, qOverload<int, QProcess::ExitStatus>(&QProcess::finished),
            this, &LanguageInterpreterService::translationFinished);
}

LanguageInterpreterService::~LanguageInterpreterService()
{
    m_active = false;
    terminateProcess(m_recorder);
    terminateProcess(m_stt);
    terminateProcess(m_translation);
    if (!m_sessionDir.isEmpty()) QDir(m_sessionDir).removeRecursively();
}

QString LanguageInterpreterService::discoverRepositoryRoot() const
{
    const auto envRoot = qEnvironmentVariable("FA3_REPO_ROOT");
    if (!envRoot.isEmpty() && QFileInfo::exists(QDir(envRoot).filePath("canonical")))
        return QDir(envRoot).absolutePath();

    const QStringList candidates = {QDir::currentPath(), QCoreApplication::applicationDirPath()};
    for (const auto &candidate : candidates) {
        QDir dir(candidate);
        for (int depth = 0; depth < 8; ++depth) {
            if (dir.exists("canonical") && dir.exists("src") && QFileInfo::exists(dir.filePath("README.md")))
                return dir.absolutePath();
            if (!dir.cdUp()) break;
        }
    }
    return QDir::currentPath();
}

QString LanguageInterpreterService::interpreterTempRoot() const
{
    auto base = QStandardPaths::writableLocation(QStandardPaths::TempLocation);
    if (base.isEmpty()) base = QDir::tempPath();
    return QDir(base).filePath(QStringLiteral("fa3-language-interpreter"));
}

QString LanguageInterpreterService::pythonExecutable() const
{
    const auto configured = qEnvironmentVariable("FA3_WHISPER_PYTHON").trimmed();
    if (!configured.isEmpty()) {
        const QFileInfo info(configured);
        if (info.isAbsolute() && info.isExecutable()) return info.absoluteFilePath();
        const auto resolved = QStandardPaths::findExecutable(configured);
        if (!resolved.isEmpty()) return resolved;
    }
    return QStandardPaths::findExecutable(QStringLiteral("python3"));
}

QString LanguageInterpreterService::translationAdapterExecutable() const
{
    if (!translationAdapterAdmitted()) return {};
    const auto configured = qEnvironmentVariable("FA3_LANGUAGE_TRANSLATION_ADAPTER").trimmed();
    if (configured.isEmpty()) return {};
    const QFileInfo info(configured);
    if (!info.isAbsolute() || !info.isExecutable()) return {};
    return info.absoluteFilePath();
}

bool LanguageInterpreterService::translationAdapterAdmitted() const
{
    return qEnvironmentVariable("FA3_LANGUAGE_TRANSLATION_ADAPTER_ADMITTED").trimmed() == QStringLiteral("1");
}

QVariantMap LanguageInterpreterService::probe() const
{
    const auto ffmpeg = QStandardPaths::findExecutable(QStringLiteral("ffmpeg"));
    const auto python = pythonExecutable();
    const auto sttProvider = QDir(m_repoRoot).filePath(QStringLiteral("src/fa3_whisper_stt_provider.py"));
    const auto translator = translationAdapterExecutable();
    return {
        {QStringLiteral("microphoneCapture"), ffmpeg.isEmpty() ? QStringLiteral("UNAVAILABLE") : QStringLiteral("READY")},
        {QStringLiteral("captureExecutable"), ffmpeg},
        {QStringLiteral("stt"), (!python.isEmpty() && QFileInfo::exists(sttProvider)) ? QStringLiteral("PROBE-READY") : QStringLiteral("UNAVAILABLE")},
        {QStringLiteral("sttProvider"), QStringLiteral("FA3-PROVIDER-WHISPER-001")},
        {QStringLiteral("translation"), translator.isEmpty() ? QStringLiteral("ADAPTER-GATED") : QStringLiteral("ADMITTED")},
        {QStringLiteral("translationAdapter"), translator},
        {QStringLiteral("tts"), QStringLiteral("ADAPTER-GATED")},
        {QStringLiteral("repoRoot"), m_repoRoot},
        {QStringLiteral("audioRetention"), QStringLiteral("EPHEMERAL-TEMP-ONLY")},
        {QStringLiteral("egress"), QStringLiteral("FAIL-CLOSED")}
    };
}

void LanguageInterpreterService::startLive(const QString &sourceLanguage,
                                           const QString &targetLanguage,
                                           const QString &dataClassification,
                                           bool localFirst,
                                           bool cloudRequested)
{
    stop();

    m_sourceLanguage = normalizedLanguage(sourceLanguage);
    m_targetLanguage = targetLanguage.trimmed().isEmpty() ? QStringLiteral("same-as-input") : normalizedLanguage(targetLanguage);
    m_dataClassification = dataClassification.trimmed().toUpper();
    if (m_dataClassification.isEmpty()) m_dataClassification = QStringLiteral("INTERNAL");
    m_localFirst = localFirst;
    m_cloudRequested = cloudRequested;
    m_sessionId = QUuid::createUuid().toString(QUuid::WithoutBraces);
    m_chunkIndex = 0;
    m_originalText.clear();
    m_translatedText.clear();
    m_detectedLanguage.clear();
    m_microphoneStatus = QStringLiteral("STARTING");
    m_sttStatus = QStringLiteral("PROBE-READY");
    m_translationStatus = QStringLiteral("ADAPTER-GATED");
    m_ttsStatus = QStringLiteral("ADAPTER-GATED");

    QDir root(interpreterTempRoot());
    if (!root.exists() && !QDir().mkpath(root.absolutePath())) {
        setBlocked(QStringLiteral("TEMP_STORAGE_BLOCKED"), QStringLiteral("Az ideiglenes, session-szintű audio tár nem hozható létre."));
        return;
    }
    m_sessionDir = root.filePath(m_sessionId);
    if (!QDir().mkpath(m_sessionDir)) {
        setBlocked(QStringLiteral("TEMP_STORAGE_BLOCKED"), QStringLiteral("A tolmács session könyvtára nem hozható létre."));
        return;
    }

    m_active = true;
    m_paused = false;
    m_state = QStringLiteral("STARTING");
    m_detail = (m_dataClassification == QStringLiteral("SECRET") && m_cloudRequested)
        ? QStringLiteral("SECRET adat: a cloud-kérés figyelmen kívül marad, csak helyi útvonal engedhető.")
        : QStringLiteral("Élő tolmács session indul; mikrofon inicializálása.");
    emit transcriptChanged();
    emit runtimeChanged();
    startCapture();
}

void LanguageInterpreterService::stop()
{
    m_active = false;
    m_paused = false;
    terminateProcess(m_recorder);
    terminateProcess(m_stt);
    terminateProcess(m_translation);
    cleanupCurrentChunk();
    if (!m_sessionDir.isEmpty()) QDir(m_sessionDir).removeRecursively();
    m_sessionDir.clear();
    m_state = QStringLiteral("IDLE");
    m_detail = QStringLiteral("A tolmács leállítva.");
    m_microphoneStatus = QStringLiteral("IDLE");
    emit runtimeChanged();
}

void LanguageInterpreterService::pause()
{
    if (!m_active || m_paused) return;
    m_paused = true;
    terminateProcess(m_recorder);
    terminateProcess(m_stt);
    terminateProcess(m_translation);
    m_state = QStringLiteral("PAUSED");
    m_detail = QStringLiteral("A tolmácsolás szünetel; a mikrofon nincs rögzítve.");
    m_microphoneStatus = QStringLiteral("PAUSED");
    emit runtimeChanged();
}

void LanguageInterpreterService::resume()
{
    if (!m_active || !m_paused) return;
    m_paused = false;
    m_detail = QStringLiteral("Tolmácsolás folytatása.");
    emit runtimeChanged();
    startCapture();
}

void LanguageInterpreterService::clearTranscript()
{
    m_originalText.clear();
    m_translatedText.clear();
    m_detectedLanguage.clear();
    emit transcriptChanged();
}

void LanguageInterpreterService::startCapture()
{
    if (!m_active || m_paused) return;

    const auto ffmpeg = QStandardPaths::findExecutable(QStringLiteral("ffmpeg"));
    if (ffmpeg.isEmpty()) {
        m_microphoneStatus = QStringLiteral("UNAVAILABLE");
        setBlocked(QStringLiteral("MICROPHONE_CAPTURE_UNAVAILABLE"),
                   QStringLiteral("Az ffmpeg nem érhető el; az FA3 nem tud biztonságos PCM16/16 kHz mikrofon-chunkot létrehozni."));
        return;
    }
    const auto python = pythonExecutable();
    const auto sttProvider = QDir(m_repoRoot).filePath(QStringLiteral("src/fa3_whisper_stt_provider.py"));
    if (python.isEmpty() || !QFileInfo::exists(sttProvider)) {
        m_sttStatus = QStringLiteral("UNAVAILABLE");
        setBlocked(QStringLiteral("STT_UNAVAILABLE"),
                   QStringLiteral("A Python/Whisper STT provider nem érhető el a jelenlegi FA3 runtime-ban."));
        return;
    }

    cleanupCurrentChunk();
    ++m_chunkIndex;
    m_audioPath = QDir(m_sessionDir).filePath(QStringLiteral("chunk-%1.wav").arg(m_chunkIndex, 6, 10, QLatin1Char('0')));
    m_state = QStringLiteral("LISTENING");
    m_detail = QStringLiteral("Hallgatás… %1 másodperces helyi audio-chunk.").arg(kCaptureSeconds);
    m_microphoneStatus = QStringLiteral("LISTENING");
    emit runtimeChanged();

    m_recorder->setProgram(ffmpeg);
    m_recorder->setArguments({
        QStringLiteral("-nostdin"),
        QStringLiteral("-hide_banner"),
        QStringLiteral("-loglevel"), QStringLiteral("error"),
        QStringLiteral("-f"), QStringLiteral("pulse"),
        QStringLiteral("-i"), QStringLiteral("default"),
        QStringLiteral("-ac"), QStringLiteral("1"),
        QStringLiteral("-ar"), QStringLiteral("16000"),
        QStringLiteral("-c:a"), QStringLiteral("pcm_s16le"),
        QStringLiteral("-t"), QString::number(kCaptureSeconds),
        QStringLiteral("-y"), m_audioPath
    });
    m_recorder->start();
}

void LanguageInterpreterService::recorderFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    if (!m_active || m_paused) return;
    if (exitStatus != QProcess::NormalExit || exitCode != 0 || QFileInfo(m_audioPath).size() <= 44) {
        m_microphoneStatus = QStringLiteral("FAILED");
        setBlocked(QStringLiteral("MICROPHONE_CAPTURE_FAILED"),
                   QStringLiteral("A mikrofonrögzítés sikertelen: %1").arg(compactProcessError(m_recorder)));
        return;
    }
    m_microphoneStatus = QStringLiteral("READY");
    startStt();
}

void LanguageInterpreterService::recorderError(QProcess::ProcessError)
{
    if (!m_active || m_paused || m_state != QStringLiteral("LISTENING")) return;
    m_microphoneStatus = QStringLiteral("FAILED");
    setBlocked(QStringLiteral("MICROPHONE_CAPTURE_FAILED"),
               QStringLiteral("A mikrofonfolyamat nem indítható: %1").arg(m_recorder->errorString()));
}

void LanguageInterpreterService::startStt()
{
    if (!m_active || m_paused) return;
    const auto audioHash = sha256File(m_audioPath);
    if (audioHash.isEmpty()) {
        m_sttStatus = QStringLiteral("FAILED");
        setBlocked(QStringLiteral("STT_INPUT_INVALID"), QStringLiteral("Az audio chunk SHA-256 lenyomata nem képezhető."));
        return;
    }

    m_sttRequestPath = QDir(m_sessionDir).filePath(QStringLiteral("stt-request-%1.json").arg(m_chunkIndex));
    m_sttResultPath = QDir(m_sessionDir).filePath(QStringLiteral("stt-result-%1.json").arg(m_chunkIndex));
    const QJsonObject request {
        {QStringLiteral("schema"), QStringLiteral("fa3.stt-media-request.v1")},
        {QStringLiteral("audio_path"), m_audioPath},
        {QStringLiteral("audio_hash"), audioHash},
        {QStringLiteral("language"), m_sourceLanguage},
        {QStringLiteral("task"), QStringLiteral("transcribe")},
        {QStringLiteral("time_origin"), QStringLiteral("RELATIVE_ZERO")},
        {QStringLiteral("required_result_schema"), QStringLiteral("fa3.stt-media-result.v1")}
    };
    if (!writeJson(m_sttRequestPath, request)) {
        m_sttStatus = QStringLiteral("FAILED");
        setBlocked(QStringLiteral("STT_REQUEST_WRITE_FAILED"), QStringLiteral("Az STT kérés ideiglenes fájlja nem írható."));
        return;
    }

    const auto provider = QDir(m_repoRoot).filePath(QStringLiteral("src/fa3_whisper_stt_provider.py"));
    m_state = QStringLiteral("TRANSCRIBING");
    m_detail = QStringLiteral("Beszédfelismerés: FA3-PROVIDER-WHISPER-001, offline/fail-closed mód.");
    m_sttStatus = QStringLiteral("RUNNING");
    emit runtimeChanged();

    m_stt->setProgram(pythonExecutable());
    m_stt->setArguments({
        provider,
        QStringLiteral("--root"), m_repoRoot,
        QStringLiteral("transcribe"),
        QStringLiteral("--request"), m_sttRequestPath,
        QStringLiteral("--result"), m_sttResultPath,
        QStringLiteral("--model"), QStringLiteral("turbo"),
        QStringLiteral("--device"), QStringLiteral("cpu"),
        QStringLiteral("--no-word-timestamps")
    });
    m_stt->start();
}

void LanguageInterpreterService::sttFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    if (!m_active || m_paused) return;
    if (exitStatus != QProcess::NormalExit || exitCode != 0) {
        m_sttStatus = QStringLiteral("BLOCKED");
        setBlocked(QStringLiteral("STT_BLOCKED"),
                   QStringLiteral("A Whisper STT provider fail-closed állapotban leállt: %1").arg(compactProcessError(m_stt)));
        return;
    }

    const auto result = readJsonObject(m_sttResultPath);
    if (result.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.stt-media-result.v1")
        || result.value(QStringLiteral("status")).toString() != QStringLiteral("PASS")) {
        m_sttStatus = QStringLiteral("INVALID-EVIDENCE");
        setBlocked(QStringLiteral("STT_EVIDENCE_REJECTED"), QStringLiteral("Az STT eredmény nem teljesíti a typed PASS contractot."));
        return;
    }

    QStringList parts;
    const auto segments = result.value(QStringLiteral("segments")).toArray();
    for (const auto &segmentValue : segments) {
        const auto text = segmentValue.toObject().value(QStringLiteral("text")).toString().trimmed();
        if (!text.isEmpty()) parts.append(text);
    }
    const auto chunkText = parts.join(QLatin1Char(' ')).trimmed();
    if (chunkText.isEmpty()) {
        m_sttStatus = QStringLiteral("NO-SPEECH");
        m_state = QStringLiteral("LISTENING");
        m_detail = QStringLiteral("Nem észlelhető beszéd; hallgatás folytatása.");
        emit runtimeChanged();
        scheduleNextCapture();
        return;
    }

    m_detectedLanguage = normalizedLanguage(result.value(QStringLiteral("language")).toString());
    if (!m_originalText.isEmpty()) m_originalText += QLatin1Char('\n');
    m_originalText += chunkText;
    m_pendingChunkText = chunkText;
    m_pendingChunkLanguage = m_detectedLanguage;
    m_sttStatus = QStringLiteral("PASS");
    emit transcriptChanged();

    const auto target = normalizedLanguage(m_targetLanguage);
    if (target == QStringLiteral("same-as-input") || target == m_detectedLanguage
        || (target == QStringLiteral("auto") && m_sourceLanguage != QStringLiteral("auto"))) {
        m_translationStatus = QStringLiteral("BYPASS-SAME-LANGUAGE");
        continueAfterTranslation(chunkText);
        return;
    }
    startTranslation(chunkText, m_detectedLanguage);
}

void LanguageInterpreterService::startTranslation(const QString &sourceText, const QString &sourceLanguage)
{
    if (!m_active || m_paused) return;
    const auto adapter = translationAdapterExecutable();
    if (adapter.isEmpty()) {
        m_translationStatus = QStringLiteral("ADAPTER-GATED");
        m_paused = true;
        m_state = QStringLiteral("TRANSLATION_ADAPTER_REQUIRED");
        m_detail = QStringLiteral("A beszéd felismerve, de eltérő célnyelvhez nincs admitted FA3 fordítóadapter. A session fail-closed szünetel; a transcript megmarad.");
        emit runtimeChanged();
        return;
    }

    const bool externalAllowed = m_cloudRequested && m_dataClassification != QStringLiteral("SECRET");
    m_translationRequestPath = QDir(m_sessionDir).filePath(QStringLiteral("translation-request-%1.json").arg(m_chunkIndex));
    m_translationResultPath = QDir(m_sessionDir).filePath(QStringLiteral("translation-result-%1.json").arg(m_chunkIndex));
    const QJsonObject request {
        {QStringLiteral("schema"), QStringLiteral("fa3.language-translation-request.v1")},
        {QStringLiteral("request_id"), QStringLiteral("%1-%2").arg(m_sessionId).arg(m_chunkIndex)},
        {QStringLiteral("source_text"), sourceText},
        {QStringLiteral("source_language"), sourceLanguage},
        {QStringLiteral("target_language"), normalizedLanguage(m_targetLanguage)},
        {QStringLiteral("data_classification"), m_dataClassification},
        {QStringLiteral("local_first"), m_localFirst},
        {QStringLiteral("external_egress_allowed"), externalAllowed},
        {QStringLiteral("original_authoritative"), true},
        {QStringLiteral("required_result_schema"), QStringLiteral("fa3.language-translation-result.v1")}
    };
    if (!writeJson(m_translationRequestPath, request)) {
        m_translationStatus = QStringLiteral("FAILED");
        setBlocked(QStringLiteral("TRANSLATION_REQUEST_WRITE_FAILED"), QStringLiteral("A fordítási kérés ideiglenes fájlja nem írható."));
        return;
    }

    m_state = QStringLiteral("TRANSLATING");
    m_detail = QStringLiteral("Fordítás admitted Language Bridge adapteren keresztül.");
    m_translationStatus = QStringLiteral("RUNNING");
    emit runtimeChanged();

    auto env = QProcessEnvironment::systemEnvironment();
    env.insert(QStringLiteral("FA3_EGRESS_POLICY"), externalAllowed ? QStringLiteral("POLICY_GATED") : QStringLiteral("DENY_EXTERNAL"));
    env.insert(QStringLiteral("FA3_DATA_CLASSIFICATION"), m_dataClassification);
    m_translation->setProcessEnvironment(env);
    m_translation->setProgram(adapter);
    m_translation->setArguments({QStringLiteral("--request"), m_translationRequestPath,
                                 QStringLiteral("--result"), m_translationResultPath});
    m_translation->start();
}

void LanguageInterpreterService::translationFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    if (!m_active || m_paused) return;
    if (exitStatus != QProcess::NormalExit || exitCode != 0) {
        m_translationStatus = QStringLiteral("BLOCKED");
        setBlocked(QStringLiteral("TRANSLATION_BLOCKED"),
                   QStringLiteral("A fordítóadapter fail-closed állapotban leállt: %1").arg(compactProcessError(m_translation)));
        return;
    }

    const auto result = readJsonObject(m_translationResultPath);
    if (result.value(QStringLiteral("schema")).toString() != QStringLiteral("fa3.language-translation-result.v1")
        || result.value(QStringLiteral("status")).toString() != QStringLiteral("PASS")) {
        m_translationStatus = QStringLiteral("INVALID-EVIDENCE");
        setBlocked(QStringLiteral("TRANSLATION_EVIDENCE_REJECTED"), QStringLiteral("A fordítási eredmény typed PASS evidence nélkül elutasítva."));
        return;
    }
    const auto translated = result.value(QStringLiteral("translated_text")).toString().trimmed();
    if (translated.isEmpty()) {
        m_translationStatus = QStringLiteral("INVALID-EVIDENCE");
        setBlocked(QStringLiteral("TRANSLATION_EMPTY"), QStringLiteral("A fordítóadapter üres eredményt adott."));
        return;
    }

    const auto evidence = result.value(QStringLiteral("execution_evidence")).toObject();
    const auto egress = evidence.value(QStringLiteral("egress")).toString();
    const bool externalAllowed = m_cloudRequested && m_dataClassification != QStringLiteral("SECRET");
    if (!externalAllowed && egress != QStringLiteral("LOCAL_ONLY")) {
        m_translationStatus = QStringLiteral("POLICY-DENIED");
        setBlocked(QStringLiteral("TRANSLATION_EGRESS_REJECTED"), QStringLiteral("A fordítási evidence nem bizonyít LOCAL_ONLY végrehajtást, ezért az eredmény elutasítva."));
        return;
    }

    m_translationStatus = QStringLiteral("PASS");
    continueAfterTranslation(translated);
}

void LanguageInterpreterService::continueAfterTranslation(const QString &translatedText)
{
    if (!m_translatedText.isEmpty()) m_translatedText += QLatin1Char('\n');
    m_translatedText += translatedText;
    m_state = QStringLiteral("READY");
    m_detail = QStringLiteral("A chunk feldolgozva. A TTS külön admitted adapter hiányában nem indul; élő szöveges tolmácsolás folytatódik.");
    m_ttsStatus = QStringLiteral("ADAPTER-GATED");
    emit transcriptChanged();
    emit runtimeChanged();
    scheduleNextCapture();
}

void LanguageInterpreterService::scheduleNextCapture()
{
    if (!m_active || m_paused) return;
    QTimer::singleShot(180, this, [this] {
        if (m_active && !m_paused) startCapture();
    });
}

void LanguageInterpreterService::setBlocked(const QString &state, const QString &detail)
{
    m_state = state;
    m_detail = detail;
    m_paused = true;
    emit runtimeChanged();
}

void LanguageInterpreterService::terminateProcess(QProcess *process)
{
    if (!process || process->state() == QProcess::NotRunning) return;
    process->terminate();
    if (!process->waitForFinished(500)) {
        process->kill();
        process->waitForFinished(500);
    }
}

void LanguageInterpreterService::cleanupCurrentChunk()
{
    const QStringList paths = {m_audioPath, m_sttRequestPath, m_sttResultPath,
                               m_translationRequestPath, m_translationResultPath};
    for (const auto &path : paths) {
        if (!path.isEmpty()) QFile::remove(path);
    }
    m_audioPath.clear();
    m_sttRequestPath.clear();
    m_sttResultPath.clear();
    m_translationRequestPath.clear();
    m_translationResultPath.clear();
}

QString LanguageInterpreterService::compactProcessError(QProcess *process) const
{
    if (!process) return QStringLiteral("unknown process error");
    QString detail = QString::fromUtf8(process->readAllStandardError()).trimmed();
    if (detail.isEmpty()) detail = process->errorString().trimmed();
    detail.replace(QLatin1Char('\n'), QLatin1Char(' '));
    if (detail.size() > 360) detail = detail.left(360) + QStringLiteral("…");
    return detail.isEmpty() ? QStringLiteral("nincs további diagnosztika") : detail;
}
