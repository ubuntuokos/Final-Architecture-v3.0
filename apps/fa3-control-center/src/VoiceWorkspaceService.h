#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class VoiceWorkspaceService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QVariantList voiceProfiles READ voiceProfiles NOTIFY stateChanged)
    Q_PROPERTY(QVariantList jobs READ jobs NOTIFY stateChanged)
    Q_PROPERTY(QVariantList captures READ captures NOTIFY stateChanged)
    Q_PROPERTY(QVariantList handoffs READ handoffs NOTIFY stateChanged)
    Q_PROPERTY(QVariantMap activity READ activity NOTIFY stateChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
    Q_PROPERTY(QString lastOperation READ lastOperation NOTIFY lastOperationChanged)

public:
    explicit VoiceWorkspaceService(const QString &repoRoot, QObject *parent = nullptr);

    QVariantList voiceProfiles() const;
    QVariantList jobs() const;
    QVariantList captures() const;
    QVariantList handoffs() const;
    QVariantMap activity() const;
    QString lastError() const { return m_lastError; }
    QString lastOperation() const { return m_lastOperation; }

    Q_INVOKABLE void refresh();
    Q_INVOKABLE QVariantMap upsertVoiceProfile(const QString &voiceProfileId,
                                                const QString &name,
                                                const QString &language,
                                                const QString &identityKind,
                                                const QString &consentStatus,
                                                const QString &consentProofRef);
    Q_INVOKABLE QVariantMap createCapture(const QString &language,
                                          const QString &sourceRef,
                                          const QString &transcript = QString());
    Q_INVOKABLE QVariantMap stageGeneration(const QString &text,
                                            const QString &voiceProfileId,
                                            const QString &language,
                                            const QString &style,
                                            const QString &durationMode,
                                            int targetDurationMs,
                                            bool generateCaptions,
                                            bool duckBackgroundMusic);
    Q_INVOKABLE QVariantMap fitToClip(int targetDurationMs, int generatedDurationMs) const;
    Q_INVOKABLE QVariantMap stageQuickDub(const QString &sourceLanguage,
                                          const QString &targetLanguage,
                                          const QVariantList &speakerMappings,
                                          bool translationEnabled);
    Q_INVOKABLE QVariantMap acceptProviderResult(const QString &jobId, const QVariantMap &result);
    Q_INVOKABLE QVariantMap stageTimelineHandoff(const QString &jobId,
                                                 const QString &clipId,
                                                 const QString &captionAlignmentRef,
                                                 bool musicDucking);
    Q_INVOKABLE QVariantMap cancelJob(const QString &jobId, const QString &reason = QString());
    Q_INVOKABLE QVariantMap status(const QString &jobId = QString()) const;

signals:
    void stateChanged();
    void lastErrorChanged();
    void lastOperationChanged();

private:
    void load();
    bool save();
    QVariantMap baseState() const;
    QVariantMap admittedRoute(const QString &language, const QString &mode) const;
    QVariantMap findObject(const QString &bucket, const QString &idKey, const QString &id) const;
    QVariantList bucketValues(const QString &bucket) const;
    void setError(const QString &message);
    void setOperation(const QString &message);
    static QString makeId(const QString &prefix);

    QString m_repoRoot;
    QString m_statePath;
    QVariantMap m_state;
    QString m_lastError;
    QString m_lastOperation;
};
