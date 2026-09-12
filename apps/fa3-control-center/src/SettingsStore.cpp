#include "SettingsStore.h"

#include <QDir>
#include <QFileDialog>
#include <QFileInfo>
#include <QSettings>
#include <QStorageInfo>

namespace {
QSettings makeSettings()
{
    return QSettings();
}

QString normalizedPath(const QString &value)
{
    if (value.trimmed().isEmpty())
        return {};
    return QDir::cleanPath(QDir::fromNativeSeparators(value.trimmed()));
}
}

SettingsStore::SettingsStore(QObject *parent)
    : QObject(parent)
{
}

QVariant SettingsStore::defaultForKey(const QString &key) const
{
    const QString home = QDir::homePath();
    if (key == "appearance/uiScale") return 1.0;
    if (key == "appearance/baseFontSize") return 13;
    if (key == "appearance/themeMode") return QStringLiteral("system");
    if (key == "appearance/density") return QStringLiteral("normal");
    if (key == "appearance/reducedMotion") return false;
    if (key == "appearance/highContrast") return false;
    if (key == "locale/language") return QStringLiteral("hu");
    if (key == "locale/technicalTermsEnglish") return true;
    if (key == "workspace/startPage") return QStringLiteral("Command Center");
    if (key == "workspace/restoreSession") return true;
    if (key == "workspace/autosaveMinutes") return 5;
    if (key == "dashboard/profile") return QStringLiteral("Studio");
    if (key == "notifications/enabled") return true;
    if (key == "notifications/errorsOnly") return false;
    if (key == "performance/telemetryRefreshSeconds") return 5;
    if (key == "paths/projects") return home + QStringLiteral("/FA3-Projects");
    if (key == "paths/workspaces") return home + QStringLiteral("/FA3-Workspaces");
    if (key == "paths/models") return QStringLiteral("/AI-modells");
    if (key == "paths/modelCache") return QStringLiteral("/ai-cache");
    if (key == "paths/datasets") return QStringLiteral("/ai-datasets");
    if (key == "paths/outputs") return home + QStringLiteral("/FA3-Outputs");
    if (key == "paths/evidenceExport") return home + QStringLiteral("/FA3-Evidence");
    if (key == "paths/imageAssets") return home + QStringLiteral("/FA3-Assets/Images");
    if (key == "paths/videoAssets") return home + QStringLiteral("/FA3-Assets/Video");
    if (key == "paths/audioAssets") return home + QStringLiteral("/FA3-Assets/Audio");
    if (key == "paths/threeDAssets") return home + QStringLiteral("/FA3-Assets/3D");
    if (key == "paths/lutLibrary") return home + QStringLiteral("/FA3-Assets/LUT");
    if (key == "integrations/imageEditor") return QStringLiteral("Krita");
    if (key == "integrations/videoEditor") return QStringLiteral("Kdenlive");
    if (key == "integrations/audioEditor") return QStringLiteral("Ardour");
    if (key == "integrations/threeDEditor") return QStringLiteral("Bforartists");
    if (key == "mentor/enabled") return true;
    if (key == "mentor/profile") return QStringLiteral("Expert Assistant");
    if (key == "mentor/detail") return QStringLiteral("Normal");
    if (key == "mentor/initiative") return QStringLiteral("Balanced");
    if (key == "mentor/memoryPolicy") return QStringLiteral("Ask for new categories");
    if (key == "mentor/masteryTracking") return true;
    if (key == "mentor/practiceLab") return true;
    if (key == "mentor/voice") return false;
    if (key == "mentor/citationsRequired") return true;
    if (key == "coach/enabled") return true;
    if (key == "coach/profile") return QStringLiteral("Executive");
    if (key == "coach/proactivity") return QStringLiteral("Balanced");
    if (key == "coach/checkIns") return true;
    if (key == "coach/projectAwareness") return true;
    if (key == "coach/intervention") return QStringLiteral("Balanced");
    if (key == "coach/mentorReferrals") return true;
    if (key == "coach/weeklyReview") return true;
    if (key == "coach/quietHours") return QStringLiteral("20:00-08:00");
    return {};
}

QVariant SettingsStore::value(const QString &key, const QVariant &fallback) const
{
    QSettings settings = makeSettings();
    const QVariant defaultValue = fallback.isValid() ? fallback : defaultForKey(key);
    return settings.value(key, defaultValue);
}

void SettingsStore::persist(const QString &key, const QVariant &newValue)
{
    QSettings settings = makeSettings();
    if (settings.value(key, defaultForKey(key)) == newValue)
        return;
    settings.setValue(key, newValue);
    settings.sync();
    emit settingChanged(key);
}

qreal SettingsStore::uiScale() const { return value(QStringLiteral("appearance/uiScale")).toReal(); }
int SettingsStore::baseFontSize() const { return value(QStringLiteral("appearance/baseFontSize")).toInt(); }
QString SettingsStore::language() const { return value(QStringLiteral("locale/language")).toString(); }
QString SettingsStore::themeMode() const { return value(QStringLiteral("appearance/themeMode")).toString(); }
QString SettingsStore::configFilePath() const { QSettings settings = makeSettings(); return settings.fileName(); }

void SettingsStore::setUiScale(qreal newValue)
{
    newValue = qBound<qreal>(0.80, newValue, 2.00);
    if (qFuzzyCompare(uiScale(), newValue)) return;
    persist(QStringLiteral("appearance/uiScale"), newValue);
    emit uiScaleChanged();
}

void SettingsStore::setBaseFontSize(int newValue)
{
    newValue = qBound(10, newValue, 28);
    if (baseFontSize() == newValue) return;
    persist(QStringLiteral("appearance/baseFontSize"), newValue);
    emit baseFontSizeChanged();
}

void SettingsStore::setLanguage(const QString &newValue)
{
    const QString normalized = (newValue == QStringLiteral("en")) ? QStringLiteral("en") : QStringLiteral("hu");
    if (language() == normalized) return;
    persist(QStringLiteral("locale/language"), normalized);
    emit languageChanged();
}

void SettingsStore::setThemeMode(const QString &newValue)
{
    const QStringList allowed{QStringLiteral("system"), QStringLiteral("light"), QStringLiteral("dark")};
    const QString normalized = allowed.contains(newValue) ? newValue : QStringLiteral("system");
    if (themeMode() == normalized) return;
    persist(QStringLiteral("appearance/themeMode"), normalized);
    emit themeModeChanged();
}

void SettingsStore::setValue(const QString &key, const QVariant &newValue)
{
    if (key == QStringLiteral("appearance/uiScale")) { setUiScale(newValue.toReal()); return; }
    if (key == QStringLiteral("appearance/baseFontSize")) { setBaseFontSize(newValue.toInt()); return; }
    if (key == QStringLiteral("locale/language")) { setLanguage(newValue.toString()); return; }
    if (key == QStringLiteral("appearance/themeMode")) { setThemeMode(newValue.toString()); return; }
    persist(key, newValue);
}

QString SettingsStore::chooseDirectory(const QString &title, const QString &initialPath) const
{
    const QString seed = initialPath.isEmpty() ? QDir::homePath() : initialPath;
    const QString selected = QFileDialog::getExistingDirectory(nullptr, title, seed,
        QFileDialog::ShowDirsOnly | QFileDialog::DontResolveSymlinks);
    return normalizedPath(selected);
}

QVariantMap SettingsStore::pathStatus(const QString &path) const
{
    QVariantMap result;
    const QString normalized = normalizedPath(path);
    QFileInfo info(normalized);
    QStorageInfo storage(normalized);
    result.insert(QStringLiteral("path"), normalized);
    result.insert(QStringLiteral("exists"), info.exists() && info.isDir());
    result.insert(QStringLiteral("writable"), info.exists() && info.isDir() && info.isWritable());
    result.insert(QStringLiteral("ready"), storage.isReady());
    result.insert(QStringLiteral("filesystem"), QString::fromLatin1(storage.fileSystemType()));
    result.insert(QStringLiteral("rootPath"), storage.rootPath());
    result.insert(QStringLiteral("freeGiB"), storage.isReady() ? (double(storage.bytesAvailable()) / 1073741824.0) : 0.0);
    return result;
}

void SettingsStore::resetGroup(const QString &group)
{
    QSettings settings = makeSettings();
    settings.beginGroup(group);
    settings.remove(QString());
    settings.endGroup();
    settings.sync();
    emit uiScaleChanged(); emit baseFontSizeChanged(); emit languageChanged(); emit themeModeChanged(); emit settingsReset();
}

void SettingsStore::resetAll()
{
    QSettings settings = makeSettings();
    settings.clear();
    settings.sync();
    emit uiScaleChanged(); emit baseFontSizeChanged(); emit languageChanged(); emit themeModeChanged(); emit settingsReset();
}
