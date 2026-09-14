#include "ChatFileService.h"

#include <QFile>
#include <QFileInfo>
#include <QMimeDatabase>
#include <QSaveFile>
#include <QStringConverter>
#include <QTextStream>

ChatFileService::ChatFileService(QObject *parent)
    : QObject(parent)
{
}

QString ChatFileService::humanReadableSize(qint64 bytes)
{
    static const char *units[] = {"B", "KiB", "MiB", "GiB", "TiB"};
    double value = static_cast<double>(bytes);
    int unit = 0;
    while (value >= 1024.0 && unit < 4) {
        value /= 1024.0;
        ++unit;
    }
    return unit == 0
        ? QStringLiteral("%1 %2").arg(bytes).arg(QString::fromLatin1(units[unit]))
        : QStringLiteral("%1 %2").arg(value, 0, 'f', value < 10.0 ? 1 : 0).arg(QString::fromLatin1(units[unit]));
}

QString ChatFileService::analysisClassFor(const QString &mimeName, const QString &suffix)
{
    const QString ext = suffix.toLower();
    if (mimeName == QStringLiteral("image/svg+xml") || ext == QStringLiteral("svg"))
        return QStringLiteral("SVG");
    if (mimeName.startsWith(QStringLiteral("image/")))
        return QStringLiteral("IMAGE");
    if (mimeName.startsWith(QStringLiteral("text/")) ||
        QStringList{QStringLiteral("md"), QStringLiteral("json"), QStringLiteral("yaml"), QStringLiteral("yml"),
                    QStringLiteral("toml"), QStringLiteral("xml"), QStringLiteral("csv"), QStringLiteral("tsv"),
                    QStringLiteral("log"), QStringLiteral("ini"), QStringLiteral("cfg")}.contains(ext))
        return QStringLiteral("TEXT");
    if (mimeName == QStringLiteral("application/pdf") || ext == QStringLiteral("pdf"))
        return QStringLiteral("PDF");
    if (QStringList{QStringLiteral("xls"), QStringLiteral("xlsx"), QStringLiteral("ods"), QStringLiteral("csv"), QStringLiteral("tsv")}.contains(ext) ||
        mimeName.contains(QStringLiteral("spreadsheet")) || mimeName.contains(QStringLiteral("excel")))
        return QStringLiteral("SPREADSHEET");
    if (QStringList{QStringLiteral("doc"), QStringLiteral("docx"), QStringLiteral("odt"), QStringLiteral("rtf"), QStringLiteral("epub")}.contains(ext) ||
        mimeName.contains(QStringLiteral("wordprocessing")) || mimeName.contains(QStringLiteral("opendocument.text")))
        return QStringLiteral("DOCUMENT");
    if (QStringList{QStringLiteral("ppt"), QStringLiteral("pptx"), QStringLiteral("odp")}.contains(ext) ||
        mimeName.contains(QStringLiteral("presentation")))
        return QStringLiteral("PRESENTATION");
    if (mimeName.startsWith(QStringLiteral("audio/")))
        return QStringLiteral("AUDIO");
    if (mimeName.startsWith(QStringLiteral("video/")))
        return QStringLiteral("VIDEO");
    return QStringLiteral("GENERIC_BINARY");
}

QVariantMap ChatFileService::inspectLocalFile(const QUrl &url) const
{
    QVariantMap result;
    result.insert(QStringLiteral("valid"), false);
    result.insert(QStringLiteral("url"), url.toString());

    if (!url.isValid() || !url.isLocalFile()) {
        result.insert(QStringLiteral("error"), QStringLiteral("Only local files can be attached."));
        return result;
    }

    const QString path = url.toLocalFile();
    const QFileInfo info(path);
    if (!info.exists() || !info.isFile() || !info.isReadable()) {
        result.insert(QStringLiteral("error"), QStringLiteral("The selected file is missing or not readable."));
        return result;
    }

    QMimeDatabase database;
    const QString mimeName = database.mimeTypeForFile(info, QMimeDatabase::MatchContent).name();
    const QString analysisClass = analysisClassFor(mimeName, info.suffix());

    result.insert(QStringLiteral("valid"), true);
    result.insert(QStringLiteral("path"), info.absoluteFilePath());
    result.insert(QStringLiteral("name"), info.fileName());
    result.insert(QStringLiteral("suffix"), info.suffix().toLower());
    result.insert(QStringLiteral("mime"), mimeName);
    result.insert(QStringLiteral("size"), info.size());
    result.insert(QStringLiteral("sizeLabel"), humanReadableSize(info.size()));
    result.insert(QStringLiteral("analysisClass"), analysisClass);
    result.insert(QStringLiteral("adapterValidationRequired"), analysisClass == QStringLiteral("GENERIC_BINARY"));
    result.insert(QStringLiteral("error"), QString());
    return result;
}

QVariantMap ChatFileService::saveTextFile(const QUrl &destination, const QString &text) const
{
    QVariantMap result;
    result.insert(QStringLiteral("ok"), false);
    if (!destination.isValid() || !destination.isLocalFile()) {
        result.insert(QStringLiteral("error"), QStringLiteral("The destination must be a local file."));
        return result;
    }

    QSaveFile file(destination.toLocalFile());
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        result.insert(QStringLiteral("error"), file.errorString());
        return result;
    }

    QTextStream stream(&file);
    stream.setEncoding(QStringConverter::Utf8);
    stream << text;
    stream.flush();
    if (!file.commit()) {
        result.insert(QStringLiteral("error"), file.errorString());
        return result;
    }

    result.insert(QStringLiteral("ok"), true);
    result.insert(QStringLiteral("path"), destination.toLocalFile());
    result.insert(QStringLiteral("error"), QString());
    return result;
}

QVariantMap ChatFileService::copyLocalFile(const QUrl &source, const QUrl &destination) const
{
    QVariantMap result;
    result.insert(QStringLiteral("ok"), false);
    if (!source.isValid() || !source.isLocalFile() || !destination.isValid() || !destination.isLocalFile()) {
        result.insert(QStringLiteral("error"), QStringLiteral("Source and destination must be local files."));
        return result;
    }

    QFile input(source.toLocalFile());
    if (!input.open(QIODevice::ReadOnly)) {
        result.insert(QStringLiteral("error"), input.errorString());
        return result;
    }

    QSaveFile output(destination.toLocalFile());
    if (!output.open(QIODevice::WriteOnly)) {
        result.insert(QStringLiteral("error"), output.errorString());
        return result;
    }

    QByteArray buffer;
    buffer.resize(1024 * 1024);
    while (!input.atEnd()) {
        const qint64 bytesRead = input.read(buffer.data(), buffer.size());
        if (bytesRead < 0) {
            result.insert(QStringLiteral("error"), input.errorString());
            output.cancelWriting();
            return result;
        }
        if (bytesRead > 0 && output.write(buffer.constData(), bytesRead) != bytesRead) {
            result.insert(QStringLiteral("error"), output.errorString());
            output.cancelWriting();
            return result;
        }
    }

    if (!output.commit()) {
        result.insert(QStringLiteral("error"), output.errorString());
        return result;
    }

    result.insert(QStringLiteral("ok"), true);
    result.insert(QStringLiteral("path"), destination.toLocalFile());
    result.insert(QStringLiteral("error"), QString());
    return result;
}
