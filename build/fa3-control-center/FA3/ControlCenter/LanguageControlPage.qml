import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    required property var preferences
    required property color panel
    required property color panelRaised
    required property color border
    required property color textPrimary
    required property color textMuted
    required property color accent
    required property color green
    required property color orange

    // Keep mandatory system-language policy visible to the language gate while
    // the primary Tolmács surface is the live interpreter workspace.
    readonly property string surfaceName: "Tolmács / Nyelvi híd"
    readonly property string controlProfileId: "FA3-GUI-LANGUAGE-CONTROL-001"
    readonly property string bridgeProfileId: "FA3-LANGUAGE-BRIDGE-001"
    readonly property string nativeLanguagePreference: "Natív modellnyelv előnyben"
    readonly property string mediatedLanguagePreference: "Közvetített nyelv engedélyezése"
    property string primaryLanguage: String(preferences.value("languagePolicy/primaryLanguage", ""))
    property string secondaryLanguage: String(preferences.value("languagePolicy/secondaryLanguage", ""))
    readonly property bool systemLanguageValid: primaryLanguage.length > 0
                                                && secondaryLanguage.length > 0
                                                && primaryLanguage !== secondaryLanguage
    function setPrimaryLanguage(value) {
        if (value.length > 0 && value !== secondaryLanguage) {
            primaryLanguage = value
            preferences.setValue("languagePolicy/primaryLanguage", value)
        }
    }
    function setSecondaryLanguage(value) {
        if (value.length > 0 && value !== primaryLanguage) {
            secondaryLanguage = value
            preferences.setValue("languagePolicy/secondaryLanguage", value)
        }
    }

    readonly property string truthBoundary: "ADAPTER-GATED · PENDING_BACKEND · SECRET egress denied · translation is a derived projection"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "Élő Tolmács" }
            TabButton { text: "Nyelvi policy" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            LiveInterpreterPage {
                preferences: root.preferences
                panel: root.panel
                panelRaised: root.panelRaised
                border: root.border
                textPrimary: root.textPrimary
                textMuted: root.textMuted
                accent: root.accent
                green: root.green
                orange: root.orange
            }

            LanguagePolicyPage {
                preferences: root.preferences
                panel: root.panel
                panelRaised: root.panelRaised
                border: root.border
                textPrimary: root.textPrimary
                textMuted: root.textMuted
                accent: root.accent
                green: root.green
                orange: root.orange
            }
        }
    }
}
