import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    width: 1510
    height: 910
    minimumWidth: 1200
    minimumHeight: 780
    visible: true
    title: "FA3 World & Environment Studio – World & Event Director"
    color: "#0b121d"
    property color panel: "#142338"
    property color raised: "#1d334a"
    property color muted: "#a2bdce"
    property color white: "#edf5ff"
    property color cyan: "#56d6f0"
    property color mint: "#72e2b3"
    property color amber: "#ffc96e"
    property real previewRain: world.rain
    property real previewWind: world.wind
    property real previewCloud: world.cloud

    component HeaderText: Text {
        color:root.white
        font.pixelSize:13
        font.bold:true
    }
    component AccentButton: Button {
        background: Rectangle { radius:6; color: parent.down?"#3066a4": "#315a80"; border.color:"#426f8b" }
        contentItem: Text {text:parent.text;color:root.white;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.pixelSize:12;font.bold:true}
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10
        RowLayout {
            Layout.preferredHeight: 42
            Text { text: "◈  FA3 WORLD & ENVIRONMENT STUDIO"; color:root.white; font.pixelSize:21;font.bold:true; Layout.fillWidth:true }
            Text { text:"WORLD & EVENT DIRECTOR   ·   CPU PREVIEW";color:root.cyan;font.bold:true }
        }
        Rectangle { Layout.fillWidth:true; height:1; color:"#355268" }
        RowLayout {
            Layout.preferredHeight: 43; spacing: 9
            Text {text:"HELY";color:root.muted;font.bold:true}
            ComboBox {id:place;model:["Budapest","Cape Town","Singapore","Tromso","Nairobi"];currentIndex:0; Layout.preferredWidth:132}
            Text {text:"DÁTUM";color:root.muted;font.bold:true}
            TextField {id:day; text:world.date; Layout.preferredWidth:120;selectByMouse:true}
            Text {text:"IDŐ";color:root.muted;font.bold:true}
            TextField {id:clock; text:world.clock; Layout.preferredWidth:75;placeholderText:"ismeretlen"}
            Text {text:"VILÁG";color:root.muted;font.bold:true}
            ComboBox {id:mode;model:["HISTORICAL","HYBRID","ALTERNATE_HISTORY","FICTIONAL"]; currentIndex:1; Layout.preferredWidth:190}
            AccentButton {text:"ALKALMAZ";onClicked:world.applyContext(place.currentText,day.text,clock.text,mode.currentText)}
            Item {Layout.fillWidth:true}
            AccentButton {text:"MENTÉS";onClicked:saveDialog.open()}
            AccentButton {text:"MEGNYITÁS";onClicked:openDialog.open()}
        }
        RowLayout {
            Layout.fillWidth:true; Layout.fillHeight:true;spacing:10
            Rectangle {
                Layout.preferredWidth:205;Layout.fillHeight:true;color:root.panel;radius:8;border.color:"#334b63"
                ColumnLayout {
                    anchors.fill:parent;anchors.margins:14;spacing:12
                    HeaderText {text:"VILÁG & ESEMÉNYEK";color:root.cyan}
                    Repeater {
                        model:["◉   NÉGY KÖRNYEZET", "◭   TERMÉSZET", "▦   TELEPÜLÉS", "⌂   ÉPÜLETKÖRNYEZET", "▤   BELSŐ TEREK"]
                        delegate: Rectangle {required property string modelData; Layout.fillWidth:true;height:38;radius:5;color:index===0?"#315a80":root.raised
                            Text {anchors.centerIn:parent;text:modelData;color:root.white;font.pixelSize:12} }
                    }
                    Rectangle {height:1;Layout.fillWidth:true;color:"#38546b"}
                    HeaderText {text:"JELENSÉGEK";color:root.muted}
                    Text {text:"Zivatar · hó · szél · köd";color:root.white;font.pixelSize:12}
                    Text {text:"Árvíz · tűz · földrengés";color:root.white;font.pixelSize:12}
                    Rectangle {height:1;Layout.fillWidth:true;color:"#38546b"}
                    HeaderText {text:"FÜGGETLEN RÉTEGEK";color:root.muted}
                    Text {text:"FÖLDRAJZ / NAPÁLLÁS";color:root.mint;font.pixelSize:12;font.bold:true}
                    Text {text:"FORGATÓKÖNYVI ESEMÉNY";color:root.amber;font.pixelSize:12;font.bold:true}
                    Text {text:"VILÁGSZABÁLYOK";color:root.cyan;font.pixelSize:12;font.bold:true}
                    Item{Layout.fillHeight:true}
                    Text {text:"Pontatlan korabeli\nutcaszint: ISMERETLEN";wrapMode:Text.WordWrap;color:root.muted;font.pixelSize:11}
                }
            }
            ColumnLayout {
                Layout.fillWidth:true;Layout.fillHeight:true;spacing:8
                Rectangle {
                    Layout.fillWidth:true;height:38;color:root.panel;radius:6
                    HeaderText {anchors.verticalCenter:parent.verticalCenter;x:14;text:"KÖRNYEZETI ÁTTEKINTÉS   ·   4 TÉRBELI LÉPTÉK"}
                }
                GridLayout {
                    Layout.fillWidth:true;Layout.fillHeight:true;columns:2;rowSpacing:10;columnSpacing:10
                    ScenePane {scope:"NATURAL";heading:"01   TERMÉSZET / TÁJ";effects:world.impactNatural;rain:root.previewRain;wind:root.previewWind;clouds:root.previewCloud; Layout.fillHeight:true;Layout.fillWidth:true}
                    ScenePane {scope:"CITY";heading:"02   LAKOTT TERÜLET";effects:world.impactCity;rain:root.previewRain;wind:root.previewWind;clouds:root.previewCloud; Layout.fillHeight:true;Layout.fillWidth:true}
                    ScenePane {scope:"BUILDING";heading:"03   ÉPÜLETKÖRNYEZET";effects:world.impactBuilding;rain:root.previewRain;wind:root.previewWind;clouds:root.previewCloud;Layout.fillHeight:true;Layout.fillWidth:true}
                    ScenePane {scope:"INTERIOR";heading:"04   ÉPÜLET BELSEJE";effects:world.impactInterior;rain:root.previewRain;wind:root.previewWind;clouds:root.previewCloud;Layout.fillHeight:true;Layout.fillWidth:true}
                }
                Rectangle { Layout.fillWidth:true;Layout.preferredHeight:65;color:root.panel;radius:6
                    Column {anchors.fill:parent;anchors.margins:13;spacing:7
                        Text {text:"☼   "+world.sky;color:root.amber;font.bold:true;font.pixelSize:12}
                        Text {text:"Az esemény megváltoztatja a jelenetet, de nem írja át automatikusan az égtájakat vagy a Nap pályáját.";color:root.muted;font.pixelSize:11;elide:Text.ElideRight;width:parent.width}
                    }
                }
            }
            Rectangle {
                Layout.preferredWidth:290;Layout.fillHeight:true;color:root.panel;radius:8;border.color:"#334b63"
                ScrollView {anchors.fill:parent;anchors.margins:12;clip:true
                    ColumnLayout {width:258;spacing:9
                        HeaderText {text:"IDŐJÁRÁS & HATÁSOK";color:root.cyan;font.pixelSize:14}
                        Repeater {model:[
                            {label:"HŐMÉRSÉKLET",unit:"°C",lo:-20,hi:45,v:world.temperature,role:0},
                            {label:"CSAPADÉK",unit:"mm/h",lo:0,hi:60,v:world.rain,role:1},
                            {label:"SZÉL",unit:"km/h",lo:0,hi:120,v:world.wind,role:2},
                            {label:"FELHŐZET",unit:"%",lo:0,hi:100,v:world.cloud,role:3}
                        ];delegate:ColumnLayout{
                            required property var modelData
                            Layout.fillWidth:true;spacing:3
                            RowLayout {Layout.fillWidth:true
                                Text{text:modelData.label;color:root.muted;font.bold:true;font.pixelSize:11;Layout.fillWidth:true}
                                Text{text:slider.value.toFixed(0)+" "+modelData.unit;color:root.cyan;font.bold:true;font.pixelSize:12}
                            }
                            Slider {id:slider; Layout.fillWidth:true;from:modelData.lo;to:modelData.hi;value:modelData.v
                                onMoved:{let t=root.previewRain,r=root.previewWind,c=root.previewCloud;
                                    if(modelData.role===1)t=value;else if(modelData.role===2)r=value;else if(modelData.role===3)c=value;
                                    root.previewRain=t;root.previewWind=r;root.previewCloud=c;
                                    let temp=(modelData.role===0)?value:world.temperature;
                                    world.updateWeather(temp,t,r,c);}
                            }
                        }}
                        Rectangle {height:1;Layout.fillWidth:true;color:"#37536b"}
                        HeaderText {text:"NARRATÍV ESEMÉNY";color:root.amber}
                        ComboBox {id:eventKind;model:["STORM","FLOOD","FIRE","EARTHQUAKE","SNOW","TREX","ALIEN"];Layout.fillWidth:true}
                        AccentButton {text:"+ ESEMÉNY HOZZÁADÁSA";Layout.fillWidth:true;onClicked:world.addEvent(eventKind.currentText)}
                        HeaderText {text:"VILÁGSZABÁLYOK";color:root.muted}
                        AccentButton {text:"KÉT VALÓDI NAP…";Layout.fillWidth:true;onClicked:approval.open()}
                        AccentButton {text:"FÖLDI ALAP VISSZAÁLLÍTÁSA";Layout.fillWidth:true;onClicked:world.restoreEarth()}
                        Rectangle {height:1;Layout.fillWidth:true;color:"#37536b"}
                        HeaderText {text:"FORRÁS / BIZONYOSSÁG";color:root.muted}
                        Text{text:"FÖLDRAJZ: MINTAHELY";color:root.mint;font.bold:true;font.pixelSize:11}
                        Text{text:"NAPÁLLÁS: SZÁMÍTOTT";color:root.mint;font.bold:true;font.pixelSize:11}
                        Text{text:"IDŐJÁRÁS: KITALÁLT ADAT";color:root.amber;font.bold:true;font.pixelSize:11}
                        Text{text:"ÓRÁS HISTORIKUS ADAT: ISMERETLEN";color:root.muted;font.pixelSize:11}
                        Item {Layout.preferredHeight:12}
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth:true; Layout.preferredHeight:136;color:root.panel;radius:7;border.color:"#334b63"
            ColumnLayout {anchors.fill:parent;anchors.margins:12;spacing:8
                RowLayout {Layout.fillWidth:true
                    HeaderText {text:"ESEMÉNY-IDŐVONAL"}
                    Item {Layout.fillWidth:true}
                    AccentButton {text:"SHOT HANDOFF JSON";onClicked:handoffDialog.open()}
                }
                Repeater {model:[
                    {label:"NAP / ÉVSZAK",color:root.amber,desc:world.sky},
                    {label:"IDŐJÁRÁS",color:root.cyan,desc:world.rain.toFixed(0)+" mm/h · KITALÁLT"},
                    {label:"NARRATÍV",color:"#e99f78",desc:world.events}
                ];delegate:RowLayout {
                    required property var modelData
                    Layout.fillWidth:true;spacing:10
                    Text {text:modelData.label;color:modelData.color;Layout.preferredWidth:130;font.pixelSize:11;font.bold:true}
                    Rectangle {Layout.fillWidth:true;height:17;radius:4;color:Qt.darker(modelData.color,2.5)
                        Text{x:12;anchors.verticalCenter:parent.verticalCenter;text:modelData.desc;color:root.white;font.pixelSize:11;elide:Text.ElideRight;width:parent.width-24}
                    }
                }}
            }
        }
        RowLayout {
            Layout.fillWidth:true;Layout.preferredHeight:23
            Text {text:"●  "+world.status;color:root.mint;font.pixelSize:11;Layout.fillWidth:true;elide:Text.ElideRight}
            Text {text:"HRB: nincs helyi runtime-admission igazolás";color:root.muted;font.pixelSize:11}
        }
    }
    Dialog { id:approval;title:"Bolygószintű világszabály módosítása";modal:true;standardButtons:Dialog.Yes|Dialog.No
        anchors.centerIn: Overlay.overlay; width:490
        contentItem:Text {text:"Két valódi Napra változtatod a bolygót? Ez a földi napállás modelljének külön jóváhagyott felülírása.";wrapMode:Text.WordWrap;color:root.white;font.pixelSize:13}
        onAccepted:world.approveTwoSuns()
    }
    FileDialog {id:saveDialog;title:"FA3 világprojekt mentése";fileMode:FileDialog.SaveFile;nameFilters:["FA3 world (*.fa3world)"];onAccepted:world.save(selectedFile.toString().replace(/^file:\/\//,""))}
    FileDialog {id:openDialog;title:"FA3 világprojekt megnyitása";fileMode:FileDialog.OpenFile;nameFilters:["FA3 world (*.fa3world)"];onAccepted:world.load(selectedFile.toString().replace(/^file:\/\//,""))}
    FileDialog {id:handoffDialog;title:"Shot handoff JSON export";fileMode:FileDialog.SaveFile;nameFilters:["JSON (*.json)"];onAccepted:world.exportShot(selectedFile.toString().replace(/^file:\/\//,""))}
}
