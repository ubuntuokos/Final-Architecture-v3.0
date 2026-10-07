#include "SystemDeviceModel.h"

#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QPrinterInfo>
#include <QRegularExpression>
#include <QSysInfo>
#include <QThread>

SystemDeviceModel::SystemDeviceModel(QObject *parent)
    : QObject(parent)
{
    refresh();
}

QString SystemDeviceModel::readTextFile(const QString &path) const
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) return {};
    return QString::fromUtf8(file.readAll()).trimmed();
}

void SystemDeviceModel::addRow(const QString &kind, const QString &id, const QString &title,
                               const QString &detail, const QString &status)
{
    QVariantMap row;
    row.insert(QStringLiteral("kind"), kind);
    row.insert(QStringLiteral("id"), id);
    row.insert(QStringLiteral("title"), title);
    row.insert(QStringLiteral("detail"), detail);
    row.insert(QStringLiteral("status"), status);
    m_inventory.append(row);
}

void SystemDeviceModel::refresh()
{
    m_inventory.clear();

    addRow(QStringLiteral("CPU"), QStringLiteral("cpu"), QStringLiteral("CPU"),
           QStringLiteral("%1 logical thread · %2 · local GUI observation only; FA3 hardware discovery / HRB remains authoritative for admission and placement")
               .arg(QThread::idealThreadCount()).arg(QSysInfo::currentCpuArchitecture()),
           QStringLiteral("OBSERVED_NON_AUTHORITATIVE"));

    const QRegularExpression drmCard(QStringLiteral("^card\\d+$"));
    const QDir drmDir(QStringLiteral("/sys/class/drm"));
    bool gpuFound = false;
    for (const auto &entry : drmDir.entryList(QDir::Dirs | QDir::System | QDir::NoDotAndDotDot)) {
        if (!drmCard.match(entry).hasMatch()) continue;
        const auto base = drmDir.absoluteFilePath(entry + QStringLiteral("/device"));
        if (!QFileInfo::exists(base)) continue;
        const auto vendor = readTextFile(base + QStringLiteral("/vendor"));
        const auto device = readTextFile(base + QStringLiteral("/device"));
        addRow(QStringLiteral("GPU"), entry, QStringLiteral("GPU · %1").arg(entry),
               QStringLiteral("DRM observation · vendor %1 · device %2 · diagnostic only; FA3 hardware discovery / HRB remains authoritative")
                   .arg(vendor.isEmpty() ? QStringLiteral("N/A") : vendor,
                        device.isEmpty() ? QStringLiteral("N/A") : device),
               QStringLiteral("OBSERVED_NON_AUTHORITATIVE"));
        gpuFound = true;
    }
    if (!gpuFound) {
        addRow(QStringLiteral("GPU"), QStringLiteral("gpu-adapter"), QStringLiteral("GPU"),
               QStringLiteral("No local DRM accelerator observation; canonical discovery/provider adapters may still supply inventory. Admission remains HRB-authoritative."),
               QStringLiteral("ADAPTER_GATED_NON_AUTHORITATIVE"));
    }

    const QDir accelDir(QStringLiteral("/sys/class/accel"));
    const auto accelEntries = accelDir.exists()
        ? accelDir.entryList({QStringLiteral("accel*")}, QDir::Dirs | QDir::System | QDir::NoDotAndDotDot)
        : QStringList{};
    if (accelEntries.isEmpty()) {
        addRow(QStringLiteral("NPU"), QStringLiteral("npu-adapter"), QStringLiteral("NPU"),
               QStringLiteral("No local /sys/class/accel observation; canonical discovery/vendor adapter remains the source of capability truth."),
               QStringLiteral("ADAPTER_GATED_NON_AUTHORITATIVE"));
    } else {
        for (const auto &entry : accelEntries) {
            addRow(QStringLiteral("NPU"), entry, QStringLiteral("NPU · %1").arg(entry),
                   QStringLiteral("Linux accelerator class observation · diagnostic only; FA3 hardware discovery / HRB remains authoritative"),
                   QStringLiteral("OBSERVED_NON_AUTHORITATIVE"));
        }
    }

    const auto productName = readTextFile(QStringLiteral("/sys/class/dmi/id/product_name"));
    const auto productVersion = readTextFile(QStringLiteral("/sys/class/dmi/id/product_version"));
    if (productName.contains(QStringLiteral("DGX"), Qt::CaseInsensitive)) {
        addRow(QStringLiteral("DGX"), QStringLiteral("dgx-platform"), productName,
               QStringLiteral("%1 · local platform observation only; no admission authority")
                   .arg(productVersion.isEmpty() ? QStringLiteral("NVIDIA DGX platform") : productVersion),
               QStringLiteral("OBSERVED_NON_AUTHORITATIVE"));
    } else {
        addRow(QStringLiteral("DGX"), QStringLiteral("dgx-platform"), QStringLiteral("NVIDIA DGX / NVSwitch fabric"),
               QStringLiteral("Optional hardware-agnostic FA3 target; not observed by this local diagnostic probe."),
               QStringLiteral("NOT OBSERVED"));
    }

    const QDir devDir(QStringLiteral("/dev"));
    const auto videoEntries = devDir.entryList({QStringLiteral("video*")}, QDir::System | QDir::Files | QDir::NoDotAndDotDot);
    if (videoEntries.isEmpty()) {
        addRow(QStringLiteral("WEBCAM"), QStringLiteral("camera-adapter"), QStringLiteral("Webkamera / Capture"),
               QStringLiteral("No V4L2 video node discovered."), QStringLiteral("NOT DETECTED"));
    } else {
        for (const auto &entry : videoEntries) {
            addRow(QStringLiteral("WEBCAM"), entry, QStringLiteral("/dev/%1").arg(entry),
                   QStringLiteral("V4L2 video/capture node"), QStringLiteral("DISCOVERED"));
        }
    }

    const auto printers = QPrinterInfo::availablePrinters();
    if (printers.isEmpty()) {
        addRow(QStringLiteral("PRINTER"), QStringLiteral("printer-adapter"), QStringLiteral("Nyomtató"),
               QStringLiteral("No Qt/CUPS printer discovered."), QStringLiteral("NOT DETECTED"));
    } else {
        for (const auto &printer : printers) {
            const auto detail = QStringLiteral("%1%2")
                .arg(printer.description().isEmpty() ? printer.location() : printer.description(),
                     printer.isDefault() ? QStringLiteral(" · DEFAULT") : QString());
            addRow(QStringLiteral("PRINTER"), printer.printerName(), printer.printerName(), detail,
                   QStringLiteral("DISCOVERED"));
        }
    }

    if (QFileInfo::exists(QStringLiteral("/dev/scanner"))) {
        addRow(QStringLiteral("SCANNER"), QStringLiteral("/dev/scanner"), QStringLiteral("Scanner"),
               QStringLiteral("Generic scanner node discovered; SANE adapter owns detailed capability discovery."),
               QStringLiteral("DISCOVERED"));
    } else {
        addRow(QStringLiteral("SCANNER"), QStringLiteral("sane-adapter"), QStringLiteral("Scanner / SANE"),
               QStringLiteral("Detailed scanner discovery requires the SANE provider adapter."),
               QStringLiteral("ADAPTER-GATED"));
    }

    const QDir sndDir(QStringLiteral("/dev/snd"));
    const auto midiEntries = sndDir.exists()
        ? sndDir.entryList({QStringLiteral("midiC*D*")}, QDir::System | QDir::Files | QDir::NoDotAndDotDot)
        : QStringList{};
    for (const auto &entry : midiEntries) {
        addRow(QStringLiteral("MIDI"), entry, QStringLiteral("/dev/snd/%1").arg(entry),
               QStringLiteral("ALSA raw MIDI port"), QStringLiteral("DISCOVERED"));
    }
    if (QFileInfo::exists(QStringLiteral("/dev/snd/seq"))) {
        addRow(QStringLiteral("MIDI"), QStringLiteral("alsa-seq"), QStringLiteral("ALSA Sequencer"),
               QStringLiteral("/dev/snd/seq · routing/control-surface endpoint"), QStringLiteral("DISCOVERED"));
    }
    if (midiEntries.isEmpty() && !QFileInfo::exists(QStringLiteral("/dev/snd/seq"))) {
        addRow(QStringLiteral("MIDI"), QStringLiteral("midi-adapter"), QStringLiteral("MIDI / Control Surface"),
               QStringLiteral("No ALSA MIDI endpoint discovered."), QStringLiteral("NOT DETECTED"));
    }

    m_lastRefresh = QDateTime::currentDateTime().toString(Qt::ISODate);
    emit inventoryChanged();
}

QVariantList SystemDeviceModel::byKind(const QString &kind) const
{
    QVariantList result;
    for (const auto &value : m_inventory) {
        const auto row = value.toMap();
        if (row.value(QStringLiteral("kind")).toString().compare(kind, Qt::CaseInsensitive) == 0)
            result.append(row);
    }
    return result;
}
