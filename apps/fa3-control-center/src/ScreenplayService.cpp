#include "ScreenplayService.h"
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QProcess>
#include <QSaveFile>
#include <QTemporaryDir>

ScreenplayService::ScreenplayService(QObject *parent): QObject(parent) {}

void ScreenplayService::setError(const QString &message) {
    m_error = message.left(2000);
    emit errorChanged();
}

QString ScreenplayService::cliPath() const {
    const QString explicitPath = qEnvironmentVariable("FA3_SCREENPLAY_CLI");
    const QString appDir = QCoreApplication::applicationDirPath();
    const QStringList candidates = explicitPath.isEmpty()
        ? QStringList{appDir + "/fa3-screenplay", QDir::currentPath() + "/bin/fa3-screenplay",
                      QDir(appDir).absoluteFilePath("../../bin/fa3-screenplay")}
        : QStringList{explicitPath};
    for (const QString &candidate : candidates) {
        const QFileInfo info(candidate);
        if (info.isFile() && info.isExecutable() && !info.isSymLink())
            return info.absoluteFilePath();
    }
    return {};
}

bool ScreenplayService::saveTemp(const QString &path, const QByteArray &data) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::NewOnly)) {
        setError(QStringLiteral("Cannot write local temporary file"));
        return false;
    }
    if (file.write(data) != data.size()) {
        setError(QStringLiteral("Incomplete temporary file write"));
        return false;
    }
    file.close();
    return true;
}

bool ScreenplayService::run(const QStringList &args, const QString &resultFile, QJsonObject &result, bool acceptBlocker) {
    const QString cli = cliPath();
    if (cli.isEmpty()) {
        setError(QStringLiteral("Local FA3 screenplay executable unavailable; no automatic provider fallback"));
        return false;
    }
    QProcess process;
    process.setProgram(cli);
    process.setArguments(args);
    process.start(QIODevice::ReadOnly);
    if (!process.waitForStarted(5000)) {
        setError(QStringLiteral("Could not start the local screenplay CLI"));
        return false;
    }
    if (!process.waitForFinished(20000)) {
        process.kill();
        process.waitForFinished(3000);
        setError(QStringLiteral("Local screenplay CLI timed out; operation not committed"));
        return false;
    }
    const int code = process.exitCode();
    if (process.exitStatus() != QProcess::NormalExit ||
        (code != 0 && !(acceptBlocker && code == 3))) {
        setError(QString::fromUtf8(process.readAllStandardError()).left(1500));
        return false;
    }
    m_receipt = QString::fromUtf8(process.readAllStandardOutput()).left(4000);
    emit receiptChanged();
    QFile file(resultFile);
    if (!file.open(QIODevice::ReadOnly)) {
        setError(QStringLiteral("CLI succeeded without an expected output file"));
        return false;
    }
    QJsonParseError err;
    QJsonDocument parsed = QJsonDocument::fromJson(file.readAll(), &err);
    if (err.error != QJsonParseError::NoError || !parsed.isObject()) {
        setError(QStringLiteral("Local screenplay CLI produced invalid JSON"));
        return false;
    }
    result = parsed.object();
    setError(QString());
    return true;
}

void ScreenplayService::clearDerived() {
    m_breakdown = QJsonObject();
    m_handoff = QJsonObject();
    emit breakdownChanged();
    emit handoffChanged();
}

bool ScreenplayService::importText(const QString &text, const QString &format, const QString &profile) {
    if (text.toUtf8().size() > 5 * 1024 * 1024) {
        setError(QStringLiteral("Source exceeds 5 MiB"));
        return false;
    }
    QTemporaryDir temp;
    if (!temp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString source = temp.filePath("script-input.txt");
    const QString target = temp.filePath("script-document.json");
    if (!saveTemp(source, text.toUtf8())) return false;
    QJsonObject result;
    if (!run({"import", "--input", source, "--format", format, "--profile", profile,
              "--output", target}, target, result)) return false;
    m_document = result;
    emit documentChanged();
    clearDerived();
    return true;
}

bool ScreenplayService::importFile(const QUrl &url, const QString &format, const QString &profile) {
    if (!url.isLocalFile() || QFileInfo(url.toLocalFile()).isSymLink()) {
        setError(QStringLiteral("Only an ordinary local screenplay file may be imported"));
        return false;
    }
    QFile source(url.toLocalFile());
    if (!source.open(QIODevice::ReadOnly) || source.size() > 5 * 1024 * 1024) {
        setError(QStringLiteral("Cannot read file or exceeds 5 MiB"));
        return false;
    }
    return importText(QString::fromUtf8(source.readAll()), format, profile);
}

bool ScreenplayService::loadCanonical(const QUrl &url) {
    if (!url.isLocalFile() || QFileInfo(url.toLocalFile()).isSymLink()) {
        setError(QStringLiteral("Only an ordinary local FA3 JSON file may be loaded"));
        return false;
    }
    QFile file(url.toLocalFile());
    if (!file.open(QIODevice::ReadOnly) || file.size() > 5 * 1024 * 1024) {
        setError(QStringLiteral("Cannot read canonical document or exceeds 5 MiB"));
        return false;
    }
    QTemporaryDir temp;
    if (!temp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString path = temp.filePath("document.json");
    const QByteArray bytes = file.readAll();
    if (!saveTemp(path, bytes)) return false;
    const QString cli = cliPath();
    if (cli.isEmpty()) { setError(QStringLiteral("Local screenplay CLI unavailable")); return false; }
    QProcess proc;
    proc.start(cli, {"validate", "--input", path}, QIODevice::ReadOnly);
    if (!proc.waitForStarted(5000) || !proc.waitForFinished(20000) || proc.exitCode() != 0) {
        setError(QString::fromUtf8(proc.readAllStandardError()).left(1500));
        return false;
    }
    const QJsonDocument parsed = QJsonDocument::fromJson(bytes);
    if (!parsed.isObject()) { setError(QStringLiteral("Invalid canonical JSON")); return false; }
    m_document = parsed.object();
    emit documentChanged();
    clearDerived();
    setError(QString());
    return true;
}

bool ScreenplayService::writeCanonical(const QString &path, bool replace) {
    if (m_document.isEmpty()) { setError(QStringLiteral("No imported screenplay to save")); return false; }
    QFileInfo info(path);
    if ((info.exists() && !replace) || info.isSymLink()) {
        setError(QStringLiteral("Destination exists; explicitly select Replace for an owned regular file"));
        return false;
    }
    QSaveFile out(path);
    if (!out.open(QIODevice::WriteOnly)) { setError(out.errorString()); return false; }
    const QByteArray payload = QJsonDocument(m_document).toJson(QJsonDocument::Indented);
    if (out.write(payload) != payload.size() || !out.commit()) {
        setError(QStringLiteral("Failed atomic save; previous document retained"));
        return false;
    }
    setError(QString());
    return true;
}

bool ScreenplayService::saveCanonical(const QUrl &url, bool replace) {
    if (!url.isLocalFile()) { setError(QStringLiteral("Network URLs are never saved")); return false; }
    return writeCanonical(url.toLocalFile(), replace);
}

bool ScreenplayService::exportSource(const QUrl &url, const QString &format, bool replace) {
    if (m_document.isEmpty() || !url.isLocalFile() || QFileInfo(url.toLocalFile()).isSymLink()) {
        setError(QStringLiteral("A canonical screenplay and ordinary local output path are required"));
        return false;
    }
    QTemporaryDir temp;
    if (!temp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString source = temp.filePath("document.json");
    const QString exported = temp.filePath("exported-screenplay.txt");
    if (!saveTemp(source, QJsonDocument(m_document).toJson())) return false;
    const QString cli = cliPath();
    if (cli.isEmpty()) { setError(QStringLiteral("Local screenplay CLI unavailable")); return false; }
    QProcess proc;
    proc.start(cli, {"export", "--format", format, "--input", source, "--output", exported}, QIODevice::ReadOnly);
    if (!proc.waitForStarted(5000) || !proc.waitForFinished(20000) || proc.exitCode() != 0) {
        setError(QString::fromUtf8(proc.readAllStandardError()).left(1500));
        return false;
    }
    QFile exportedFile(exported);
    if (!exportedFile.open(QIODevice::ReadOnly)) { setError(QStringLiteral("Export output missing")); return false; }
    const QFileInfo destInfo(url.toLocalFile());
    if (destInfo.exists() && !replace) { setError(QStringLiteral("Destination exists; explicit Replace required")); return false; }
    QSaveFile dest(url.toLocalFile());
    if (!dest.open(QIODevice::WriteOnly)) { setError(dest.errorString()); return false; }
    const QByteArray payload = exportedFile.readAll();
    if (dest.write(payload) != payload.size() || !dest.commit()) {
        setError(QStringLiteral("Export atomic save failed")); return false;
    }
    m_receipt = QString::fromUtf8(proc.readAllStandardOutput());
    emit receiptChanged();
    setError(QString());
    return true;
}

bool ScreenplayService::derive(bool refreshAffected) {
    if (m_document.isEmpty()) { setError(QStringLiteral("Import a screenplay first")); return false; }
    QTemporaryDir tmp;
    if (!tmp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString source = tmp.filePath("document.json");
    const QString target = tmp.filePath("breakdown.json");
    if (!saveTemp(source, QJsonDocument(m_document).toJson())) return false;
    QStringList args{"breakdown", "--input", source, "--output", target};
    if (!m_breakdown.isEmpty()) {
        const QString prior = tmp.filePath("prior.json");
        if (!saveTemp(prior, QJsonDocument(m_breakdown).toJson())) return false;
        args.append({"--previous", prior});
    }
    if (refreshAffected) args.append("--refresh-affected");
    QJsonObject result;
    if (!run(args, target, result)) return false;
    m_breakdown = result;
    emit breakdownChanged();
    m_handoff = QJsonObject();
    emit handoffChanged();
    return true;
}

bool ScreenplayService::review(const QString &id, const QString &decision, const QString &actor) {
    if (m_breakdown.isEmpty() || actor.trimmed().isEmpty()) {
        setError(QStringLiteral("A breakdown and named local reviewer are required")); return false;
    }
    QTemporaryDir tmp;
    if (!tmp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString input = tmp.filePath("breakdown.json"), target = tmp.filePath("reviewed.json");
    if (!saveTemp(input, QJsonDocument(m_breakdown).toJson())) return false;
    QJsonObject result;
    if (!run({"review", "--input", input, "--candidate-id", id,
              "--decision", decision, "--actor", actor, "--output", target}, target, result)) return false;
    m_breakdown = result;
    emit breakdownChanged();
    m_handoff = QJsonObject();
    emit handoffChanged();
    return true;
}

bool ScreenplayService::fork(const QString &branchId) {
    if (m_document.isEmpty()) { setError(QStringLiteral("No active screenplay")); return false; }
    QTemporaryDir tmp;
    if (!tmp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString input = tmp.filePath("document.json"), target = tmp.filePath("branch.json");
    if (!saveTemp(input, QJsonDocument(m_document).toJson())) return false;
    QJsonObject result;
    if (!run({"branch", "--input", input, "--branch", branchId, "--output", target}, target, result)) return false;
    m_document = result;
    emit documentChanged();
    clearDerived();
    return true;
}

bool ScreenplayService::editHeading(const QString &sceneId, const QString &heading) {
    if (m_document.isEmpty()) { setError(QStringLiteral("No active screenplay")); return false; }
    QTemporaryDir tmp;
    if (!tmp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString input = tmp.filePath("document.json"), target = tmp.filePath("edited.json");
    if (!saveTemp(input, QJsonDocument(m_document).toJson())) return false;
    QJsonObject result;
    if (!run({"edit-scene", "--input", input, "--scene", sceneId,
              "--heading", heading, "--output", target}, target, result)) return false;
    m_document = result;
    emit documentChanged();
    // Do not drop the prior breakdown: it is needed to show STALE on explicit derive.
    m_handoff = QJsonObject();
    emit handoffChanged();
    return true;
}

bool ScreenplayService::buildHandoffPreview() {
    if (m_document.isEmpty() || m_breakdown.isEmpty()) {
        setError(QStringLiteral("Both a document and a reviewed breakdown are required")); return false;
    }
    QTemporaryDir tmp;
    if (!tmp.isValid()) { setError(QStringLiteral("Secure temporary directory unavailable")); return false; }
    const QString source = tmp.filePath("doc.json"), bd = tmp.filePath("breakdown.json"),
                  target = tmp.filePath("handoff.json");
    if (!saveTemp(source, QJsonDocument(m_document).toJson()) ||
        !saveTemp(bd, QJsonDocument(m_breakdown).toJson())) return false;
    QJsonObject result;
    if (!run({"handoff", "--input", source, "--breakdown", bd, "--output", target},
             target, result, true)) return false;
    m_handoff = result;
    emit handoffChanged();
    return result.value("status").toString() == "LOCAL_REVIEW_ONLY";
}
