import QtQuick
import QtQuick.Window
import QtQuick.Controls
import Qt.labs.qmlmodels
import QtQuick.Layouts
// import my_TableModel

Item {
    
    id:rootId

    ColumnLayout{
        id: mLayoutId

        signal clickedButton(string name)

        HorizontalHeaderView {
            id: horizontalHeader
            syncView: tableViewId
            clip: true
            Layout.alignment: Qt.AlignCenter
        }

        TableView {
            id: tableViewId
            width : 600
            height : 400
            Layout.alignment: Qt.AlignCenter

            signal selectedRow(int row)

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded 
            }

            columnSpacing: 1
            rowSpacing: 1
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            model: my_TableModel 
            
            selectionModel: ItemSelectionModel {
                id: selId
                model: tableViewId.model
            }

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
                            tableViewId.selectedRow(tableViewId.model.index(index,0).row) 
                        }
                }
            }
            SelectionRectangle {
                target: tableViewId
            }
            Component.onCompleted: {
                //Connect a signal to another signal
                tableViewId.selectedRow.connect(my_TableModel.selected)
            }
        }

        GridLayout {
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
        
        function change_button_status(bList) {
            if (bList[0]) ctId.changeState(bList[0])
            if (bList[1]) mandibleId.changeState(bList[1])
            if (bList[2]) maxillaryId.changeState(bList[2])
            if (bList[3]) upperId.changeState(bList[3])
            if (bList[4]) leftSinusId.changeState(bList[4])
            if (bList[5]) rightSinusId.changeState(bList[5])
            if (bList[6]) lowerId.changeState(bList[6])
            if (bList[7]) leftNerveId.changeState(bList[7])
            if (bList[8]) rightNerveId.changeState(bList[8])
            if (bList[9]) tooth11Id.changeState(bList[9])
            if (bList[10]) tooth12Id.changeState(bList[10])
            if (bList[11]) tooth13Id.changeState(bList[11])
            if (bList[12]) tooth14Id.changeState(bList[12])
            if (bList[13]) tooth15Id.changeState(bList[13])
            if (bList[14]) tooth16Id.changeState(bList[14])
            if (bList[15]) tooth17Id.changeState(bList[15])
            if (bList[16]) tooth18Id.changeState(bList[16])
            if (bList[17]) tooth21Id.changeState(bList[17])
            if (bList[18]) tooth22Id.changeState(bList[18])
            if (bList[19]) tooth23Id.changeState(bList[19])
            if (bList[20]) tooth24Id.changeState(bList[20])
            if (bList[21]) tooth25Id.changeState(bList[21])
            if (bList[22]) tooth26Id.changeState(bList[22])
            if (bList[23]) tooth27Id.changeState(bList[23])
            if (bList[24]) tooth28Id.changeState(bList[24])
            if (bList[25]) tooth31Id.changeState(bList[25])
            if (bList[26]) tooth32Id.changeState(bList[26])
            if (bList[27]) tooth33Id.changeState(bList[27])
            if (bList[28]) tooth34Id.changeState(bList[28])
            if (bList[29]) tooth35Id.changeState(bList[29])
            if (bList[30]) tooth36Id.changeState(bList[30])
            if (bList[31]) tooth37Id.changeState(bList[31])
            if (bList[32]) tooth38Id.changeState(bList[32])
            if (bList[33]) tooth41Id.changeState(bList[33])
            if (bList[34]) tooth42Id.changeState(bList[34])
            if (bList[35]) tooth43Id.changeState(bList[35])
            if (bList[36]) tooth44Id.changeState(bList[36])
            if (bList[37]) tooth45Id.changeState(bList[37])
            if (bList[38]) tooth46Id.changeState(bList[38])
            if (bList[39]) tooth47Id.changeState(bList[39])
            if (bList[40]) tooth48Id.changeState(bList[40])
            console.log(bList)
        }

        function onBtnClicked(bText) {
            console.log(bText + "Clicked")
            mLayoutId.clickedButton(bText)
        }

        Component.onCompleted: {
            my_TableModel.changeButtonStatus.connect(mLayoutId.change_button_status)
            mLayoutId.clickedButton.connect(my_TableModel.clickedButton)
            // for each 41 button
            ctId.buttonClicked.connect(mLayoutId.onBtnClicked)
            mandibleId.buttonClicked.connect(mLayoutId.onBtnClicked)
            maxillaryId.buttonClicked.connect(mLayoutId.onBtnClicked)
            upperId.buttonClicked.connect(mLayoutId.onBtnClicked)
            leftSinusId.buttonClicked.connect(mLayoutId.onBtnClicked)
            rightSinusId.buttonClicked.connect(mLayoutId.onBtnClicked)
            lowerId.buttonClicked.connect(mLayoutId.onBtnClicked)
            leftNerveId.buttonClicked.connect(mLayoutId.onBtnClicked)
            rightNerveId.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth11Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth12Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth13Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth14Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth15Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth16Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth17Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth18Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth21Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth22Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth23Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth24Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth25Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth26Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth27Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth28Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth31Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth32Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth33Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth34Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth35Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth36Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth37Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth38Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth41Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth42Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth43Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth44Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth45Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth46Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth47Id.buttonClicked.connect(mLayoutId.onBtnClicked)
            tooth48Id.buttonClicked.connect(mLayoutId.onBtnClicked)
        }
    }
}