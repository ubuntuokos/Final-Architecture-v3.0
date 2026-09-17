#pragma once

#include <QObject>
#include <QProcess>
#include <QVariantMap>

class LanguageInterpreterService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool active READ active NOTIFY runtimeChanged)
    Q_PROPERTY(bool paused READ paused NOTIFY runtimeChanged)
    Q_PROPERTY(QString state READ state NOTIFY runtimeChanged)
    Q_PROPERTY(QString detail READ detail NOTIFY runtimeChanged)
    Q_PROPERTY(QString sessionId READ sessionId NOTIFY runtimeChanged)
    Q_PROPERTY(QString sourceLanguage READ sourceLanguage NOTIFY runtimeChanged)
    Q_PROPERTY(QString targetLanguage READ targetLanguage NOTIFY runtimeChanged)
    Q_PROPERTY(QString detectedLanguage READ detectedLanguage NOTIFY transcriptChanged)
    Q_PROPERTY(QString originalText READ originalText NOTIFY transcriptChanged)
    Q_PROPERTY(QString translatedText READ translatedText NOTIFY transcriptChanged)
    Q_PROPERTY(QString microphoneStatus READ microphoneStatus NOTIFY runtimeChanged)
    Q_PROPERTY(QString sttStatus READ sttStatus NOTIFY runtimeChanged)
    Q_PROPERTY(QString translationStatus READ translationStatus NOTIFY runtimeChanged)
    Q_PROPERTY(QString ttsStatus READ ttsStatus NOTIFY runtimeChanged)

public:
    explicit LanguageInterpreterService(QObject *parent = nullptr);
    ~LanguageInterpreterService() override;

    bool active() const { return m_active; }
    bool paused() const { return m_paused; }
    QString state() const { return m_state; }
    QString detail() const { return m_detail; }
    QString sessionId() const { return m_sessionId; }
    QString sourceLanguage() const { return m_sourceLanguage; }
    QString targetLanguage() const { return m_targetLanguage; }
    QString detectedLanguage() const { return m_detectedLanguage; }
    QString originalText() const { return m_originalText; }
    QString translatedText() const { return m_translatedText; }
    QString microphoneStatus() const { return m_microphoneStatus; }
    QString sttStatus() const { return m_sttStatus; }
    QString translationStatus() const { return m_translationStatus; }
    QString ttsStatus() const { return m_ttsStatus; }

    Q_INVOKABLE QVariantMap probe() const;
    Q_INVOKABLE void startLive(const QString &sourceLanguage,
                               const QString &targetLanguage,
                               const QString &dataClassification,
                               bool localFirst,
                               bool cloudRequested);
    Q_INVOKABLE void stop();
    Q_INVOKABLE void pause();
    Q_INVOKABLE void resume();
    Q_INVOKABLE void clearTranscript();

signals:
    void runtimeChanged();
    void transcriptChanged();

private slots:
    void recorderFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void recorderError(QProcess::ProcessError error);
    void sttFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void translationFinished(int exitCode, QProcess::ExitStatus exitStatus);

private:
    QString discoverRepositoryRoot() const;
    QString interpreterTempRoot() const;
    QString pythonExecutable() const;
    QString translationAdapterExecutable() const;
    bool translationAdapterAdmitted() const;
    void startCapture();
    void startStt();
    void startTranslation(const QString &sourceText, const QString &sourceLanguage);
    void continueAfterTranslation(const QString &translatedText);
    void scheduleNextCapture();
    void setBlocked(const QString &state, const QString &detail);
    void terminateProcess(QProcess *process);
    void cleanupCurrentChunk();
    QString compactProcessError(QProcess *process) const;

    QProcess *m_recorder = nullptr;
    QProcess *m_stt = nullptr;
    QProcess *m_translation = nullptr;

    bool m_active = false;
    bool m_paused = false;
    bool m_localFirst = true;
    bool m_cloudRequested = false;
    QString m_state = QStringLiteral("IDLE");
    QString m_detail = QStringLiteral("A tolmács készen áll.");
    QString m_sessionId;
    QString m_sourceLanguage = QStringLiteral("auto");
    QString m_targetLanguage = QStringLiteral("same-as-input");
    QString m_dataClassification = QStringLiteral("INTERNAL");
    QString m_detectedLanguage;
    QString m_originalText;
    QString m_translatedText;
    QString m_microphoneStatus = QStringLiteral("IDLE");
    QString m_sttStatus = QStringLiteral("READY-CHECK");
    QString m_translationStatus = QStringLiteral("ADAPTER-GATED");
    QString m_ttsStatus = QStringLiteral("ADAPTER-GATED");
    QString m_repoRoot;
    QString m_sessionDir;
    QString m_audioPath;
    QString m_sttRequestPath;
    QString m_sttResultPath;
    QString m_translationRequestPath;
    QString m_translationResultPath;
    QString m_pendingChunkText;
    QString m_pendingChunkLanguage;
    int m_chunkIndex = 0;
};
