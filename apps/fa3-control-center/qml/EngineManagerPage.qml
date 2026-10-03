// SPDX-License-Identifier: Apache-2.0
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property var engineController

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        Label {
            text: "Engine & Provider Manager"
            font.pixelSize: 22
            font.bold: true
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Közös motorleltár és felhasználói preferenciafelület. A provider/model route, hardver-hozzárendelés, credential, license és runtime admission a meglévő FA3 authority-k feladata."
        }
        EngineSelectorPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true
            controller: root.engineController
        }
    }
}
