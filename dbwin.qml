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
            width : 750
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

            // selectionMode: tableViewId.SingleSelection
            // selectionBehavior: tableViewId.SelectRows

            delegate:  Rectangle {
                implicitWidth: 140
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
                            tableViewId.selectionModel.select(tableViewId.model.index(index, 0),ItemSelectionModel.ClearAndSelect | ItemSelectionModel.Current | ItemSelectionModel.Rows)
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


        RowLayout {
            id: inputLayoutId
            Layout.alignment: Qt.AlignCenter

            Button {
                id: segmentId
                width: 48; height: 24
                text: "Segment"
                onClicked: my_TableModel.segment()
            }
            Button {
                id: renderModeId
                width: 48; height: 24
                text: "Rendering Mode"
                onClicked: my_TableModel.rendermode()
            }
            Button {
                id: renderDirection
                width: 48; height: 24
                text: "Rendering Direction"
                onClicked: my_TableModel.renderDirection()
            }
            Button {
                id: captureId
                width: 48; height: 24
                text: "Capture"
                onClicked: my_TableModel.captureScreen()
            }

            TextInput {
                id: textInput1
                width: 200; height: 24
                focus: true
                text: ""
            }

            Button {
                id: saveId
                width: 48; height: 24
                text: "Save Comment"
                onClicked: my_TableModel.saveComment(textInput1.text)
            }
        }   


        function change_button_status(bList) {
            ctId.changeState(bList[0])
            mandibleId.changeState(bList[1])
            maxillaryId.changeState(bList[2])
            upperId.changeState(bList[3])
            leftSinusId.changeState(bList[4])
            rightSinusId.changeState(bList[5])
            lowerId.changeState(bList[6])
            leftNerveId.changeState(bList[7])
            rightNerveId.changeState(bList[8])
            tooth11Id.changeState(bList[9])
            tooth12Id.changeState(bList[10])
            tooth13Id.changeState(bList[11])
            tooth14Id.changeState(bList[12])
            tooth15Id.changeState(bList[13])
            tooth16Id.changeState(bList[14])
            tooth17Id.changeState(bList[15])
            tooth18Id.changeState(bList[16])
            tooth21Id.changeState(bList[17])
            tooth22Id.changeState(bList[18])
            tooth23Id.changeState(bList[19])
            tooth24Id.changeState(bList[20])
            tooth25Id.changeState(bList[21])
            tooth26Id.changeState(bList[22])
            tooth27Id.changeState(bList[23])
            tooth28Id.changeState(bList[24])
            tooth31Id.changeState(bList[25])
            tooth32Id.changeState(bList[26])
            tooth33Id.changeState(bList[27])
            tooth34Id.changeState(bList[28])
            tooth35Id.changeState(bList[29])
            tooth36Id.changeState(bList[30])
            tooth37Id.changeState(bList[31])
            tooth38Id.changeState(bList[32])
            tooth41Id.changeState(bList[33])
            tooth42Id.changeState(bList[34])
            tooth43Id.changeState(bList[35])
            tooth44Id.changeState(bList[36])
            tooth45Id.changeState(bList[37])
            tooth46Id.changeState(bList[38])
            tooth47Id.changeState(bList[39])
            tooth48Id.changeState(bList[40])
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