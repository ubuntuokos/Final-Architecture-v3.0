#include "VoiceWorkspaceService.h"
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QStandardPaths>
#include <QUrl>
VoiceWorkspaceService::VoiceWorkspaceService(QObject *parent):QObject(parent),m_net(new QNetworkAccessManager(this)){}
QByteArray VoiceWorkspaceService::token() const {
 QString p=QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation)+"/fa3/voice-studio.token";
 QFile f(p); if(!f.open(QIODevice::ReadOnly)) return {}; return f.readAll().trimmed();
}
void VoiceWorkspaceService::error(const QString &m){m_lastError=m;m_state="UNREACHABLE_OR_DENIED";emit lastErrorChanged();emit stateChanged();}
void VoiceWorkspaceService::getJson(const QString &path,const std::function<void(const QVariantMap&)> &ok){
 QNetworkRequest r(QUrl("http://127.0.0.1:18796"+path)); auto t=token(); if(!t.isEmpty())r.setRawHeader("Authorization","Bearer "+t); r.setRawHeader("Accept","application/json");
 auto *q=m_net->get(r); connect(q,&QNetworkReply::finished,this,[this,q,ok](){auto raw=q->readAll();QJsonParseError e;auto d=QJsonDocument::fromJson(raw,&e);if(q->error()!=QNetworkReply::NoError||e.error!=QJsonParseError::NoError||!d.isObject())error(q->errorString());else ok(d.object().toVariantMap());q->deleteLater();});
}
void VoiceWorkspaceService::postJson(const QString &path,const QVariantMap &payload,const std::function<void(const QVariantMap&)> &ok){
 QNetworkRequest r(QUrl("http://127.0.0.1:18796"+path));auto t=token();if(t.isEmpty()){error("Voice Studio session token unavailable");return;}r.setRawHeader("Authorization","Bearer "+t);r.setHeader(QNetworkRequest::ContentTypeHeader,"application/json");
 auto *q=m_net->post(r,QJsonDocument(QJsonObject::fromVariantMap(payload)).toJson(QJsonDocument::Compact));connect(q,&QNetworkReply::finished,this,[this,q,ok](){auto raw=q->readAll();QJsonParseError e;auto d=QJsonDocument::fromJson(raw,&e);if(q->error()!=QNetworkReply::NoError||e.error!=QJsonParseError::NoError||!d.isObject()){QString m=q->errorString();if(d.isObject()&&d.object().contains("error"))m=d.object().value("error").toString();error(m);}else ok(d.object().toVariantMap());q->deleteLater();});
}
void VoiceWorkspaceService::refresh(){
 getJson("/healthz",[this](const QVariantMap &v){m_state=v.value("status").toString()=="ok"?"READY":"UNVERIFIED";m_lastError.clear();emit stateChanged();emit lastErrorChanged();});
 getJson("/api/profiles",[this](const QVariantMap &v){m_profiles=v.value("profiles").toList();emit profilesChanged();});
 getJson("/api/jobs",[this](const QVariantMap &v){m_jobs=v.value("jobs").toList();emit jobsChanged();});
}
void VoiceWorkspaceService::generate(const QString &text,const QString &voice,const QString &language,int targetMs,bool musicDucking,bool candidateAck){
 QVariantMap p{{"text",text},{"language",language},{"voice_identity_ref",voice},{"mode","plain"},{"license_and_rights_ref","FA3-VOICE-WORKSPACE-USER-AUTHORIZED"},{"candidate_execution_ack",candidateAck},{"music_ducking",musicDucking}};if(targetMs>0)p["target_duration_ms"]=targetMs;
 postJson("/api/generate",p,[this](const QVariantMap &v){emit generationCompleted(v);refresh();});
}
void VoiceWorkspaceService::putProfile(const QString &profileId,const QString &consentRef,bool humanVoice){postJson("/api/profiles",{{"id",profileId},{"consent_ref",consentRef},{"human_voice",humanVoice}},[this](const QVariantMap &){refresh();});}
void VoiceWorkspaceService::fitToClip(int targetMs,int actualMs){postJson("/api/fit-to-clip",{{"target_ms",targetMs},{"actual_ms",actualMs}},[this](const QVariantMap &v){emit fitCompleted(v);});}
void VoiceWorkspaceService::quickDub(const QString &sourceMedia,const QString &sourceLanguage,const QString &targetLanguage){postJson("/api/quick-dub",{{"source_media_ref",sourceMedia},{"source_language",sourceLanguage},{"target_language",targetLanguage}},[this](const QVariantMap &v){emit quickDubCompleted(v);});}
