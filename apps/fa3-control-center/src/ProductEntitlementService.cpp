// SPDX-License-Identifier: Apache-2.0
#include "ProductEntitlementService.h"
#include <QDir>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <algorithm>
ProductEntitlementService::ProductEntitlementService(const QString &repoRoot,QObject *parent):QObject(parent),m_repoRoot(QDir(repoRoot).absolutePath()){refresh();}
QVariantMap ProductEntitlementService::readCanonical(const QString &fileName) const{
 QStringList c;if(!m_repoRoot.isEmpty())c<<QDir(m_repoRoot).filePath(QStringLiteral("canonical/%1").arg(fileName));c<<QDir(QStringLiteral("/usr/share/fa3/canonical")).filePath(fileName);
 for(const auto &path:c){QFile f(path);if(!f.open(QIODevice::ReadOnly))continue;QJsonParseError e;const auto d=QJsonDocument::fromJson(f.readAll(),&e);if(e.error==QJsonParseError::NoError&&d.isObject())return d.object().toVariantMap();}return {};
}
void ProductEntitlementService::refresh(){
 const auto levels=readCanonical(QStringLiteral("FA3-OPERATING-LEVEL-MODEL-001.json"));const auto portfolio=readCanonical(QStringLiteral("FA3-APPLICATION-PORTFOLIO-001.json"));const auto packs=readCanonical(QStringLiteral("FA3-DOMAIN-PACK-REGISTRY-001.json"));const auto catalog=readCanonical(QStringLiteral("FA3-PRODUCT-CATALOG-001.json"));const auto policy=readCanonical(QStringLiteral("FA3-ENTITLEMENT-POLICY-001.json"));
 const bool valid=levels.value(QStringLiteral("id")).toString()==QStringLiteral("FA3-OPERATING-LEVEL-MODEL-001")&&portfolio.value(QStringLiteral("id")).toString()==QStringLiteral("FA3-APPLICATION-PORTFOLIO-001")&&packs.value(QStringLiteral("id")).toString()==QStringLiteral("FA3-DOMAIN-PACK-REGISTRY-001")&&catalog.value(QStringLiteral("id")).toString()==QStringLiteral("FA3-PRODUCT-CATALOG-001")&&policy.value(QStringLiteral("id")).toString()==QStringLiteral("FA3-ENTITLEMENT-POLICY-001")&&levels.value(QStringLiteral("capability_count")).toInt()==175&&portfolio.value(QStringLiteral("capability_count")).toInt()==175&&packs.value(QStringLiteral("capability_count")).toInt()==175&&catalog.value(QStringLiteral("capability_count")).toInt()==175&&policy.value(QStringLiteral("capability_count")).toInt()==175&&!catalog.value(QStringLiteral("authority")).toBool()&&!policy.value(QStringLiteral("authority")).toBool();
 if(!valid){m_operatingLevels.clear();m_applications.clear();m_domainPacks.clear();m_optionalAddons.clear();m_status=QStringLiteral("FAIL_CLOSED");m_lastError=QStringLiteral("A Product Entitlement kanonikus rekordjai hiányoznak vagy érvénytelenek.");emit catalogChanged();return;}
 m_operatingLevels.clear();const auto levelMap=levels.value(QStringLiteral("levels")).toMap();for(const auto &v:levels.value(QStringLiteral("order")).toList()){const auto id=v.toString();auto row=levelMap.value(id).toMap();row.insert(QStringLiteral("level_id"),id);m_operatingLevels.append(row);}
 m_applications.clear();for(const auto &v:portfolio.value(QStringLiteral("applications")).toList()){const auto row=v.toMap();if(!row.value(QStringLiteral("individually_entitleable")).toBool())continue;if(row.value(QStringLiteral("portfolio_state")).toString()==QStringLiteral("RETIRED"))continue;m_applications.append(row);}std::sort(m_applications.begin(),m_applications.end(),[](const QVariant&a,const QVariant&b){return a.toMap().value(QStringLiteral("name")).toString().localeAwareCompare(b.toMap().value(QStringLiteral("name")).toString())<0;});
 m_domainPacks=catalog.value(QStringLiteral("bundles")).toList();std::sort(m_domainPacks.begin(),m_domainPacks.end(),[](const QVariant&a,const QVariant&b){return a.toMap().value(QStringLiteral("name")).toString().localeAwareCompare(b.toMap().value(QStringLiteral("name")).toString())<0;});
 m_optionalAddons=catalog.value(QStringLiteral("optional_addons")).toList();std::sort(m_optionalAddons.begin(),m_optionalAddons.end(),[](const QVariant&a,const QVariant&b){return a.toMap().value(QStringLiteral("class")).toString()<b.toMap().value(QStringLiteral("class")).toString();});
 m_status=QStringLiteral("READ_ONLY_CANONICAL_PROJECTION");m_lastError.clear();emit catalogChanged();
}
