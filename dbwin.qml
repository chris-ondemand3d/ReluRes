import QtQuick
import QtQuick.Window
import QtQuick.Controls
import Qt.labs.qmlmodels
import QtQuick.Layouts

ApplicationWindow {
    width: 640
    height: 1024
    visible: true
    title: qsTr("View Relu Result")

    ColumnLayout{
        id: mLayoutId

        HorizontalHeaderView {
            id: horizontalHeader
            syncView: tableViewId
            clip: true
            Layout.alignment: Qt.AlignCenter
        }
        
        ItemSelectionModel {
            id: selId
            model: tableViewId.model
                // onCurrentChanged: { console.log("current changed!") }
        }

        TableView {
            id: tableViewId
            width : 600
            height : 400
            Layout.alignment: Qt.AlignCenter

            //selectedRow = Signal(int)

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded 
            }

            columnSpacing: 1
            rowSpacing: 1
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            model: my_TableModel 
            selectionModel: selId

            delegate:  Rectangle {
                implicitWidth: 150
                implicitHeight: 32
                //anchors.fill: parent
                required property bool selected
                required property bool current

                Text {
                    text: model.display
                    wrapMode: Text.WrapAnywhere  //Wrapping text in itemDelegate
                    padding: 12
                }

                color: selected ? "yellow" : "#efefef"
                z: -1
                
                MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            tableViewId.selectionModel.select(tableViewId.model.index(index, 0),ItemSelectionModel.Select)
                            console.log(tableViewId.model.index(index,0).row)
                            //selectedRow.emit(tableViewId.model.index(index,0).row) 
                        }
                }
            }
            SelectionRectangle {
                target: tableViewId
            }  
        }

        GridLayout{
            id: mGridLayoutId
            Layout.alignment: Qt.AlignCenter

            columns: 3 

            MButton2 {
                id: ctId
                buttonText: "CT"
            }
            MButton2 {
                id: mandibleId
                buttonText: "Mandible"
            }
            MButton2 {
                id: maxillaryId
                buttonText: "Maxiilary"
            }
            MButton2 {
                id: upperId
                buttonText: "Upper"
            }
            MButton2 {
                id:leftSinusId
                buttonText: "Left Sinus"
            }
            MButton2 {
                id: rightSinusId
                buttonText: "Right Sinus"
            }
            MButton2 {
                id: lowerId
                buttonText: "Lower"
            }
            MButton2 {
                id: leftNerveId
                buttonText: "Left Nerve"
            }
            MButton2 {
                id: rightNerveId
                buttonText: "Right Nerve"
            }
        }
    
        GridLayout {
            id: mTeethGridLayoutId
            Layout.alignment: Qt.AlignCenter
            columns: 2

            RowLayout { 
                MButton {
                    id: tooth11Id
                    buttonText: "11"
                }
                MButton {
                    id: tooth12Id
                    buttonText: "12"
                }
                MButton {
                    id: tooth13Id
                    buttonText: "13"
                }
                MButton {
                    id: tooth14Id
                    buttonText: "14"
                }
                MButton {
                    id: tooth15Id
                    buttonText: "15"
                }
                MButton {
                    id: tooth16Id
                    buttonText: "16"
                }
                MButton {
                    id: tooth17Id
                    buttonText: "17"
                }
                MButton {
                    id: tooth18Id
                    buttonText: "18"
                }   
            }
            RowLayout { 
                MButton {
                    id: tooth21Id
                    buttonText: "21"
                }
                MButton {
                    id: tooth22Id
                    buttonText: "22"
                }
                MButton {
                    id: tooth23Id
                    buttonText: "23"
                }
                MButton {
                    id: tooth24Id
                    buttonText: "24"
                }
                MButton {
                    id: tooth25Id
                    buttonText: "25"
                }
                MButton {
                    id: tooth26Id
                    buttonText: "26"
                }
                MButton {
                    id: tooth27Id
                    buttonText: "27"
                }
                MButton {
                    id: tooth28Id
                    buttonText: "28"
                }   
            }
            RowLayout { 
                MButton {
                    id: tooth31Id
                    buttonText: "31"
                }
                MButton {
                    id: tooth32Id
                    buttonText: "32"
                }
                MButton {
                    id: tooth33Id
                    buttonText: "33"
                }
                MButton {
                    id: tooth34Id
                    buttonText: "34"
                }
                MButton {
                    id: tooth35Id
                    buttonText: "35"
                }
                MButton {
                    id: tooth36Id
                    buttonText: "36"
                }
                MButton {
                    id: tooth37Id
                    buttonText: "37"
                }
                MButton {
                    id: tooth38Id
                    buttonText: "38"
                }   
            }
            RowLayout { 
                MButton {
                    id: tooth41Id
                    buttonText: "41"
                }
                MButton {
                    id: tooth42Id
                    buttonText: "42"
                }
                MButton {
                    id: tooth43Id
                    buttonText: "43"
                }
                MButton {
                    id: tooth44Id
                    buttonText: "44"
                }
                MButton {
                    id: tooth45Id
                    buttonText: "45"
                }
                MButton {
                    id: tooth46Id
                    buttonText: "46"
                }
                MButton {
                    id: tooth47Id
                    buttonText: "47"
                }
                MButton {
                    id: tooth48Id
                    buttonText: "48"
                }   
            }
        }
    }
}