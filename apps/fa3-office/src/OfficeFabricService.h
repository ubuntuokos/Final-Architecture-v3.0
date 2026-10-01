// SPDX-License-Identifier: Apache-2.0
#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class OfficeFabricService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString fabricState READ fabricState CONSTANT)
    Q_PROPERTY(QString engineCandidate READ engineCandidate CONSTANT)

public:
    explicit OfficeFabricService(QObject *parent = nullptr);

    QString fabricState() const;
    QString engineCandidate() const;

    Q_INVOKABLE QVariantList surfaces() const;
    Q_INVOKABLE QVariantList formatProfiles() const;
    Q_INVOKABLE QVariantMap runtimeProbe() const;
    Q_INVOKABLE QVariantMap prepareSession(const QString &surface,
                                           const QString &format,
                                           bool aiEnabled) const;

private:
    static bool supportedSurface(const QString &surface);
    static bool candidateEditableFormat(const QString &format);
};
