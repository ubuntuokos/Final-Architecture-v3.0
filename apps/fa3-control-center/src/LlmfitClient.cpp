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
QByteArray decodeChunked(const QByteArray &body, bool *ok)
{
    QByteArray decoded;
    qsizetype pos = 0;
    *ok = false;

    while (pos < body.size()) {
        const auto eol = body.indexOf("\r\n", pos);
        if (eol < 0) return {};
        bool lengthOk = false;
        const auto lengthToken = body.mid(pos, eol - pos).trimmed().split(';').constFirst();
        const auto length = lengthToken.toLongLong(&lengthOk, 16);
        if (!lengthOk || length < 0) return {};
        pos = eol + 2;
        if (length == 0) {
            *ok = true;
            return decoded;
        }
        if (pos + length + 2 > body.size()) return {};
        decoded += body.mid(pos, length);
        pos += length;
        if (body.mid(pos, 2) != "\r\n") return {};
        pos += 2;
    }
    return {};
}

QByteArray httpJsonBody(const QByteArray &response, QString *error)
{
    const auto split = response.indexOf("\r\n\r\n");
    if (split < 0) {
        *error = "Invalid HTTP response from llmfit";
        return {};
    }

    const auto headers = response.left(split);
    const auto firstLineEnd = headers.indexOf("\r\n");
    const auto statusLine = headers.left(firstLineEnd < 0 ? headers.size() : firstLineEnd);
    const auto statusParts = statusLine.split(' ');
    bool statusOk = false;
    const auto status = statusParts.size() >= 2 ? statusParts.at(1).toInt(&statusOk) : 0;
    if (!statusOk || status < 200 || status >= 300) {
        *error = QString("llmfit HTTP status %1").arg(statusOk ? status : 0);
        return {};
    }

    auto body = response.mid(split + 4);
    if (headers.toLower().contains("transfer-encoding: chunked")) {
        bool chunkOk = false;
        body = decodeChunked(body, &chunkOk);
        if (!chunkOk) {
            *error = "Invalid chunked response from llmfit";
            return {};
        }
    }
    return body;
}
}

LlmfitClient::LlmfitClient(QObject *parent)
    : QObject(parent)
{
    const auto overrideSocket = qEnvironmentVariable("FA3_LLMFIT_SOCKET");
    if (!overrideSocket.isEmpty()) {
        m_socketPath = overrideSocket;
    } else {
        auto runtimeDir = QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation);
        if (runtimeDir.isEmpty()) runtimeDir = qEnvironmentVariable("XDG_RUNTIME_DIR", "/tmp");
        m_socketPath = QDir(runtimeDir).filePath("fa3/llmfit.sock");
    }
}

QString LlmfitClient::statusText() const
{
    if (m_busy) return "Refreshing";
    if (m_available) return "Connected";
    if (!m_lastError.isEmpty()) return "Unavailable";
    return "Not connected";
}

void LlmfitClient::setBusy(bool busy)
{
    if (m_busy == busy) return;
    m_busy = busy;
    emit stateChanged();
}

void LlmfitClient::setError(const QString &message)
{
    m_available = false;
    m_lastError = message;
    emit stateChanged();
}

void LlmfitClient::requestJson(const QString &path, JsonHandler handler)
{
    setBusy(true);

    auto *socket = new QLocalSocket(this);
    const auto buffer = std::make_shared<QByteArray>();
    const auto handled = std::make_shared<bool>(false);

    const auto fail = [this, socket, handled](const QString &message) {
        if (*handled) return;
        *handled = true;
        setBusy(false);
        setError(message);
        socket->abort();
        socket->deleteLater();
    };

    connect(socket, &QLocalSocket::connected, this, [socket, path] {
        QByteArray request = "GET ";
        request += path.toUtf8();
        request += " HTTP/1.1\r\nHost: localhost\r\nAccept: application/json\r\nConnection: close\r\n\r\n";
        socket->write(request);
        socket->flush();
    });

    connect(socket, &QLocalSocket::readyRead, this, [socket, buffer] {
        buffer->append(socket->readAll());
    });

    connect(socket, &QLocalSocket::errorOccurred, this,
            [socket, fail](QLocalSocket::LocalSocketError) { fail(socket->errorString()); });

    connect(socket, &QLocalSocket::disconnected, this, [this, socket, buffer, handled, handler] {
        if (*handled) return;
        buffer->append(socket->readAll());

        QString httpError;
        const auto body = httpJsonBody(*buffer, &httpError);
        if (!httpError.isEmpty()) {
            *handled = true;
            setBusy(false);
            setError(httpError);
            socket->deleteLater();
            return;
        }

        QJsonParseError parseError;
        const auto document = QJsonDocument::fromJson(body, &parseError);
        if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
            *handled = true;
            setBusy(false);
            setError(QString("Invalid llmfit JSON: %1").arg(parseError.errorString()));
            socket->deleteLater();
            return;
        }

        *handled = true;
        m_available = true;
        m_lastError.clear();
        setBusy(false);
        emit stateChanged();
        handler(document.object());
        socket->deleteLater();
    });

    socket->connectToServer(m_socketPath, QIODevice::ReadWrite);
}

void LlmfitClient::requestSystem()
{
    requestJson("/api/v1/system", [this](const QJsonObject &root) {
        m_system = root.value("system").toObject().toVariantMap();
        emit dataChanged();
        requestModels();
    });
}

void LlmfitClient::requestModels()
{
    const auto useCase = QString::fromLatin1(QUrl::toPercentEncoding(m_useCase));
    const auto runtime = QString::fromLatin1(QUrl::toPercentEncoding(m_runtime));
    const auto path = QString("/api/v1/models/top?limit=50&min_fit=marginal&sort=score&use_case=%1&runtime=%2&max_context=%3")
                          .arg(useCase, runtime)
                          .arg(m_maxContext);

    requestJson(path, [this](const QJsonObject &root) {
        QVariantList next;
        const auto rows = root.value("models").toArray();
        next.reserve(rows.size());
        for (const auto &row : rows) {
            if (row.isObject()) next.append(row.toObject().toVariantMap());
        }
        m_models = next;
        emit dataChanged();
    });
}

void LlmfitClient::refresh()
{
    requestSystem();
}

void LlmfitClient::recommendModels(const QString &useCase, const QString &runtime, int maxContext)
{
    static const QStringList allowedUseCases = {"general", "coding", "reasoning", "chat", "multimodal", "embedding"};
    static const QStringList allowedRuntimes = {"any", "llamacpp", "mlx"};

    m_useCase = allowedUseCases.contains(useCase) ? useCase : "general";
    m_runtime = allowedRuntimes.contains(runtime) ? runtime : "any";
    m_maxContext = qBound(1024, maxContext, 1048576);
    emit filtersChanged();
    requestModels();
}
