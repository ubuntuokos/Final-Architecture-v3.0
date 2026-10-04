#pragma once
#include <QObject>
#include <functional>
#include <QVariantList>
#include <QVariantMap>
class QNetworkAccessManager;
class VoiceWorkspaceService final : public QObject {
 Q_OBJECT
 Q_PROPERTY(QString state READ state NOTIFY stateChanged)
 Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)
 Q_PROPERTY(QVariantList profiles READ profiles NOTIFY profilesChanged)
 Q_PROPERTY(QVariantList jobs READ jobs NOTIFY jobsChanged)
public:
 explicit VoiceWorkspaceService(QObject *parent=nullptr);
 QString state() const { return m_state; }
 QString lastError() const { return m_lastError; }
 QVariantList profiles() const { return m_profiles; }
 QVariantList jobs() const { return m_jobs; }
 Q_INVOKABLE void refresh();
 Q_INVOKABLE void generate(const QString &text,const QString &voice,const QString &language,int targetMs,bool musicDucking,bool candidateAck);
 Q_INVOKABLE void fitToClip(int targetMs,int actualMs);
 Q_INVOKABLE void putProfile(const QString &profileId,const QString &consentRef,bool humanVoice);
 Q_INVOKABLE void transcribe(const QString &audioPath,const QString &language);
 Q_INVOKABLE void planEffects(const QString &sourceAudioRef);
 Q_INVOKABLE void quickDub(const QString &sourceMedia,const QString &sourceLanguage,const QString &targetLanguage);
signals:
 void stateChanged(); void lastErrorChanged(); void profilesChanged(); void jobsChanged();
 void generationCompleted(QVariantMap result); void transcriptionCompleted(QVariantMap result); void effectsPlanCompleted(QVariantMap result); void fitCompleted(QVariantMap result); void quickDubCompleted(QVariantMap result);
private:
 void getJson(const QString &path,const std::function<void(const QVariantMap&)> &ok);
 void postJson(const QString &path,const QVariantMap &payload,const std::function<void(const QVariantMap&)> &ok);
 QByteArray token() const; void error(const QString &message);
 QNetworkAccessManager *m_net; QString m_state="UNREACHABLE"; QString m_lastError; QVariantList m_profiles; QVariantList m_jobs;
};
