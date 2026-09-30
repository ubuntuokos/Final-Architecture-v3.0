#pragma once

#include <QObject>
#include <QSettings>
#include <QString>
#include <QVariantList>
#include <QVariantMap>

class HumanizerSettingsService final : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString fabricState READ fabricState CONSTANT)
    Q_PROPERTY(QString language READ language NOTIFY settingsChanged)
    Q_PROPERTY(QString registerProfile READ registerProfile NOTIFY settingsChanged)
    Q_PROPERTY(QString editBudget READ editBudget NOTIFY settingsChanged)
    Q_PROPERTY(QString voiceProfile READ voiceProfile NOTIFY settingsChanged)
    Q_PROPERTY(bool aiEnabled READ aiEnabled NOTIFY settingsChanged)
    Q_PROPERTY(bool protectNumbers READ protectNumbers NOTIFY settingsChanged)
    Q_PROPERTY(bool protectUrls READ protectUrls NOTIFY settingsChanged)
    Q_PROPERTY(bool protectQuotes READ protectQuotes NOTIFY settingsChanged)
    Q_PROPERTY(bool protectCitations READ protectCitations NOTIFY settingsChanged)
    Q_PROPERTY(QVariantList policyLayers READ policyLayers CONSTANT)
    Q_PROPERTY(QVariantList languages READ languages CONSTANT)
    Q_PROPERTY(QVariantList registerProfiles READ registerProfiles CONSTANT)
    Q_PROPERTY(QVariantList editBudgets READ editBudgets CONSTANT)
    Q_PROPERTY(QVariantMap lastAnalysis READ lastAnalysis NOTIFY analysisChanged)
    Q_PROPERTY(QVariantMap lastComparison READ lastComparison NOTIFY comparisonChanged)
    Q_PROPERTY(QString lastDraftPath READ lastDraftPath NOTIFY draftCreated)

public:
    explicit HumanizerSettingsService(QObject *parent = nullptr);

    QString fabricState() const;
    QString language() const;
    QString registerProfile() const;
    QString editBudget() const;
    QString voiceProfile() const;
    bool aiEnabled() const;
    bool protectNumbers() const;
    bool protectUrls() const;
    bool protectQuotes() const;
    bool protectCitations() const;

    QVariantList policyLayers() const;
    QVariantList languages() const;
    QVariantList registerProfiles() const;
    QVariantList editBudgets() const;
    QVariantMap lastAnalysis() const;
    QVariantMap lastComparison() const;
    QString lastDraftPath() const;

    Q_INVOKABLE void setContext(const QString &projectId,
                                const QString &applicationId,
                                const QString &moduleId,
                                const QString &capabilityId,
                                const QString &functionId);
    Q_INVOKABLE bool setPreference(const QString &scope,
                                   const QString &key,
                                   const QVariant &value);
    Q_INVOKABLE QVariant resolvedSetting(const QString &key) const;
    Q_INVOKABLE QVariantMap analyzeText(const QString &text);
    Q_INVOKABLE QString safeNormalize(const QString &text);
    Q_INVOKABLE QVariantMap compareText(const QString &original,
                                        const QString &candidate);
    Q_INVOKABLE QVariantMap buildAiRewriteRequest(const QString &text) const;
    Q_INVOKABLE QString createAuthorityDraft(const QString &scope,
                                              const QString &key,
                                              const QVariant &value);
    Q_INVOKABLE void refresh();

signals:
    void settingsChanged();
    void analysisChanged();
    void comparisonChanged();
    void draftCreated();

private:
    QString safeId(const QString &value) const;
    QString scopePath(const QString &scope) const;
    QVariant defaultSetting(const QString &key) const;
    QStringList extractMatches(const QString &text, const QString &pattern) const;
    bool sameProtectedSet(const QStringList &a, const QStringList &b) const;

    QSettings m_settings;
    QString m_projectId;
    QString m_applicationId;
    QString m_moduleId;
    QString m_capabilityId;
    QString m_functionId;
    QVariantMap m_lastAnalysis;
    QVariantMap m_lastComparison;
    QString m_lastDraftPath;
};
