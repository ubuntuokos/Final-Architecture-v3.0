#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and p.read_text(encoding="utf-8") == content:
        return
    p.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str, sentinel: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    if sentinel in text:
        return
    if old not in text:
        raise SystemExit(f"materializer marker missing: {path}: {old[:100]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---- C++ services ---------------------------------------------------------
write("apps/fa3-control-center/src/CivitaiClient.h", r'''#pragma once

#include <QObject>
#include <QVariantList>

class QNetworkAccessManager;
class SecretBrokerService;

class CivitaiClient final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(bool busy READ busy NOTIFY changed)
    Q_PROPERTY(QString statusText READ statusText NOTIFY changed)
    Q_PROPERTY(QString errorText READ errorText NOTIFY changed)
    Q_PROPERTY(QVariantList models READ models NOTIFY changed)

public:
    explicit CivitaiClient(SecretBrokerService *broker, QObject *parent = nullptr);

    bool busy() const { return m_busy; }
    QString statusText() const;
    QString errorText() const { return m_errorText; }
    QVariantList models() const { return m_models; }

    Q_INVOKABLE void searchModels(const QString &query);

signals:
    void changed();

private:
    SecretBrokerService *m_broker = nullptr;
    QNetworkAccessManager *m_network = nullptr;
    bool m_busy = false;
    QString m_errorText;
    QVariantList m_models;
};
''')

write("apps/fa3-control-center/src/CivitaiClient.cpp", r'''#include "CivitaiClient.h"
#include "SecretBrokerService.h"

#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QUrlQuery>

CivitaiClient::CivitaiClient(SecretBrokerService *broker, QObject *parent)
    : QObject(parent), m_broker(broker), m_network(new QNetworkAccessManager(this))
{
}

QString CivitaiClient::statusText() const
{
    if (m_busy) return QStringLiteral("LOADING");
    if (!m_errorText.isEmpty()) return QStringLiteral("ERROR");
    return m_models.isEmpty() ? QStringLiteral("READY") : QStringLiteral("LOADED");
}

void CivitaiClient::searchModels(const QString &queryText)
{
    if (m_busy) return;
    m_busy = true;
    m_errorText.clear();
    emit changed();

    QUrl url(QStringLiteral("https://civitai.com/api/v1/models"));
    QUrlQuery query;
    if (!queryText.trimmed().isEmpty()) query.addQueryItem(QStringLiteral("query"), queryText.trimmed());
    query.addQueryItem(QStringLiteral("limit"), QStringLiteral("24"));
    url.setQuery(query);

    QNetworkRequest request(url);
    request.setHeader(QNetworkRequest::UserAgentHeader, QStringLiteral("FA3-Control-Center/0.4 CivitAI-Provider"));
    request.setRawHeader("Accept", "application/json");
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);

    QByteArray token = m_broker ? m_broker->resolveSecret(QStringLiteral("civitai")) : QByteArray();
    if (!token.isEmpty()) request.setRawHeader("Authorization", QByteArray("Bearer ") + token);
    if (!token.isEmpty()) token.fill('\0');

    QNetworkReply *reply = m_network->get(request);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        const QByteArray payload = reply->readAll();
        m_busy = false;
        if (reply->error() != QNetworkReply::NoError) {
            m_errorText = reply->errorString();
            emit changed();
            reply->deleteLater();
            return;
        }

        QJsonParseError parseError;
        const QJsonDocument doc = QJsonDocument::fromJson(payload, &parseError);
        if (parseError.error != QJsonParseError::NoError || !doc.isObject()) {
            m_errorText = QStringLiteral("INVALID_CIVITAI_JSON");
            emit changed();
            reply->deleteLater();
            return;
        }

        QVariantList next;
        const QJsonArray items = doc.object().value(QStringLiteral("items")).toArray();
        for (const QJsonValue &itemValue : items) {
            const QJsonObject item = itemValue.toObject();
            const QJsonObject creator = item.value(QStringLiteral("creator")).toObject();
            const QJsonArray versions = item.value(QStringLiteral("modelVersions")).toArray();
            const QJsonObject version = versions.isEmpty() ? QJsonObject() : versions.first().toObject();
            const QJsonArray files = version.value(QStringLiteral("files")).toArray();
            const QJsonObject file = files.isEmpty() ? QJsonObject() : files.first().toObject();
            const QJsonObject hashes = file.value(QStringLiteral("hashes")).toObject();

            QVariantMap row;
            row.insert(QStringLiteral("id"), QString::number(item.value(QStringLiteral("id")).toVariant().toLongLong()));
            row.insert(QStringLiteral("name"), item.value(QStringLiteral("name")).toString());
            row.insert(QStringLiteral("type"), item.value(QStringLiteral("type")).toString());
            row.insert(QStringLiteral("creator"), creator.value(QStringLiteral("username")).toString());
            row.insert(QStringLiteral("versionId"), QString::number(version.value(QStringLiteral("id")).toVariant().toLongLong()));
            row.insert(QStringLiteral("versionName"), version.value(QStringLiteral("name")).toString());
            row.insert(QStringLiteral("fileName"), file.value(QStringLiteral("name")).toString());
            row.insert(QStringLiteral("downloadUrl"), file.value(QStringLiteral("downloadUrl")).toString());
            row.insert(QStringLiteral("sha256"), hashes.value(QStringLiteral("SHA256")).toString().toLower());
            row.insert(QStringLiteral("sizeKB"), file.value(QStringLiteral("sizeKB")).toDouble());
            row.insert(QStringLiteral("pickleScanResult"), file.value(QStringLiteral("pickleScanResult")).toString());
            row.insert(QStringLiteral("virusScanResult"), file.value(QStringLiteral("virusScanResult")).toString());
            next.push_back(row);
        }
        m_models = next;
        m_errorText.clear();
        emit changed();
        reply->deleteLater();
    });
}
''')

write("apps/fa3-control-center/src/SearchIndexService.h", r'''#pragma once

#include <QObject>
#include <QVariantList>
#include <QVariantMap>

class SearchIndexService final : public QObject
{
    Q_OBJECT
public:
    explicit SearchIndexService(QObject *parent = nullptr) : QObject(parent) {}

    Q_INVOKABLE QVariantList searchProjects(const QString &rootPath, const QString &query, int limit = 100) const;
    Q_INVOKABLE QVariantMap conversationIndexStatus() const;
};
''')

write("apps/fa3-control-center/src/SearchIndexService.cpp", r'''#include "SearchIndexService.h"

#include <QDir>
#include <QDirIterator>
#include <QFileInfo>

QVariantList SearchIndexService::searchProjects(const QString &rootPath, const QString &query, int limit) const
{
    QVariantList out;
    const QString root = QDir::cleanPath(QDir::fromNativeSeparators(rootPath));
    const QFileInfo rootInfo(root);
    if (!rootInfo.exists() || !rootInfo.isDir()) return out;

    const QString needle = query.trimmed();
    const int boundedLimit = qBound(1, limit, 250);
    int scanned = 0;
    QDirIterator it(root, QDir::AllEntries | QDir::NoDotAndDotDot, QDirIterator::Subdirectories);
    while (it.hasNext() && out.size() < boundedLimit && scanned < 5000) {
        const QString path = it.next();
        ++scanned;
        const QFileInfo info(path);
        if (info.isSymLink()) continue;
        if (!needle.isEmpty() && !info.fileName().contains(needle, Qt::CaseInsensitive)
            && !path.contains(needle, Qt::CaseInsensitive)) continue;
        QVariantMap row;
        row.insert(QStringLiteral("name"), info.fileName());
        row.insert(QStringLiteral("path"), path);
        row.insert(QStringLiteral("type"), info.isDir() ? QStringLiteral("directory") : QStringLiteral("file"));
        out.push_back(row);
    }
    return out;
}

QVariantMap SearchIndexService::conversationIndexStatus() const
{
    return {
        {QStringLiteral("available"), false},
        {QStringLiteral("reason"), QStringLiteral("NO_CANONICAL_CONVERSATION_INDEX_ADAPTER")},
        {QStringLiteral("detail"), QStringLiteral("Conversation search remains unavailable until a canonical read-only conversation index adapter is materialized.")}
    };
}
''')

# ---- QML pages ------------------------------------------------------------
write("apps/fa3-control-center/qml/SearchPage.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property var settings
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language

    property var results: []
    property var conversationStatus: fa3SearchIndex.conversationIndexStatus()
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    function runSearch() {
        if (scope.currentIndex === 0) {
            results = repository.searchRecords(query.text.trim())
        } else if (scope.currentIndex === 1) {
            results = fa3SearchIndex.searchProjects(settings.value("paths/projects", ""), query.text.trim(), 100)
        } else {
            results = []
            conversationStatus = fa3SearchIndex.conversationIndexStatus()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14
        Label { text: root.t("Keresés", "Search"); font.pixelSize: root.px(24); font.bold: true }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("Szolgáltatások, projektek és — canonical adapter rendelkezésre állásakor — beszélgetések read-only keresése.", "Read-only search across services, projects and — when a canonical adapter is available — conversations.") }
        RowLayout {
            Layout.fillWidth: true
            ComboBox { id: scope; model: [root.t("Szolgáltatás", "Service"), root.t("Projekt", "Project"), root.t("Beszélgetés", "Conversation")]; onActivated: root.runSearch() }
            TextField { id: query; Layout.fillWidth: true; placeholderText: root.t("Keresési kifejezés…", "Search…"); onAccepted: root.runSearch() }
            Button { text: root.t("Keresés", "Search"); onClicked: root.runSearch() }
        }
        Rectangle {
            visible: scope.currentIndex === 2 && !root.conversationStatus.available
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            radius: 8
            color: root.surface1
            Column { anchors.fill: parent; anchors.margins: 12; spacing: 5
                Label { text: root.t("Beszélgetés-keresés nem érhető el", "Conversation search unavailable"); font.bold: true }
                Label { width: parent.width; wrapMode: Text.WordWrap; color: root.textMuted; text: root.conversationStatus.reason + " — " + root.conversationStatus.detail }
            }
        }
        ScrollView {
            visible: scope.currentIndex !== 2
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width
                spacing: 8
                Repeater {
                    model: root.results
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        radius: 8
                        color: root.surface1
                        RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 10
                            ColumnLayout { Layout.fillWidth: true
                                Label { Layout.fillWidth: true; font.bold: true; elide: Text.ElideRight; text: modelData.id || modelData.name || "—" }
                                Label { Layout.fillWidth: true; color: root.textMuted; elide: Text.ElideMiddle; text: modelData.title || modelData.path || modelData.category || "" }
                            }
                            Label { text: modelData.status || modelData.type || "READ"; color: root.accent }
                        }
                    }
                }
            }
        }
    }
}
''')

write("apps/fa3-control-center/qml/StarterModelsPage.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    property string lastDraft: ""
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }
    property var starterRoles: [
        { id: "GENERAL_CHAT_LLM", title: "General / Chat LLM", note: "general assistant and chat baseline" },
        { id: "CODING_REASONING_LLM", title: "Coding / Reasoning LLM", note: "coding and structured reasoning" },
        { id: "EMBEDDING_MODEL", title: "Embedding", note: "RAG / semantic index baseline" },
        { id: "VISION_MULTIMODAL", title: "Vision / Multimodal", note: "image-language understanding" },
        { id: "IMAGE_GENERATION_BASE", title: "Image generation base", note: "local image generation baseline" },
        { id: "SPEECH_TO_TEXT", title: "Speech-to-text", note: "local transcription baseline" },
        { id: "TEXT_TO_SPEECH", title: "Text-to-speech", note: "local speech synthesis baseline" }
    ]

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14
        Label { text: root.t("Starter modellek", "Starter Models"); font.pixelSize: root.px(24); font.bold: true }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("Minimális logikai modell-szerepek. A gomb nem tölt le közvetlenül: Model Manager acquisition draftot hoz létre; llmfit finomíthatja a hardware-fit választást, és production admission előtt kötelező a Model Artifact Security lánc.", "Minimal logical model roles. Buttons do not bypass acquisition: they create Model Manager acquisition drafts; llmfit may refine hardware fit and Model Artifact Security remains mandatory before production admission.") }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth
            Flow { width: parent.width; spacing: 12
                Repeater { model: root.starterRoles
                    delegate: Rectangle { required property var modelData; width: 300; height: 150; radius: 10; color: root.surface1
                        ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 7
                            Label { Layout.fillWidth: true; text: modelData.title; font.bold: true; font.pixelSize: root.px(16) }
                            Label { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData.note; color: root.textMuted; wrapMode: Text.WordWrap }
                            Button { text: root.t("Letöltési kérelem", "Request download"); onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_STARTER_MODEL", modelData.id, "Starter model acquisition; provider/model revision chosen through Model Manager + llmfit fit + security admission.") }
                        }
                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""; color: root.accent; elide: Text.ElideMiddle }
    }
}
''')

write("apps/fa3-control-center/qml/CivitaiPanel.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property var repository
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    property string lastDraft: ""
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }
    property var credential: fa3SecretBroker.credentialStatus("civitai")

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true
                Label { text: "CivitAI"; font.pixelSize: root.px(22); font.bold: true }
                Label { text: "FA3-PROVIDER-CIVITAI-001 · Model Manager provider projection"; color: root.textMuted }
            }
            Label { text: root.credential.available ? "AUTH READY" : "PUBLIC / NO TOKEN"; color: root.accent; font.bold: true }
        }
        RowLayout { Layout.fillWidth: true
            TextField { id: search; Layout.fillWidth: true; placeholderText: root.t("CivitAI modellek keresése…", "Search CivitAI models…"); onAccepted: civitaiClient.searchModels(text) }
            Button { text: civitaiClient.busy ? root.t("Betöltés…", "Loading…") : root.t("Keresés", "Search"); enabled: !civitaiClient.busy; onClicked: civitaiClient.searchModels(search.text) }
        }
        Label { Layout.fillWidth: true; visible: civitaiClient.errorText.length > 0; color: "#d99b32"; text: civitaiClient.errorText; wrapMode: Text.WordWrap }
        Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WordWrap; text: root.t("A CivitAI pickle/virus scan státusza upstream metadata, nem FA3 security PASS. Letöltési admission előtt SHA-256, licenc/provenance review és Model Artifact Security szükséges.", "CivitAI pickle/virus scan status is upstream metadata, not FA3 security PASS. SHA-256, license/provenance review and Model Artifact Security are required before download admission.") }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth
            ColumnLayout { width: parent.width; spacing: 8
                Repeater { model: civitaiClient.models
                    delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 124; radius: 8; color: root.surface1
                        RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 12
                            ColumnLayout { Layout.fillWidth: true
                                Label { Layout.fillWidth: true; text: modelData.name + (modelData.versionName ? " · " + modelData.versionName : ""); font.bold: true; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: (modelData.type || "") + " · " + (modelData.creator || ""); color: root.textMuted; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: "SHA-256: " + (modelData.sha256 || "MISSING"); color: modelData.sha256 && modelData.sha256.length === 64 ? root.accent : "#d99b32"; font.family: "monospace"; elide: Text.ElideMiddle }
                                Label { Layout.fillWidth: true; text: "Upstream scans: pickle=" + (modelData.pickleScanResult || "unknown") + " · virus=" + (modelData.virusScanResult || "unknown"); color: root.textMuted }
                            }
                            Button { text: root.t("Acquisition draft", "Acquisition draft"); enabled: modelData.sha256 && modelData.sha256.length === 64 && modelData.downloadUrl; onClicked: root.lastDraft = root.repository.createDraftChangeSet("model-manager", "ACQUIRE_CIVITAI_MODEL", "civitai:" + modelData.id + ":" + modelData.versionId + ":" + modelData.fileName, "CivitAI staged acquisition; expected SHA256=" + modelData.sha256 + "; upstream scan metadata is non-authoritative; license/provenance/security admission required.") }
                        }
                    }
                }
            }
        }
        Label { Layout.fillWidth: true; text: root.lastDraft.length ? root.t("Draft: ", "Draft: ") + root.lastDraft : ""; color: root.accent; elide: Text.ElideMiddle }
    }
}
''')

write("apps/fa3-control-center/qml/OpenModelDbPanel.qml", r'''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property color surface1
    required property color textMuted
    required property color accent
    required property real fontScale
    required property string language
    function t(hu, en) { return language === "en" ? en : hu }
    function px(v) { return Math.max(9, Math.round(v * fontScale)) }

    Component.onCompleted: if (openModelDbService.catalogStatus === "NOT_LOADED") openModelDbService.refreshCatalog()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 12
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true
                Label { text: "OpenModelDB"; font.pixelSize: root.px(22); font.bold: true }
                Label { text: "FA3-PROVIDER-OPENMODELDB-001 · staged SHA-256 acquisition"; color: root.textMuted }
            }
            Label { text: openModelDbService.catalogStatus; color: root.accent }
            Button { text: root.t("Frissítés", "Refresh"); enabled: !openModelDbService.catalogBusy; onClicked: openModelDbService.refreshCatalog() }
        }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.textMuted; text: root.t("A letöltések staging területre érkeznek, SHA-256 ellenőrzéssel. A staging siker nem production admission; provenance/licenc/security gate továbbra is szükséges.", "Downloads land in staging with SHA-256 verification. Successful staging is not production admission; provenance/license/security gates remain required.") }
        SplitView { Layout.fillWidth: true; Layout.fillHeight: true
            ScrollView { SplitView.fillWidth: true; SplitView.preferredWidth: 760; contentWidth: availableWidth
                ColumnLayout { width: parent.width; spacing: 8
                    Repeater { model: openModelDbService.models
                        delegate: Rectangle { required property var modelData; Layout.fillWidth: true; Layout.preferredHeight: 130; radius: 8; color: root.surface1
                            RowLayout { anchors.fill: parent; anchors.margins: 12; spacing: 12
                                ColumnLayout { Layout.fillWidth: true
                                    Label { Layout.fillWidth: true; text: modelData.name; font.bold: true; elide: Text.ElideRight }
                                    Label { text: modelData.author + " · " + modelData.license; color: root.textMuted }
                                    Label { Layout.fillWidth: true; text: modelData.resources.length ? (modelData.resources[0].label + " · SHA256 " + (modelData.resources[0].sha256 || "MISSING")) : root.t("Nincs resource", "No resource"); color: root.textMuted; elide: Text.ElideMiddle }
                                }
                                Button { text: root.t("Staging letöltés", "Stage download"); enabled: modelData.resources.length > 0 && modelData.resources[0].sha256 && modelData.resources[0].sha256.length === 64; onClicked: openModelDbService.queueDownload(modelData.id, modelData.name, modelData.license, modelData.resources[0]) }
                            }
                        }
                    }
                }
            }
            Rectangle { SplitView.preferredWidth: 360; SplitView.minimumWidth: 280; color: root.surface1; radius: 8
                ColumnLayout { anchors.fill: parent; anchors.margins: 12; spacing: 8
                    Label { text: root.t("Letöltési sor", "Download queue"); font.bold: true }
                    Label { Layout.fillWidth: true; color: root.textMuted; elide: Text.ElideMiddle; text: openModelDbService.stagingRoot }
                    ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: openModelDbService.downloads
                        delegate: ItemDelegate { required property var modelData; width: ListView.view.width; text: (modelData.model_name || modelData.id || "download") + " · " + (modelData.status || "") }
                    }
                }
            }
        }
    }
}
''')

# ---- canonical decision + gate ------------------------------------------
decision = {
    "schema": "fa3.decision-record.v1",
    "id": "FA3-DEC-GUI-CATALOG-SEARCH-STARTER-2026-09-13",
    "date": "2026-09-13",
    "status": "CANONICAL_CLOSED",
    "subject": "Unified GUI search, starter-model bootstrap, catalog providers, credential projection and area visibility",
    "decision": "MATERIALIZE",
    "profile_id": "FA3-DESKTOP-001",
    "new_capabilities": 0,
    "new_architectural_authorities": 0,
    "capability_count_after": 143,
    "bindings": {
        "token_governance": "FA3-TOKEN-GOVERNANCE-001",
        "secret_broker": "FA3-SECRET-BROKER-001",
        "civitai": "FA3-PROVIDER-CIVITAI-001",
        "openmodeldb": "FA3-PROVIDER-OPENMODELDB-001",
        "model_manager": "FA3-MODEL-MANAGER-001"
    },
    "mandatory_constraints": [
        "SEARCH_IS_PRIMARY_NAVIGATION",
        "SEARCH_SCOPES_SERVICE_PROJECT_CONVERSATION",
        "CONVERSATION_SEARCH_FAILS_CLOSED_WITHOUT_CANONICAL_INDEX_ADAPTER",
        "STARTER_MODELS_IS_PRIMARY_NAVIGATION",
        "STARTER_ACQUISITION_USES_MODEL_MANAGER_AND_MODEL_ARTIFACT_SECURITY",
        "CIVITAI_AND_OPENMODELDB_LIVE_UNDER_MODEL_MANAGER",
        "CIVITAI_UPSTREAM_SCAN_METADATA_IS_NOT_FA3_SECURITY_PASS",
        "AREA_VISIBILITY_IS_QSETTINGS_UI_ONLY",
        "HIDDEN_AREA_DOES_NOT_DISABLE_CANONICAL_CAPABILITY_OR_AUTHORITY",
        "RAW_SECRET_VALUES_NEVER_PERSIST_IN_QSETTINGS_REPO_LOG_TELEMETRY_EVIDENCE_EXPORT_URL_OR_WEB_DOM",
        "KWALLET_IS_OPTIONAL_AND_NEVER_REQUIRED"
    ]
}
write("canonical/decisions/FA3-DEC-GUI-CATALOG-SEARCH-STARTER-2026-09-13.json", json.dumps(decision, indent=2, ensure_ascii=False) + "\n")

gate = {
    "schema": "fa3.gate-record.v1",
    "id": "FA3-GATE-GUI-CATALOG-SEARCH-STARTER-001",
    "status": "CANONICAL",
    "priority": "P0",
    "requirement": "MUST",
    "decision": decision["id"],
    "fail_closed": True,
    "capability_count": 143,
    "new_capability": False,
    "new_architectural_authority": False,
    "checks": [
        "SEARCH_PRIMARY_NAV_PRESENT", "SEARCH_THREE_SCOPES_PRESENT", "CONVERSATION_SEARCH_FAIL_CLOSED",
        "STARTER_MODELS_PRIMARY_NAV_PRESENT", "STARTER_DOWNLOAD_USES_TYPED_ACQUISITION_DRAFT",
        "CIVITAI_MODEL_MANAGER_PANEL_PRESENT", "OPENMODELDB_MODEL_MANAGER_PANEL_PRESENT",
        "AREA_VISIBILITY_UI_ONLY_PRESENT", "TOKEN_SECRETREF_BOUNDARY_PRESENT", "KWALLET_NOT_REQUIRED",
        "CIVITAI_BEARER_HEADER_NOT_QUERY_TOKEN", "OPENMODELDB_SHA256_STAGING_PRESENT"
    ]
}
write("canonical/FA3-GATE-GUI-CATALOG-SEARCH-STARTER-001.json", json.dumps(gate, indent=2) + "\n")

# ---- executable gate/test ------------------------------------------------
write("src/fa3_gui_catalog_search_starter_gate.py", r'''#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def text(path): return (ROOT / path).read_text(encoding="utf-8")

def validate():
    failures=[]
    decision=json.loads(text("canonical/decisions/FA3-DEC-GUI-CATALOG-SEARCH-STARTER-2026-09-13.json"))
    gate=json.loads(text("canonical/FA3-GATE-GUI-CATALOG-SEARCH-STARTER-001.json"))
    shell=text("apps/fa3-control-center/qml/AppShell.qml")
    settings=text("apps/fa3-control-center/qml/SettingsPage.qml")
    model=text("apps/fa3-control-center/qml/ModelManagerPage.qml")
    search=text("apps/fa3-control-center/qml/SearchPage.qml")
    starter=text("apps/fa3-control-center/qml/StarterModelsPage.qml")
    civcpp=text("apps/fa3-control-center/src/CivitaiClient.cpp")
    civqml=text("apps/fa3-control-center/qml/CivitaiPanel.qml")
    omdb=text("apps/fa3-control-center/src/OpenModelDbService.cpp")
    secret_h=text("apps/fa3-control-center/src/SecretBrokerService.h")
    secret_cpp=text("apps/fa3-control-center/src/SecretBrokerService.cpp")
    cmake=text("apps/fa3-control-center/CMakeLists.txt")
    checks=[
        (decision.get("capability_count_after")==143,"capability-count"),
        (decision.get("new_architectural_authorities")==0,"no-new-authority"),
        (gate.get("fail_closed") is True,"fail-closed"),
        ('{ key: "search"' in shell and '{ key: "starterModels"' in shell,"primary-nav"),
        ('Szolgáltatás' in search and 'Projekt' in search and 'Beszélgetés' in search,"search-three-scopes"),
        ('NO_CANONICAL_CONVERSATION_INDEX_ADAPTER' in text("apps/fa3-control-center/src/SearchIndexService.cpp"),"conversation-fail-closed"),
        ('ACQUIRE_STARTER_MODEL' in starter and 'createDraftChangeSet' in starter,"starter-gated-acquisition"),
        ('["civitai", "CivitAI"]' in model and '["openmodeldb", "OpenModelDB"]' in model,"model-manager-catalogs"),
        ('areas/searchVisible' in settings and 'areas/starterModelsVisible' in settings and 'areaVisible' in shell,"area-visibility"),
        ('Tokenek & hozzáférések' in settings and 'fa3SecretBroker' in settings,"credentials-ui"),
        ('kwalletRequired() const { return false; }' in secret_h and 'KWallet (optional)' in secret_cpp,"kwallet-optional"),
        ('Authorization' in civcpp and 'Bearer ' in civcpp,"civitai-bearer"),
        ('query.addQueryItem(QStringLiteral("token")' not in civcpp and 'apiKey' not in civcpp,"civitai-no-query-secret"),
        ('upstream metadata' in civqml and 'not FA3 security PASS' in civqml,"civitai-scan-nonauthoritative"),
        ('QCryptographicHash::Sha256' in omdb or 'Sha256' in omdb,"openmodeldb-sha256"),
        ('KWALLET' not in cmake and 'KF6Wallet' not in cmake,"no-kwallet-build-dependency"),
        ('Qt.openUrlExternally' not in civqml and 'Qt.openUrlExternally' not in text("apps/fa3-control-center/qml/OpenModelDbPanel.qml"),"no-external-ai-browser"),
        ('m_sessionSecrets' in secret_cpp and 'settings.setValue' not in secret_cpp.split('setSessionSecret',1)[1].split('clearSessionSecret',1)[0],"session-secret-not-qsettings"),
    ]
    failures += [name for ok,name in checks if not ok]
    return failures

if __name__ == "__main__":
    failures=validate()
    if failures:
        print("FA3 GUI catalog/search/starter gate: FAIL")
        for f in failures: print(" -",f)
        raise SystemExit(1)
    print("FA3 GUI catalog/search/starter gate: PASS")
''')

write("tests/test_fa3_gui_catalog_search_starter_gate.py", r'''import unittest
from src.fa3_gui_catalog_search_starter_gate import validate

class TestFa3GuiCatalogSearchStarterGate(unittest.TestCase):
    def test_gate(self):
        self.assertEqual(validate(), [])

if __name__ == "__main__":
    unittest.main()
''')

# ---- patch CMake/main -----------------------------------------------------
replace_once(
    "apps/fa3-control-center/CMakeLists.txt",
    "    src/JournalReader.cpp\n    src/JournalReader.h\n)",
    "    src/JournalReader.cpp\n    src/JournalReader.h\n    src/SecretBrokerService.cpp\n    src/SecretBrokerService.h\n    src/OpenModelDbService.cpp\n    src/OpenModelDbService.h\n    src/CivitaiClient.cpp\n    src/CivitaiClient.h\n    src/SearchIndexService.cpp\n    src/SearchIndexService.h\n)",
    "src/CivitaiClient.cpp",
)
replace_once(
    "apps/fa3-control-center/CMakeLists.txt",
    "set_source_files_properties(qml/LlmfitPanel.qml PROPERTIES QT_RESOURCE_ALIAS LlmfitPanel.qml)\n",
    "set_source_files_properties(qml/LlmfitPanel.qml PROPERTIES QT_RESOURCE_ALIAS LlmfitPanel.qml)\nset_source_files_properties(qml/SearchPage.qml PROPERTIES QT_RESOURCE_ALIAS SearchPage.qml)\nset_source_files_properties(qml/StarterModelsPage.qml PROPERTIES QT_RESOURCE_ALIAS StarterModelsPage.qml)\nset_source_files_properties(qml/CivitaiPanel.qml PROPERTIES QT_RESOURCE_ALIAS CivitaiPanel.qml)\nset_source_files_properties(qml/OpenModelDbPanel.qml PROPERTIES QT_RESOURCE_ALIAS OpenModelDbPanel.qml)\n",
    "QT_RESOURCE_ALIAS SearchPage.qml",
)
replace_once(
    "apps/fa3-control-center/CMakeLists.txt",
    "        qml/LlmfitPanel.qml\n)",
    "        qml/LlmfitPanel.qml\n        qml/SearchPage.qml\n        qml/StarterModelsPage.qml\n        qml/CivitaiPanel.qml\n        qml/OpenModelDbPanel.qml\n)",
    "        qml/SearchPage.qml",
)

replace_once(
    "apps/fa3-control-center/src/main.cpp",
    '#include "JournalReader.h"\n',
    '#include "JournalReader.h"\n#include "SecretBrokerService.h"\n#include "OpenModelDbService.h"\n#include "CivitaiClient.h"\n#include "SearchIndexService.h"\n',
    '#include "SecretBrokerService.h"',
)
replace_once(
    "apps/fa3-control-center/src/main.cpp",
    "    JournalReader journal;\n",
    "    JournalReader journal;\n    SecretBrokerService secretBroker;\n    OpenModelDbService openModelDb;\n    CivitaiClient civitai(&secretBroker);\n    SearchIndexService searchIndex;\n",
    "    SecretBrokerService secretBroker;",
)
replace_once(
    "apps/fa3-control-center/src/main.cpp",
    '    engine.rootContext()->setContextProperty("fa3Journal", &journal);\n',
    '    engine.rootContext()->setContextProperty("fa3Journal", &journal);\n    engine.rootContext()->setContextProperty("fa3SecretBroker", &secretBroker);\n    engine.rootContext()->setContextProperty("openModelDbService", &openModelDb);\n    engine.rootContext()->setContextProperty("civitaiClient", &civitai);\n    engine.rootContext()->setContextProperty("fa3SearchIndex", &searchIndex);\n',
    'setContextProperty("fa3SecretBroker"',
)

# ---- patch AppShell -------------------------------------------------------
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    "    function navigateTo(index, remember) {\n        const keepHistory = remember === undefined ? true : remember\n        if (index < 0 || index >= navigationModel.length || index === selectedIndex)\n            return\n",
    "    function navigateTo(index, remember) {\n        const keepHistory = remember === undefined ? true : remember\n        if (index < 0 || index >= navigationModel.length || index === selectedIndex)\n            return\n        if (!areaVisible(navigationModel[index].key))\n            return\n",
    "!areaVisible(navigationModel[index].key)",
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    "    function toggleSidebar() {\n        sidebarCollapsed = !sidebarCollapsed\n        fa3Settings.setValue(\"appearance/sidebarCollapsed\", sidebarCollapsed)\n    }\n\n",
    "    function toggleSidebar() {\n        sidebarCollapsed = !sidebarCollapsed\n        fa3Settings.setValue(\"appearance/sidebarCollapsed\", sidebarCollapsed)\n    }\n\n    function areaVisible(key) {\n        if (key === \"command\" || key === \"settings\")\n            return true\n        return fa3Settings.value(\"areas/\" + key + \"Visible\", true)\n    }\n\n",
    "function areaVisible(key)",
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    '            modelManager: ["Model Manager", "Model Manager"],\n            architecture:',
    '            modelManager: ["Model Manager", "Model Manager"],\n            search: ["Keresés", "Search"],\n            starterModels: ["Starter modellek", "Starter Models"],\n            architecture:',
    'starterModels: ["Starter modellek"',
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    '        { key: "modelManager", iconText: "◫" },\n        { key: "architecture",',
    '        { key: "modelManager", iconText: "◫" },\n        { key: "search", iconText: "⌕" },\n        { key: "starterModels", iconText: "↓" },\n        { key: "architecture",',
    '{ key: "starterModels"',
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    "        function onSettingChanged(key) {\n            if (key.indexOf(\"shortcuts/\") === 0)\n                window.shortcutRevision += 1\n        }",
    "        function onSettingChanged(key) {\n            if (key.indexOf(\"shortcuts/\") === 0)\n                window.shortcutRevision += 1\n            if (key.indexOf(\"areas/\") === 0 && !window.areaVisible(window.navigationModel[window.selectedIndex].key))\n                window.selectedIndex = window.indexForKey(\"command\")\n        }",
    'key.indexOf("areas/")',
)
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    "                        width: ListView.view.width\n                        height: Math.round(44 * window.uiScale)\n                        highlighted:",
    "                        width: ListView.view.width\n                        visible: window.areaVisible(modelData.key)\n                        height: visible ? Math.round(44 * window.uiScale) : 0\n                        highlighted:",
    "visible: window.areaVisible(modelData.key)",
)
model_block = '''            ModelManagerPage {
                repository: fa3Repository
                surface1: window.surface1
                surface2: window.surface2
                textPrimary: window.textPrimary
                textMuted: window.textMuted
                accent: window.accent
                uiScale: window.uiScale
                fontScale: window.fontScale
                language: fa3Settings.language
            }
'''
replace_once(
    "apps/fa3-control-center/qml/AppShell.qml",
    model_block,
    model_block + '''
            SearchPage {
                repository: fa3Repository
                settings: fa3Settings
                surface1: window.surface1
                textMuted: window.textMuted
                accent: window.accent
                fontScale: window.fontScale
                language: fa3Settings.language
            }

            StarterModelsPage {
                repository: fa3Repository
                surface1: window.surface1
                textMuted: window.textMuted
                accent: window.accent
                fontScale: window.fontScale
                language: fa3Settings.language
            }
''',
    "            SearchPage {",
)

# ---- patch Settings -------------------------------------------------------
replace_once(
    "apps/fa3-control-center/qml/SettingsPage.qml",
    '        ["appearance", t("Megjelenés", "Appearance")],\n        ["locale",',
    '        ["appearance", t("Megjelenés", "Appearance")],\n        ["areas", t("Területek", "Areas")],\n        ["locale",',
    '["areas", t("Területek"',
)
replace_once(
    "apps/fa3-control-center/qml/SettingsPage.qml",
    '        ["shortcuts", t("Gyorsbillentyűk", "Shortcuts")],\n        ["integrations",',
    '        ["shortcuts", t("Gyorsbillentyűk", "Shortcuts")],\n        ["credentials", t("Tokenek & hozzáférések", "Tokens & Credentials")],\n        ["integrations",',
    '["credentials", t("Tokenek & hozzáférések"',
)
areas_page = r'''            ScrollView {
                id: areasView
                contentWidth: availableWidth
                ColumnLayout {
                    width: areasView.availableWidth; spacing: 12
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: root.t("Területek", "Areas"); subtitle: root.t("A fő felületek láthatósága. Ez kizárólag helyi UI-preferencia: elrejtés nem tilt le canonical capability-t, providert vagy authority-t.", "Visibility of major surfaces. This is a local UI preference only: hiding a surface never disables a canonical capability, provider or authority.") }
                    Card { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.preferredHeight: Math.round(570 * root.uiScale)
                        GridLayout { anchors.fill: parent; anchors.margins: 18; columns: 2; rowSpacing: 8; columnSpacing: 24
                            Label { text: root.t("Mindig látható", "Always visible") }
                            Label { text: "Command Center · Settings"; color: root.accent }
                            Label { text: root.t("Projektek", "Projects") }
                            Switch { checked: root.settings.value("areas/projectsVisible", true); onToggled: root.settings.setValue("areas/projectsVisible", checked) }
                            Label { text: "AI Studio" }
                            Switch { checked: root.settings.value("areas/studioVisible", true); onToggled: root.settings.setValue("areas/studioVisible", checked) }
                            Label { text: root.t("AI alkalmazások", "AI Applications") }
                            Switch { checked: root.settings.value("areas/aiAppsVisible", true); onToggled: root.settings.setValue("areas/aiAppsVisible", checked) }
                            Label { text: root.t("Agentek & Workflow-k", "Agents & Workflows") }
                            Switch { checked: root.settings.value("areas/agentsVisible", true); onToggled: root.settings.setValue("areas/agentsVisible", checked) }
                            Label { text: "Model Manager" }
                            Switch { checked: root.settings.value("areas/modelManagerVisible", true); onToggled: root.settings.setValue("areas/modelManagerVisible", checked) }
                            Label { text: root.t("Keresés", "Search") }
                            Switch { checked: root.settings.value("areas/searchVisible", true); onToggled: root.settings.setValue("areas/searchVisible", checked) }
                            Label { text: root.t("Starter modellek", "Starter Models") }
                            Switch { checked: root.settings.value("areas/starterModelsVisible", true); onToggled: root.settings.setValue("areas/starterModelsVisible", checked) }
                            Label { text: root.t("Architektúra", "Architecture") }
                            Switch { checked: root.settings.value("areas/architectureVisible", true); onToggled: root.settings.setValue("areas/architectureVisible", checked) }
                            Label { text: root.t("Erőforrások", "Resources") }
                            Switch { checked: root.settings.value("areas/resourcesVisible", true); onToggled: root.settings.setValue("areas/resourcesVisible", checked) }
                            Label { text: root.t("Biztonság", "Security") }
                            Switch { checked: root.settings.value("areas/securityVisible", true); onToggled: root.settings.setValue("areas/securityVisible", checked) }
                            Label { text: "Observability" }
                            Switch { checked: root.settings.value("areas/observabilityVisible", true); onToggled: root.settings.setValue("areas/observabilityVisible", checked) }
                            Label { text: "Evidence" }
                            Switch { checked: root.settings.value("areas/evidenceVisible", true); onToggled: root.settings.setValue("areas/evidenceVisible", checked) }
                            Label { text: root.t("Integrációk", "Integrations") }
                            Switch { checked: root.settings.value("areas/integrationsVisible", true); onToggled: root.settings.setValue("areas/integrationsVisible", checked) }
                            Label { text: root.t("Rendszer", "System") }
                            Switch { checked: root.settings.value("areas/systemVisible", true); onToggled: root.settings.setValue("areas/systemVisible", checked) }
                        }
                    }
                }
            }

'''
replace_once(
    "apps/fa3-control-center/qml/SettingsPage.qml",
    "            ScrollView {\n                id: localeView\n",
    areas_page + "            ScrollView {\n                id: localeView\n",
    "                id: areasView",
)
credentials_page = r'''            ScrollView {
                id: credentialsView
                contentWidth: availableWidth
                ColumnLayout {
                    width: credentialsView.availableWidth; spacing: 14
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: root.t("Tokenek & hozzáférések", "Tokens & Credentials"); subtitle: root.t("Credential SecretRef-kezelés. Nyers token nem kerül QSettings-be, repositoryba, logba, telemetrybe vagy Evidence-be. KWallet opcionális, soha nem kötelező.", "Credential SecretRef management. Raw tokens never persist in QSettings, repository, logs, telemetry or Evidence. KWallet is optional and never required.") }
                    Card { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.preferredHeight: Math.round(370 * root.uiScale)
                        ColumnLayout { anchors.fill: parent; anchors.margins: 18; spacing: 10
                            Label { text: "CivitAI"; font.pixelSize: root.px(17); font.bold: true }
                            Label { Layout.fillWidth: true; color: root.textMuted; wrapMode: Text.WordWrap; text: "Secret Broker: " + fa3SecretBroker.statusText + " · KWallet required=" + fa3SecretBroker.kwalletRequired }
                            RowLayout { Layout.fillWidth: true
                                TextField { id: civitaiToken; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: root.t("Ideiglenes session token (nem mentjük)", "Temporary session token (not persisted)") }
                                Button { text: root.t("Session token beállítása", "Set session token"); enabled: civitaiToken.text.length > 0; onClicked: { fa3SecretBroker.setSessionSecret("civitai", civitaiToken.text); civitaiToken.clear() } }
                                Button { text: root.t("Törlés", "Clear"); onClicked: fa3SecretBroker.clearSessionSecret("civitai") }
                            }
                            Label { Layout.fillWidth: true; color: root.textMuted; text: root.t("Alternatíva: CIVITAI_API_TOKEN környezeti referencia vagy más SecretRef backend.", "Alternative: CIVITAI_API_TOKEN environment reference or another SecretRef backend.") }
                            RowLayout { Layout.fillWidth: true
                                ComboBox { id: backend; model: ["ENVIRONMENT_REFERENCE", "SYSTEMD_CREDENTIAL", "EXTERNAL_SECRETREF", "OPENBAO", "OS_KEYCHAIN", "KWALLET"] }
                                TextField { id: referenceId; Layout.fillWidth: true; placeholderText: root.t("Referencia azonosító / env név / credential név", "Reference id / env name / credential name") }
                                Button { text: root.t("Referencia mentése", "Save reference"); enabled: referenceId.text.trim().length > 0; onClicked: fa3SecretBroker.configureReference("civitai", backend.currentText, referenceId.text.trim(), "CivitAI") }
                            }
                            Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; color: root.accent; text: root.t("KWallet: opcionális adapter. Hiánya nem blokkolhat buildet, telepítést vagy runtime-ot.", "KWallet: optional adapter. Its absence must not block build, installation or runtime.") }
                        }
                    }
                }
            }

'''
replace_once(
    "apps/fa3-control-center/qml/SettingsPage.qml",
    "            ScrollView {\n                id: integrationsView\n",
    credentials_page + "            ScrollView {\n                id: integrationsView\n",
    "                id: credentialsView",
)

# ---- patch Model Manager --------------------------------------------------
replace_once(
    "apps/fa3-control-center/qml/ModelManagerPage.qml",
    '        ["providers", "Providers"],\n        ["runtime",',
    '        ["providers", "Providers"],\n        ["civitai", "CivitAI"],\n        ["openmodeldb", "OpenModelDB"],\n        ["runtime",',
    '["civitai", "CivitAI"]',
)
providers_block = '''            ScrollView {
                id: providersView
                contentWidth: availableWidth
                ColumnLayout {
                    width: providersView.availableWidth
                    spacing: 12
                    Item { Layout.preferredHeight: 20 }
                    TitleBlock { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; title: "Providers"; subtitle: root.t("Canonical provider projection", "Canonical provider projection") }
                    RecordList { Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; records: root.providerRecords() }
                }
            }
'''
replace_once(
    "apps/fa3-control-center/qml/ModelManagerPage.qml",
    providers_block,
    providers_block + '''
            CivitaiPanel {
                repository: root.repository
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }

            OpenModelDbPanel {
                surface1: root.surface1
                textMuted: root.textMuted
                accent: root.accent
                fontScale: root.fontScale
                language: root.language
            }
''',
    "            CivitaiPanel {",
)

# ---- patch legacy GUI gate + workflow ------------------------------------
replace_once(
    "src/fa3_gui_gate.py",
    '    "Model Manager", "Architecture", "Resources", "Security & Approvals", "Observability",\n',
    '    "Model Manager", "Search", "Starter Models", "Architecture", "Resources", "Security & Approvals", "Observability",\n',
    '"Starter Models", "Architecture"',
)
replace_once(
    "src/fa3_gui_gate.py",
    '    "Megjelenés", "Language & Region", "Paths & Libraries", "Gyorsbillentyűk",\n',
    '    "Megjelenés", "Területek", "Language & Region", "Paths & Libraries", "Gyorsbillentyűk", "Tokenek & hozzáférések",\n',
    '"Területek", "Language & Region"',
)
replace_once(
    ".github/workflows/fa3-gui-gate.yml",
    "      - 'src/fa3_gui_usability_gate.py'\n      - 'tests/test_fa3_gui_gate.py'\n",
    "      - 'src/fa3_gui_usability_gate.py'\n      - 'src/fa3_gui_catalog_search_starter_gate.py'\n      - 'tests/test_fa3_gui_gate.py'\n      - 'tests/test_fa3_gui_catalog_search_starter_gate.py'\n",
    "src/fa3_gui_catalog_search_starter_gate.py",
)
replace_once(
    ".github/workflows/fa3-gui-gate.yml",
    "      - name: Run GUI usability regression gate\n        run: PYTHONPATH=. python src/fa3_gui_usability_gate.py\n      - name: Run GUI unit regression\n        run: PYTHONPATH=. python -m unittest tests.test_fa3_gui_gate -v\n",
    "      - name: Run GUI usability regression gate\n        run: PYTHONPATH=. python src/fa3_gui_usability_gate.py\n      - name: Run catalog/search/starter regression gate\n        run: PYTHONPATH=. python src/fa3_gui_catalog_search_starter_gate.py\n      - name: Run GUI unit regression\n        run: PYTHONPATH=. python -m unittest tests.test_fa3_gui_gate tests.test_fa3_gui_catalog_search_starter_gate -v\n",
    "Run catalog/search/starter regression gate",
)

print("FA3 GUI catalog/search/starter materialization complete")
