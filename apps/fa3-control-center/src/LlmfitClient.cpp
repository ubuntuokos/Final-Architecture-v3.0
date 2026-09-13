#include "LlmfitClient.h"

#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonParseError>
#include <QLocalSocket>
#include <QStandardPaths>
#include <QUrl>
#include <memory>

namespace {
QByteArray responseBody(const QByteArray &response, QString *error)
{
    const auto split=response.indexOf("\r\n\r\n");
    if(split<0){*error="Invalid llmfit HTTP response";return{};}
    const auto headers=response.left(split);
    const auto statusLine=headers.left(headers.indexOf("\r\n"));
    const auto parts=statusLine.split(' ');
    bool ok=false; const int status=parts.size()>1?parts.at(1).toInt(&ok):0;
    if(!ok||status<200||status>=300){*error=QString("llmfit HTTP status %1").arg(status);return{};}
    return response.mid(split+4);
}
}

LlmfitClient::LlmfitClient(QObject *parent):QObject(parent)
{
    auto runtime=QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
    if(runtime.isEmpty()) runtime=qEnvironmentVariable("XDG_RUNTIME_DIR","/tmp");
    m_socketPath=qEnvironmentVariable("FA3_LLMFIT_SOCKET",QDir(runtime).filePath("fa3/llmfit.sock"));
}

QString LlmfitClient::statusText() const
{
    if(m_busy) return QStringLiteral("Refreshing");
    if(m_available) return QStringLiteral("Connected");
    if(!m_lastError.isEmpty()) return QStringLiteral("Unavailable");
    return QStringLiteral("Not connected");
}

void LlmfitClient::requestJson(const QString &path, JsonHandler handler)
{
    m_busy=true; emit stateChanged();
    auto *socket=new QLocalSocket(this);
    const auto buffer=std::make_shared<QByteArray>();
    const auto handled=std::make_shared<bool>(false);
    auto fail=[this,socket,handled](const QString &message){if(*handled)return;*handled=true;m_busy=false;m_available=false;m_lastError=message;emit stateChanged();socket->abort();socket->deleteLater();};
    connect(socket,&QLocalSocket::connected,this,[socket,path]{QByteArray req="GET "+path.toUtf8()+" HTTP/1.1\r\nHost: localhost\r\nAccept: application/json\r\nConnection: close\r\n\r\n";socket->write(req);socket->flush();});
    connect(socket,&QLocalSocket::readyRead,this,[socket,buffer]{buffer->append(socket->readAll());});
    connect(socket,&QLocalSocket::errorOccurred,this,[socket,fail](QLocalSocket::LocalSocketError){fail(socket->errorString());});
    connect(socket,&QLocalSocket::disconnected,this,[this,socket,buffer,handled,handler]{
        if(*handled)return; buffer->append(socket->readAll()); QString err; const auto body=responseBody(*buffer,&err);
        if(!err.isEmpty()){*handled=true;m_busy=false;m_available=false;m_lastError=err;emit stateChanged();socket->deleteLater();return;}
        QJsonParseError pe; const auto doc=QJsonDocument::fromJson(body,&pe);
        if(pe.error!=QJsonParseError::NoError||!doc.isObject()){*handled=true;m_busy=false;m_available=false;m_lastError="Invalid llmfit JSON";emit stateChanged();socket->deleteLater();return;}
        *handled=true;m_busy=false;m_available=true;m_lastError.clear();emit stateChanged();handler(doc.object());socket->deleteLater();
    });
    socket->connectToServer(m_socketPath,QIODevice::ReadWrite);
}

void LlmfitClient::refresh()
{
    requestJson(QStringLiteral("/api/v1/system"),[this](const QJsonObject &root){m_system=root.value("system").toObject().toVariantMap();emit dataChanged();recommendModels("general","any",8192);});
}

void LlmfitClient::recommendModels(const QString &useCase,const QString &runtime,int maxContext)
{
    const auto uc=QString::fromLatin1(QUrl::toPercentEncoding(useCase));
    const auto rt=QString::fromLatin1(QUrl::toPercentEncoding(runtime));
    const auto path=QString("/api/v1/models/top?limit=50&min_fit=marginal&sort=score&use_case=%1&runtime=%2&max_context=%3").arg(uc,rt).arg(qBound(1024,maxContext,1048576));
    requestJson(path,[this](const QJsonObject &root){QVariantList next;for(const auto &v:root.value("models").toArray())if(v.isObject())next.append(v.toObject().toVariantMap());m_models=next;emit dataChanged();});
}
