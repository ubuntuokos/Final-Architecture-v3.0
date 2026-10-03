// SPDX-License-Identifier: Apache-2.0
#include "ProductEntitlementService.h"

#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <algorithm>

ProductEntitlementService::ProductEntitlementService(const QString &repoRoot, QObject *parent)
    : QObject(parent), m_repoRoot(QDir(repoRoot).absolutePath())
{
    refresh();
}

QVariantMap ProductEntitlementService::readCanonical(const QString &fileName) const
{
    QStringList candidates;
    if (!m_repoRoot.isEmpty()) candidates << QDir(m_repoRoot).filePath(QStringLiteral("canonical/%1").arg(fileName));
    candidates << QDir(QStringLiteral("/usr/share/fa3/canonical")).filePath(fileName);

    for (const auto &path : candidates) {
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) continue;
        QJsonParseError error;
        const auto document = QJsonDocument::fromJson(file.readAll(), &error);
        if (error.error == QJsonParseError::NoError && document.isObject())
            return document.object().toVariantMap();
    }
    return {};
}

void ProductEntitlementService::refresh()
{
    const auto levels = readCanonical(QStringLiteral("FA3-OPERATING-LEVEL-MODEL-001.json"));
    const auto portfolio = readCanonical(QStringLiteral("FA3-APPLICATION-PORTFOLIO-001.json"));
    const auto packs = readCanonical(QStringLiteral("FA3-DOMAIN-PACK-REGISTRY-001.json"));
    const auto policy = readCanonical(QStringLiteral("FA3-ENTITLEMENT-POLICY-001.json"));

    const bool valid =
        levels.value(QStringLiteral("id")).toString() == QStringLiteral("FA3-OPERATING-LEVEL-MODEL-001") &&
        portfolio.value(QStringLiteral("id")).toString() == QStringLiteral("FA3-APPLICATION-PORTFOLIO-001") &&
        packs.value(QStringLiteral("id")).toString() == QStringLiteral("FA3-DOMAIN-PACK-REGISTRY-001") &&
        policy.value(QStringLiteral("id")).toString() == QStringLiteral("FA3-ENTITLEMENT-POLICY-001") &&
        levels.value(QStringLiteral("capability_count")).toInt() == 175 &&
        portfolio.value(QStringLiteral("capability_count")).toInt() == 175 &&
        packs.value(QStringLiteral("capability_count")).toInt() == 175 &&
        policy.value(QStringLiteral("capability_count")).toInt() == 175 &&
        policy.value(QStringLiteral("authority")).isValid() &&
        !policy.value(QStringLiteral("authority")).toBool();

    if (!valid) {
        m_operatingLevels.clear();
        m_applications.clear();
        m_domainPacks.clear();
        m_status = QStringLiteral("FAIL_CLOSED");
        m_lastError = QStringLiteral("A Product Entitlement kanonikus rekordjai hiányoznak vagy érvénytelenek.");
        emit catalogChanged();
        return;
    }

    m_operatingLevels = levels.value(QStringLiteral("levels")).toList();
    std::sort(m_operatingLevels.begin(), m_operatingLevels.end(), [](const QVariant &left, const QVariant &right) {
        return left.toMap().value(QStringLiteral("rank")).toInt() <
               right.toMap().value(QStringLiteral("rank")).toInt();
    });

    m_applications.clear();
    for (const auto &value : portfolio.value(QStringLiteral("applications")).toList()) {
        const auto row = value.toMap();
        if (!row.value(QStringLiteral("individually_entitleable")).toBool()) continue;
        if (row.value(QStringLiteral("portfolio_state")).toString() == QStringLiteral("RETIRED")) continue;
        m_applications.append(row);
    }
    std::sort(m_applications.begin(), m_applications.end(), [](const QVariant &left, const QVariant &right) {
        return left.toMap().value(QStringLiteral("name")).toString().localeAwareCompare(
                   right.toMap().value(QStringLiteral("name")).toString()) < 0;
    });

    m_domainPacks = packs.value(QStringLiteral("domain_packs")).toList();
    std::sort(m_domainPacks.begin(), m_domainPacks.end(), [](const QVariant &left, const QVariant &right) {
        return left.toMap().value(QStringLiteral("name")).toString().localeAwareCompare(
                   right.toMap().value(QStringLiteral("name")).toString()) < 0;
    });

    m_status = QStringLiteral("READ_ONLY_CANONICAL_PROJECTION");
    m_lastError.clear();
    emit catalogChanged();
}
