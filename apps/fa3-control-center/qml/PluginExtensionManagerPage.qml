import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string applicationContext: "ALL_FA3"
    signal applicationContextRequested(string applicationId)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 12

        RowLayout {
            Layout.fillWidth: true
            Label { text: "Pluginok és extensionök"; font.pixelSize: 24; font.bold: true }
            Item { Layout.fillWidth: true }
            ComboBox {
                id: appScope
                model: ["ALL FA3", "Story", "Video Editor", "Photo Editor", "Vector Editor", "Music Studio", "World Studio", "Character Studio", "Presentation", "Shared", "External Hosts"]
                onActivated: {
                    root.applicationContext = currentText === "ALL FA3" ? "ALL_FA3" : currentText
                    root.applicationContextRequested(root.applicationContext)
                }
            }
        }

        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Közös FA3 management surface. A célalkalmazásnak nem kell futnia. Alkalmazásnézetben csak az adott alkalmazásban alkalmazható vagy elérhető elemek jelennek meg. Telepítve ≠ admitted ≠ enabled ≠ Current Host PASS."
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: ["Installed", "Catalog", "Updates", "Conflicts", "Quarantine", "Permissions", "Evidence"]
                delegate: Button { required property string modelData; text: modelData }
            }
        }

        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            ColumnLayout {
                anchors.fill: parent
                Label { text: "Extension details"; font.bold: true }
                Label { text: "Context: " + root.applicationContext }\n                Label { text: root.applicationContext === "ALL_FA3" ? "Nézet: teljes admitted katalógus" : "Nézet: applicability + capability + runtime + policy szerint szűrt" }
                Label { text: "Trust: PENDING / ADMITTED projection" }
                Label { text: "Installation: NOT_INSTALLED / STAGED / INSTALLED" }
                Label { text: "Activation: DISABLED / ENABLED / ACTIVE" }
                Label { text: "Evidence: PENDING_CURRENT_HOST / CURRENT_HOST_PASS" }
                Label { text: "AI: külön policy alatt · DENY győz · rejtett helyettesítés tiltott" }
                Label { text: "GPU/NPU: kizárólag HRB admission után" }
                Label { text: "Layer Guard + Software Coexistence: kötelező" }
                Item { Layout.fillHeight: true }
                RowLayout {
                    Button { text: "Enable"; enabled: false; ToolTip.text: "Authority-gated action intent" }
                    Button { text: "Update"; enabled: false; ToolTip.text: "Impact preview és approval szükséges" }
                    Button { text: "Rollback"; enabled: false }
                    Button { text: "Remove"; enabled: false }
                }
            }
        }
    }
}
