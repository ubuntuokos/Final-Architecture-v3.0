import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs

// Non-modal FA3 Coach tool window. Wayland uses the compositor's native
// startSystemMove/Resize; stored coordinates are best-effort on Wayland.
Window {
    id: root
    property var service: null
    property var preferences: null
    property bool compactMode: false
    property bool iconMode: false
    property bool pinned: false
    property int currentSection: 0
    property string notice: ""
    signal mentorRequested()
    signal managerRequested()
    signal evidenceRequested()

    width: iconMode ? 76 : (compactMode ? 460 : 740)
    height: iconMode ? 76 : (compactMode ? 380 : 640)
    minimumWidth: iconMode ? 76 : 400
    minimumHeight: iconMode ? 76 : 330
    title: "FA3 Coach – lebegő segítő"
    color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | (pinned ? Qt.WindowStaysOnTopHint : 0)
    visible: false
    opacity: 1.0

    readonly property color bg: "#0b1728"
    readonly property color raised: "#14263b"
    readonly property color edge: "#285078"
    readonly property color fg: "#eef4fb"
    readonly property color muted: "#a0b2c4"
    readonly property color blue: "#50a7ff"
    readonly property color orange: "#efb35c"
    readonly property var sections: ["Célok", "Haladás", "Akadályok", "Következő lépés", "Fókusz", "Jóváhagyás"]
    readonly property int reported: service ? service.selfReportedCount : 0
    readonly property int total: service ? service.milestones.length : 0

    function showCoach() {
        visible = true
        raise()
        requestActivate()
    }
    function saveVisualState() {
        if (!preferences) return
        preferences.setValue("coach/window/compact", compactMode)
        preferences.setValue("coach/window/pinned", pinned)
        preferences.setValue("coach/window/opacity", opacity)
        preferences.setValue("coach/window/x", x)
        preferences.setValue("coach/window/y", y)
    }
    Component.onCompleted: {
        if (!preferences) return
        compactMode = Boolean(preferences.value("coach/window/compact", false))
        pinned = Boolean(preferences.value("coach/window/pinned", false))
        opacity = Math.max(0.68, Math.min(1, Number(preferences.value("coach/window/opacity", 1))))
        // The compositor may ignore global positioning on Wayland.
        var sx = preferences.value("coach/window/x", null)
        var sy = preferences.value("coach/window/y", null)
        if (sx !== null && sy !== null && Number(sx) >= 0 && Number(sy) >= 0) {
            x = Number(sx); y = Number(sy)
        }
    }
    onXChanged: { if (visible && preferences) preferences.setValue("coach/window/x", x) }
    onYChanged: { if (visible && preferences) preferences.setValue("coach/window/y", y) }
    onClosing: function(event) { saveVisualState(); event.accepted = true; visible = false }

    component Chip: Rectangle {
        property string label: ""
        property color tone: root.blue
        radius: 8
        color: Qt.alpha(tone, 0.13)
        border.color: Qt.alpha(tone, 0.65)
        implicitWidth: chipLabel.implicitWidth + 18
        implicitHeight: 26
        Label { id: chipLabel; anchors.centerIn: parent; text: parent.label; color: parent.tone; font.pixelSize: 10; font.bold: true }
    }
    component Card: Rectangle {
        default property alias contents: cardBody.data
        implicitWidth: 300
        implicitHeight: cardBody.implicitHeight + 24
        radius: 10
        color: root.raised
        border.color: root.edge
        ColumnLayout { id: cardBody; anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }; spacing: 8 }
    }

    Rectangle {
        anchors.fill: parent
        radius: iconMode ? 38 : 12
        color: root.bg
        border.color: root.blue
        border.width: 1
    }

    Button {
        anchors.fill: parent
        visible: root.iconMode
        text: "◉\nCoach"
        font.pixelSize: 17
        onClicked: { root.iconMode = false; root.compactMode = true }
        ToolTip.visible: hovered
        ToolTip.text: "FA3 Coach kibontása"
        background: Rectangle { radius: 38; color: "#21466d"; border.color: root.blue }
        contentItem: Text { text: parent.text; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; color: root.fg; font.bold: true }
    }

    ColumnLayout {
        visible: !root.iconMode
        anchors.fill: parent
        anchors.margins: 10
        spacing: 9
        RowLayout {
            id: header
            Layout.fillWidth: true
            Layout.preferredHeight: 45
            spacing: 6
            Rectangle {
                id: moveHandle
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "transparent"
                RowLayout {
                    anchors.fill: parent
                    spacing: 8
                    Label { text: "✥"; color: root.blue; font.pixelSize: 21 }
                    ColumnLayout {
                        spacing: 0
                        Label { text: "FA3 Coach"; color: root.fg; font.pixelSize: 18; font.bold: true }
                        Label { text: "Húzd a fejlécet a kívánt helyre"; color: root.muted; font.pixelSize: 10 }
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: root.startSystemMove()
                    cursorShape: Qt.SizeAllCursor
                }
            }
            ToolButton {
                text: root.pinned ? "📌" : "Kitűzés"
                checkable: true
                checked: root.pinned
                ToolTip.text: "Mindig felül (a rendszer ablakkezelőjétől függ)"
                ToolTip.visible: hovered
                onClicked: { root.pinned = !root.pinned; root.saveVisualState() }
            }
            ToolButton {
                text: root.compactMode ? "Normál" : "Kompakt"
                onClicked: { root.compactMode = !root.compactMode; root.saveVisualState() }
            }
            ToolButton { text: "◉"; ToolTip.text: "Ikon mód"; ToolTip.visible: hovered; onClicked: {root.iconMode = true} }
            ToolButton { text: "×"; ToolTip.text: "Bezárás"; ToolTip.visible: hovered; onClicked: {root.saveVisualState(); root.hide()} }
        }
        RowLayout {
            Layout.fillWidth: true
            Chip { label: service ? service.adapterState : "NO ADAPTER"; tone: root.orange }
            Label { Layout.fillWidth: true; text: "Helyi javaslatok • nem hitelesített teljesítés"; color: root.muted; font.pixelSize: 10; elide: Text.ElideRight }
            Label { text: "Áttetszőség"; color: root.muted; font.pixelSize: 10 }
            Slider {
                id: alphaSlider
                from: .68; to: 1.0
                value: root.opacity
                Layout.preferredWidth: 84
                onMoved: { root.opacity = value; root.saveVisualState() }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: root.edge }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8
            ColumnLayout {
                Layout.preferredWidth: root.compactMode ? 82 : 148
                Layout.fillHeight: true
                spacing: 5
                Repeater {
                    model: root.sections
                    delegate: Button {
                        required property int index
                        required property string modelData
                        Layout.fillWidth: true
                        text: root.compactMode ? ["Cél", "Halad", "Akad", "Lépés", "Fókusz", "OK"][index] : modelData
                        checkable: true
                        checked: root.currentSection === index
                        onClicked: root.currentSection = index
                        background: Rectangle {
                            radius: 6
                            color: parent.checked ? "#21548c" : parent.hovered ? "#193450" : "transparent"
                            border.color: parent.checked ? root.blue : "transparent"
                        }
                        contentItem: Label {
                            text: parent.text
                            color: root.fg
                            font.pixelSize: 11
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 5
                        }
                        Accessible.name: modelData
                    }
                }
                Item { Layout.fillHeight: true }
                Label { text: "Ctrl+Shift+C"; color: root.muted; font.pixelSize: 9; visible: !root.compactMode }
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width - 10
                    spacing: 10

                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 0 || root.currentSection === 1
                        Label { text: "AKTÍV CÉL"; color: root.blue; font.bold: true; font.pixelSize: 11 }
                        ComboBox {
                            id: scopeCombo
                            Layout.fillWidth: true
                            model: ["FA3_PROJECT", "USER_SELF", "AI_AGENT_WORK"]
                            currentIndex: service && service.scope === "USER_SELF" ? 1 : service && service.scope === "AI_AGENT_WORK" ? 2 : 0
                            Accessible.name: "Cél hatóköre"
                        }
                        TextField {
                            id: goalInput
                            Layout.fillWidth: true
                            text: service ? service.goal : ""
                            placeholderText: "Írd be a saját célodat…"
                            Accessible.name: "Cél megnevezése"
                            onAccepted: if (service) service.setGoal(text, scopeCombo.currentText)
                        }
                        Button {
                            text: "Cél rögzítése (helyi vázlat)"
                            enabled: goalInput.text.trim().length > 0 && service
                            onClicked: {
                                if (!service.setGoal(goalInput.text, scopeCombo.currentText))
                                    root.notice = "Érvénytelen cél vagy hatókör."
                                else root.notice = "Helyi célrögzítés megtörtént. Nem indult végrehajtás."
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "Saját teljesítésjelzés: " + root.reported + " / " + root.total + ". Igazolt: 0 (bizonyítékadapterre vár)."
                            color: root.muted
                            wrapMode: Text.Wrap
                        }
                        ProgressBar { Layout.fillWidth: true; from: 0; to: Math.max(1,root.total); value: root.reported }
                    }
                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 0 || root.currentSection === 1
                        Label { text: "MÉRFÖLDKÖVEK"; color: root.fg; font.bold: true }
                        Repeater {
                            model: service ? service.milestones : []
                            delegate: RowLayout {
                                required property int index
                                required property var modelData
                                Layout.fillWidth: true
                                CheckBox {
                                    checked: Boolean(modelData.selfReported)
                                    onToggled: if (service) service.markMilestone(index, checked)
                                    Accessible.name: "Saját jelzés: " + modelData.text
                                }
                                Label { Layout.fillWidth: true; text: modelData.text; color: root.fg; wrapMode: Text.WordWrap }
                                Chip { label: "Nem igazolt"; tone: root.orange; visible: !root.compactMode }
                                ToolButton { text: "×"; onClicked: if (service) service.removeMilestone(index); Accessible.name: "Mérföldkő törlése" }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            TextField {
                                id: milestoneInput
                                Layout.fillWidth: true
                                placeholderText: "Új mérföldkő…"
                                onAccepted: if (service && service.addMilestone(text)) clear()
                            }
                            Button { text: "+"; enabled: milestoneInput.text.trim() !== ""; onClicked: if (service && service.addMilestone(milestoneInput.text)) milestoneInput.clear() }
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 2
                        Label { text: "AKADÁLYOK"; color: root.orange; font.bold: true }
                        Repeater {
                            model: service ? service.blockers : []
                            delegate: RowLayout {
                                required property int index
                                required property var modelData
                                Layout.fillWidth: true
                                Label { Layout.fillWidth: true; color: modelData.resolved ? root.muted : root.fg; text: modelData.text; wrapMode: Text.WordWrap }
                                Button { text: modelData.resolved ? "Feloldva" : "Feloldás jelzése"; enabled: !modelData.resolved; onClicked: service.resolveBlocker(index) }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            TextField { id: blockerInput; Layout.fillWidth: true; placeholderText: "Új akadály…" }
                            Button { text: "+"; enabled: blockerInput.text.trim() !== ""; onClicked: if (service && service.addBlocker(blockerInput.text)) blockerInput.clear() }
                        }
                    }
                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 3
                        Label { text: "JAVASOLT KÖVETKEZŐ LÉPÉS"; color: root.blue; font.bold: true }
                        Label { Layout.fillWidth: true; text: service ? service.nextStep() : "Nincs adapter."; wrapMode: Text.WordWrap; color: root.fg }
                        Label { text: "Javaslat, nem automatikus végrehajtás."; color: root.muted }
                        Button { text: "Manager megnyitása"; onClicked: root.managerRequested() }
                    }
                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 4
                        Label { text: "FÓKUSZBLOKK"; color: root.blue; font.bold: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Hossz:"; color: root.muted }
                            ComboBox {
                                id: focusDuration
                                model: ["25 perc", "45 perc", "60 perc"]
                                onActivated: { focusTimer.stop(); root.focusSeconds = [1500,2700,3600][currentIndex] }
                            }
                        }
                        Label { text: Math.floor(root.focusSeconds / 60) + ":" + ("0" + root.focusSeconds % 60).slice(-2); color: root.fg; font.pixelSize: 34; font.bold: true }
                        RowLayout {
                            Button { text: focusTimer.running ? "Szünet" : "Indítás"; onClicked: if (focusTimer.running) focusTimer.stop(); else focusTimer.start() }
                            Button { text: "Újrakezdés"; onClicked: {focusTimer.stop(); root.focusSeconds = [1500,2700,3600][focusDuration.currentIndex]} }
                        }
                        Label { text: "A fókuszidő nem bizonyíték a feladat teljesítésére."; color: root.muted; wrapMode: Text.WordWrap }
                    }
                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 5
                        Label { text: "JÓVÁHAGYÁS ÉS DELEGÁLÁS"; color: root.blue; font.bold: true }
                        CheckBox {
                            text: "Ezt a célkitűzést kifejezetten vállalom"
                            checked: service ? service.committed : false
                            onToggled: if (service) service.setCommitment(checked)
                        }
                        Label { text: "A vállalás nem jogosít végrehajtásra, memóriába írásra vagy VERIFIED státuszra."; wrapMode: Text.WordWrap; color: root.muted }
                        Button { text: "Mentor nézet"; onClicked: root.mentorRequested() }
                        Button { text: "Manager nézet"; onClicked: root.managerRequested() }
                        Button { text: "Evidence nézet"; onClicked: root.evidenceRequested() }
                    }
                    Card {
                        Layout.fillWidth: true
                        visible: root.currentSection === 0 || root.currentSection === 5
                        Label { text: "HELYI MUNKAMENET"; color: root.blue; font.bold: true }
                        Label { text: "Csak külön mentéssel marad meg; nem kanonikus FA3 Memory."; color: root.muted; wrapMode: Text.WordWrap }
                        RowLayout {
                            Button { text: "Vázlat mentése…"; enabled: service && service.goal.length > 0; onClicked: saveDialog.open() }
                            Button { text: "Megnyitás…"; onClicked: loadDialog.open() }
                            Button { text: "Ürítés"; onClicked: clearDialog.open() }
                        }
                    }
                    Label { Layout.fillWidth: true; text: root.notice; visible: root.notice.length > 0; color: root.orange; wrapMode: Text.Wrap }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: root.edge }
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: "FA3 Coach • helyi, javaslatadó mód • Éles adapter: hiányzik"
                color: root.muted
                font.pixelSize: 10
                elide: Text.ElideRight
            }
            Button {
                text: "Mentor"
                onClicked: root.mentorRequested()
                ToolTip.visible: hovered
                ToolTip.text: "Mentor felület megnyitása, nem automatikus feladatátadás"
            }
            Button { text: "Manager"; onClicked: root.managerRequested() }
        }
    }
    property int focusSeconds: 1500
    Timer {
        id: focusTimer
        interval: 1000
        repeat: true
        onTriggered: {
            root.focusSeconds = Math.max(0, root.focusSeconds - 1)
            if (root.focusSeconds === 0) { stop(); root.notice = "A fókuszblokk véget ért." }
        }
    }
    FileDialog {
        id: saveDialog
        title: "Coach vázlat mentése (külön hozzájárulással)"
        fileMode: FileDialog.SaveFile
        nameFilters: ["FA3 Coach vázlat (*.json)"]
        onAccepted: root.notice = service && service.saveDraft(selectedFile) ? "A vázlat mentve." : "Mentés elutasítva vagy sikertelen."
    }
    FileDialog {
        id: loadDialog
        title: "Coach vázlat megnyitása"
        fileMode: FileDialog.OpenFile
        nameFilters: ["FA3 Coach vázlat (*.json)"]
        onAccepted: root.notice = service && service.loadDraft(selectedFile) ? "A vázlat betöltve; a vállalás nincs automatikusan elfogadva." : "Érvénytelen vagy nem támogatott fájl."
    }
    Dialog {
        id: clearDialog
        title: "Helyi Coach-munkamenet törlése?"
        standardButtons: Dialog.Yes | Dialog.No
        modal: true
        onAccepted: if (service) {service.clearSession(); root.notice = "Helyi munkamenet ürítve."}
    }
    // Native resize without compositor-defeating global pointer repositioning.
    MouseArea {
        width: 22; height: 22
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        cursorShape: Qt.SizeFDiagCursor
        visible: !root.iconMode
        onPressed: root.startSystemResize(Qt.BottomEdge | Qt.RightEdge)
        Accessible.name: "Ablak átméretezése"
    }
}