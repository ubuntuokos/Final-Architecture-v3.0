#include "HumanizerSettingsService.h"

#include <QDateTime>
#include <QDir>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStandardPaths>
#include <QUuid>

#include <algorithm>

namespace {
const QStringList kEditableScopes{
    QStringLiteral("USER"),
    QStringLiteral("PROJECT"),
    QStringLiteral("APPLICATION"),
    QStringLiteral("MODULE_PLUGIN"),
    QStringLiteral("CAPABILITY"),
    QStringLiteral("FUNCTION")
};

const QStringList kLockedScopes{
    QStringLiteral("GLOBAL"),
    QStringLiteral("HOST"),
    QStringLiteral("USER_ROLE")
};
}

HumanizerSettingsService::HumanizerSettingsService(QObject *parent)
    : QObject(parent),
      m_settings(QSettings::IniFormat, QSettings::UserScope,
                 QStringLiteral("FA3"), QStringLiteral("Humanizer"))
{
    setContext({}, QStringLiteral("FA3-HUMANIZER-STANDALONE-001"), {},
               QStringLiteral("CAP-125"), QStringLiteral("humanizer.workspace"));
}

QString HumanizerSettingsService::fabricState() const
{
    return QStringLiteral("STATIC_GUI_READY_CURRENT_HOST_PENDING");
}

QString HumanizerSettingsService::safeId(const QString &value) const
{
    QString out = value.trimmed();
    out.replace('/', '_');
    out.replace('\\', '_');
    return out.isEmpty() ? QStringLiteral("_") : out;
}

QString HumanizerSettingsService::scopePath(const QString &scope) const
{
    const QString s = scope.trimmed().toUpper();
    if (s == "USER") return QStringLiteral("user");
    if (s == "PROJECT") return QStringLiteral("projects/") + safeId(m_projectId);
    if (s == "APPLICATION") return QStringLiteral("applications/") + safeId(m_applicationId);
    if (s == "MODULE_PLUGIN") return QStringLiteral("modules/") + safeId(m_applicationId) + "/" + safeId(m_moduleId);
    if (s == "CAPABILITY") return QStringLiteral("capabilities/") + safeId(m_capabilityId);
    if (s == "FUNCTION") return QStringLiteral("functions/") + safeId(m_applicationId) + "/" + safeId(m_functionId);
    return {};
}

QVariant HumanizerSettingsService::defaultSetting(const QString &key) const
{
    static const QVariantMap defaults{
        {"enabled", true},
        {"ai_enabled", false},
        {"language", QStringLiteral("hu-HU")},
        {"register_profile", QStringLiteral("Professional")},
        {"edit_budget", QStringLiteral("BALANCED")},
        {"voice_profile", QString()},
        {"preserve_numbers", true},
        {"preserve_urls", true},
        {"preserve_quotes", true},
        {"preserve_citations", true},
        {"preserve_terminology", true},
        {"semantic_validation", true}
    };
    return defaults.value(key);
}

QVariant HumanizerSettingsService::resolvedSetting(const QString &key) const
{
    const QStringList precedence{
        QStringLiteral("FUNCTION"),
        QStringLiteral("CAPABILITY"),
        QStringLiteral("MODULE_PLUGIN"),
        QStringLiteral("APPLICATION"),
        QStringLiteral("PROJECT"),
        QStringLiteral("USER")
    };
    for (const auto &scope : precedence) {
        const QString path = scopePath(scope);
        if (path.isEmpty()) continue;
        const QString settingKey = path + "/" + key;
        if (m_settings.contains(settingKey))
            return m_settings.value(settingKey);
    }
    return defaultSetting(key);
}

QString HumanizerSettingsService::language() const
{
    return resolvedSetting("language").toString();
}

QString HumanizerSettingsService::registerProfile() const
{
    return resolvedSetting("register_profile").toString();
}

QString HumanizerSettingsService::editBudget() const
{
    return resolvedSetting("edit_budget").toString();
}

QString HumanizerSettingsService::voiceProfile() const
{
    return resolvedSetting("voice_profile").toString();
}

bool HumanizerSettingsService::aiEnabled() const
{
    return resolvedSetting("ai_enabled").toBool();
}

bool HumanizerSettingsService::protectNumbers() const
{
    return resolvedSetting("preserve_numbers").toBool();
}

bool HumanizerSettingsService::protectUrls() const
{
    return resolvedSetting("preserve_urls").toBool();
}

bool HumanizerSettingsService::protectQuotes() const
{
    return resolvedSetting("preserve_quotes").toBool();
}

bool HumanizerSettingsService::protectCitations() const
{
    return resolvedSetting("preserve_citations").toBool();
}

QVariantList HumanizerSettingsService::policyLayers() const
{
    return {
        QVariantMap{{"id","GLOBAL"},{"label","Global policy"},{"locked",true}},
        QVariantMap{{"id","HOST"},{"label","Host policy"},{"locked",true}},
        QVariantMap{{"id","USER_ROLE"},{"label","User / role"},{"locked",true}},
        QVariantMap{{"id","PROJECT"},{"label","Project"},{"locked",false}},
        QVariantMap{{"id","APPLICATION"},{"label","Application"},{"locked",false}},
        QVariantMap{{"id","MODULE_PLUGIN"},{"label","Module / plugin"},{"locked",false}},
        QVariantMap{{"id","CAPABILITY"},{"label","Capability"},{"locked",false}},
        QVariantMap{{"id","FUNCTION"},{"label","Function"},{"locked",false}},
        QVariantMap{{"id","USER"},{"label","User default"},{"locked",false}}
    };
}

QVariantList HumanizerSettingsService::languages() const
{
    return {"hu-HU", "en-US", "de-DE", "fr-FR", "es-ES", "MULTILINGUAL"};
}

QVariantList HumanizerSettingsService::registerProfiles() const
{
    return {"Conversational", "Professional", "Technical", "Academic",
            "Journalistic", "Literary", "Screenplay", "Marketing",
            "Legal", "Business", "Documentation", "Email", "Broadcast",
            "Subtitle", "Narration"};
}

QVariantList HumanizerSettingsService::editBudgets() const
{
    return {"PRESERVE", "LIGHT", "BALANCED", "STRONG", "REBUILD"};
}

QVariantMap HumanizerSettingsService::lastAnalysis() const
{
    return m_lastAnalysis;
}

QVariantMap HumanizerSettingsService::lastComparison() const
{
    return m_lastComparison;
}

QString HumanizerSettingsService::lastDraftPath() const
{
    return m_lastDraftPath;
}

void HumanizerSettingsService::setContext(const QString &projectId,
                                          const QString &applicationId,
                                          const QString &moduleId,
                                          const QString &capabilityId,
                                          const QString &functionId)
{
    m_projectId = projectId;
    m_applicationId = applicationId;
    m_moduleId = moduleId;
    m_capabilityId = capabilityId;
    m_functionId = functionId;
    emit settingsChanged();
}

bool HumanizerSettingsService::setPreference(const QString &scope,
                                             const QString &key,
                                             const QVariant &value)
{
    const QString normalized = scope.trimmed().toUpper();
    if (!kEditableScopes.contains(normalized) || kLockedScopes.contains(normalized))
        return false;

    const QString path = scopePath(normalized);
    if (path.isEmpty())
        return false;

    static const QStringList allowedKeys{
        "enabled","ai_enabled","language","register_profile","edit_budget",
        "voice_profile","preserve_numbers","preserve_urls","preserve_quotes",
        "preserve_citations","preserve_terminology","semantic_validation"
    };
    if (!allowedKeys.contains(key))
        return false;

    m_settings.setValue(path + "/" + key, value);
    m_settings.sync();
    if (m_settings.status() != QSettings::NoError)
        return false;
    emit settingsChanged();
    return true;
}

void HumanizerSettingsService::refresh()
{
    m_settings.sync();
    emit settingsChanged();
}

QVariantMap HumanizerSettingsService::analyzeText(const QString &text)
{
    const QString normalized = text.trimmed();
    const QRegularExpression wordRx(
        QStringLiteral(R"(\b[\p{L}\p{N}][\p{L}\p{N}'’_-]*\b)"),
        QRegularExpression::UseUnicodePropertiesOption);
    const auto wordMatches = wordRx.globalMatch(normalized);
    int wordCount = 0;
    QHash<QString,int> firstWordFrequency;
    auto wi = wordMatches;
    while (wi.hasNext()) {
        wi.next();
        ++wordCount;
    }

    QStringList sentences = normalized.split(
        QRegularExpression(QStringLiteral(R"([.!?…]+(?:\s+|$))")),
        Qt::SkipEmptyParts);
    const int sentenceCount = sentences.size();
    for (const auto &sentence : sentences) {
        auto match = wordRx.match(sentence.trimmed());
        if (match.hasMatch()) {
            const QString first = match.captured(0).toCaseFolded();
            firstWordFrequency[first] += 1;
        }
    }

    const QStringList markerPatterns{
        "in conclusion", "it is important to note", "it is worth noting",
        "delve", "tapestry", "leverage", "furthermore", "moreover",
        "összességében", "fontos megjegyezni", "érdemes kiemelni",
        "továbbá", "mindemellett"
    };
    QVariantList foundMarkers;
    for (const auto &marker : markerPatterns) {
        const QRegularExpression rx(QRegularExpression::escape(marker),
                                    QRegularExpression::CaseInsensitiveOption);
        if (normalized.contains(rx))
            foundMarkers << marker;
    }

    QVariantList repeatedStarts;
    for (auto it = firstWordFrequency.cbegin(); it != firstWordFrequency.cend(); ++it) {
        if (it.value() >= 3)
            repeatedStarts << QVariantMap{{"token",it.key()},{"count",it.value()}};
    }

    QVariantList suggestions;
    if (!foundMarkers.isEmpty())
        suggestions << QStringLiteral("Review mechanical or formulaic phrases.");
    if (!repeatedStarts.isEmpty())
        suggestions << QStringLiteral("Vary repeated sentence openings when that does not change intent.");
    if (sentenceCount > 0 && (double(wordCount) / sentenceCount) > 28.0)
        suggestions << QStringLiteral("Review long sentence chains for readability.");

    m_lastAnalysis = {
        {"schema","fa3.humanizer-analysis.v1"},
        {"authoritative",false},
        {"language",language()},
        {"register",registerProfile()},
        {"wordCount",wordCount},
        {"sentenceCount",sentenceCount},
        {"averageSentenceWords", sentenceCount ? double(wordCount) / sentenceCount : 0.0},
        {"mechanicalMarkerCount",foundMarkers.size()},
        {"mechanicalMarkers",foundMarkers},
        {"repeatedSentenceStarts",repeatedStarts},
        {"suggestions",suggestions},
        {"status", (foundMarkers.isEmpty() && repeatedStarts.isEmpty()) ? "PASS" : "REVIEW"}
    };
    emit analysisChanged();
    return m_lastAnalysis;
}

QString HumanizerSettingsService::safeNormalize(const QString &text)
{
    QString out = text;
    out.replace("\r\n", "\n");
    out.replace('\r', '\n');
    out.replace(QRegularExpression(QStringLiteral("[ \\t]+(?=\\n)")), QString());
    out.replace(QRegularExpression(QStringLiteral("[ \\t]{2,}")), QStringLiteral(" "));
    out.replace(QRegularExpression(QStringLiteral("\\n{3,}")), QStringLiteral("\n\n"));
    return out.trimmed();
}

QStringList HumanizerSettingsService::extractMatches(const QString &text,
                                                     const QString &pattern) const
{
    QRegularExpression rx(pattern, QRegularExpression::UseUnicodePropertiesOption);
    QStringList result;
    auto i = rx.globalMatch(text);
    while (i.hasNext())
        result << i.next().captured(0);
    std::sort(result.begin(), result.end());
    return result;
}

bool HumanizerSettingsService::sameProtectedSet(const QStringList &a,
                                                const QStringList &b) const
{
    return a == b;
}

QVariantMap HumanizerSettingsService::compareText(const QString &original,
                                                  const QString &candidate)
{
    const auto originalNumbers = extractMatches(original, QStringLiteral(R"(\b\d+(?:[.,]\d+)?%?\b)"));
    const auto candidateNumbers = extractMatches(candidate, QStringLiteral(R"(\b\d+(?:[.,]\d+)?%?\b)"));
    const auto originalUrls = extractMatches(original, QStringLiteral(R"(https?://[^\s\)\]\}>]+)"));
    const auto candidateUrls = extractMatches(candidate, QStringLiteral(R"(https?://[^\s\)\]\}>]+)"));
    const auto originalQuotes = extractMatches(original, QStringLiteral(R"("[^"]+"|“[^”]+”)"));
    const auto candidateQuotes = extractMatches(candidate, QStringLiteral(R"("[^"]+"|“[^”]+”)"));
    const auto originalCitations = extractMatches(original, QStringLiteral(R"(\[[0-9A-Za-z,;:.\- ]+\])"));
    const auto candidateCitations = extractMatches(candidate, QStringLiteral(R"(\[[0-9A-Za-z,;:.\- ]+\])"));

    const bool numbersOk = !protectNumbers() || sameProtectedSet(originalNumbers, candidateNumbers);
    const bool urlsOk = !protectUrls() || sameProtectedSet(originalUrls, candidateUrls);
    const bool quotesOk = !protectQuotes() || sameProtectedSet(originalQuotes, candidateQuotes);
    const bool citationsOk = !protectCitations() || sameProtectedSet(originalCitations, candidateCitations);
    const bool protectedOk = numbersOk && urlsOk && quotesOk && citationsOk;

    m_lastComparison = {
        {"schema","fa3.humanizer-comparison.v1"},
        {"numbersPreserved",numbersOk},
        {"urlsPreserved",urlsOk},
        {"quotesPreserved",quotesOk},
        {"citationsPreserved",citationsOk},
        {"protectedContentPreserved",protectedOk},
        {"semanticSimilarity",QVariant()},
        {"semanticAuthority",false},
        {"result",protectedOk ? "PASS_PROTECTED_CONTENT" : "REVIEW_OR_REJECT"}
    };
    emit comparisonChanged();
    return m_lastComparison;
}

QVariantMap HumanizerSettingsService::buildAiRewriteRequest(const QString &text) const
{
    if (!aiEnabled()) {
        return {
            {"schema","fa3.humanizer-ai-request.v1"},
            {"state","DENIED_AI_DISABLED"},
            {"direct_provider_call",false},
            {"model_router_required",true},
            {"uaf_required",true},
            {"hrb_required_for_execution",true}
        };
    }

    return {
        {"schema","fa3.humanizer-ai-request.v1"},
        {"state","ROUTE_REQUIRED_NOT_EXECUTED"},
        {"action_id","humanizer.rewrite"},
        {"text",text},
        {"language",language()},
        {"register",registerProfile()},
        {"edit_budget",editBudget()},
        {"voice_profile",voiceProfile()},
        {"direct_provider_call",false},
        {"model_router_required",true},
        {"uaf_required",true},
        {"hrb_required_for_execution",true},
        {"silent_fallback",false},
        {"human_acceptance_required",true}
    };
}

QString HumanizerSettingsService::createAuthorityDraft(const QString &scope,
                                                       const QString &key,
                                                       const QVariant &value)
{
    const QString normalized = scope.trimmed().toUpper();
    if (!kLockedScopes.contains(normalized) || key.trimmed().isEmpty())
        return {};

    const QString root = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation)
        + QStringLiteral("/fa3/humanizer/drafts");
    QDir().mkpath(root);

    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QString path = root + QStringLiteral("/humanizer-draft-") + id + QStringLiteral(".json");
    QJsonObject doc{
        {"schema","fa3.humanizer-settings-draft.v1"},
        {"id",id},
        {"status","DRAFT_NOT_SUBMITTED"},
        {"created_at",QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)},
        {"scope",normalized},
        {"key",key},
        {"value",QJsonValue::fromVariant(value)},
        {"authority",false},
        {"direct_execution",false},
        {"approval_required",true}
    };

    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text))
        return {};
    file.write(QJsonDocument(doc).toJson(QJsonDocument::Indented));
    if (!file.commit())
        return {};

    m_lastDraftPath = path;
    emit draftCreated();
    return path;
}
