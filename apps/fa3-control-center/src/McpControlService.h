#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class McpControlService final : public QObject
{
    Q_OBJECT
public:
    explicit McpControlService(QObject *parent = nullptr);

    Q_INVOKABLE QVariantList targets() const;
    Q_INVOKABLE QVariantMap authoritySnapshot(const QString &targetId) const;
    Q_INVOKABLE QVariantMap createDraftRequest(const QString &mode,
                                                const QString &targetId,
                                                const QString &prompt,
                                                const QString &attachmentsJson,
                                                const QString &riskHint) const;

private:
    bool isKnownTarget(const QString &targetId) const;
};
