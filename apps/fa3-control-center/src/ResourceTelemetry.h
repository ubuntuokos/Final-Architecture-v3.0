#pragma once

#include <QObject>
#include <QProcess>
#include <QTimer>

class ResourceTelemetry final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(double cpuPercent READ cpuPercent NOTIFY telemetryChanged)
    Q_PROPERTY(double ramPercent READ ramPercent NOTIFY telemetryChanged)
    Q_PROPERTY(double ramUsedGiB READ ramUsedGiB NOTIFY telemetryChanged)
    Q_PROPERTY(double ramTotalGiB READ ramTotalGiB NOTIFY telemetryChanged)
    Q_PROPERTY(bool gpuAvailable READ gpuAvailable NOTIFY telemetryChanged)
    Q_PROPERTY(QString gpuLabel READ gpuLabel NOTIFY telemetryChanged)
    Q_PROPERTY(double gpuPercent READ gpuPercent NOTIFY telemetryChanged)
    Q_PROPERTY(double gpuMemoryUsedGiB READ gpuMemoryUsedGiB NOTIFY telemetryChanged)
    Q_PROPERTY(double gpuMemoryTotalGiB READ gpuMemoryTotalGiB NOTIFY telemetryChanged)
    Q_PROPERTY(double gpuTemperatureC READ gpuTemperatureC NOTIFY telemetryChanged)
    Q_PROPERTY(bool npuAvailable READ npuAvailable NOTIFY telemetryChanged)
    Q_PROPERTY(QString npuLabel READ npuLabel NOTIFY telemetryChanged)
    Q_PROPERTY(double npuPercent READ npuPercent NOTIFY telemetryChanged)
    Q_PROPERTY(QString pressureState READ pressureState NOTIFY telemetryChanged)
    Q_PROPERTY(QString pressureSummary READ pressureSummary NOTIFY telemetryChanged)

public:
    explicit ResourceTelemetry(QObject *parent = nullptr);

    double cpuPercent() const { return m_cpuPercent; }
    double ramPercent() const { return m_ramPercent; }
    double ramUsedGiB() const { return m_ramUsedGiB; }
    double ramTotalGiB() const { return m_ramTotalGiB; }

    bool gpuAvailable() const { return m_gpuAvailable; }
    QString gpuLabel() const { return m_gpuLabel; }
    double gpuPercent() const { return m_gpuPercent; }
    double gpuMemoryUsedGiB() const { return m_gpuMemoryUsedGiB; }
    double gpuMemoryTotalGiB() const { return m_gpuMemoryTotalGiB; }
    double gpuTemperatureC() const { return m_gpuTemperatureC; }

    bool npuAvailable() const { return m_npuAvailable; }
    QString npuLabel() const { return m_npuLabel; }
    double npuPercent() const { return m_npuPercent; }

    QString pressureState() const { return m_pressureState; }
    QString pressureSummary() const { return m_pressureSummary; }

    Q_INVOKABLE void refreshNow();

signals:
    void telemetryChanged();

private slots:
    void sampleFast();
    void sampleAccelerators();
    void handleGpuProbeFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void handleGpuProbeError(QProcess::ProcessError error);

private:
    void sampleCpu();
    void sampleMemory();
    void sampleLinuxGpuFallback();
    void sampleLinuxNpu();
    void updatePressure();
    void clearGpu();

    QTimer m_fastTimer;
    QTimer m_acceleratorTimer;
    QProcess m_gpuProbe;
    bool m_nvidiaProbeDisabled = false;

    quint64 m_previousCpuTotal = 0;
    quint64 m_previousCpuIdle = 0;

    double m_cpuPercent = -1.0;
    double m_ramPercent = -1.0;
    double m_ramUsedGiB = -1.0;
    double m_ramTotalGiB = -1.0;

    bool m_gpuAvailable = false;
    QString m_gpuLabel = QStringLiteral("GPU");
    double m_gpuPercent = -1.0;
    double m_gpuMemoryUsedGiB = -1.0;
    double m_gpuMemoryTotalGiB = -1.0;
    double m_gpuTemperatureC = -1.0;

    bool m_npuAvailable = false;
    QString m_npuLabel = QStringLiteral("NPU");
    double m_npuPercent = -1.0;

    QString m_pressureState = QStringLiteral("NORMAL");
    QString m_pressureSummary = QStringLiteral("No measured resource pressure");
};
