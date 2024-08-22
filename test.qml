import QtQuick
import QtQuick.Window
import QtQuick.Controls
import Qt.labs.qmlmodels
import QtQuick.Layouts

Window {
    width: 640
    height: 1024
    visible: true
    title: qsTr("View Relu Result")

    GridLayout{
        id: mGridLayoutId
        columns: 2 
        // anchors.fill: parent
        anchors.left: parent.left
        anchors.right: parent.right
        
        MButton2 {
            id: button1Id
            buttonText: "Button1"
            Layout.alignment: Qt.AlignHCenter
        }

        MButton2 {
            id: button2Id
            buttonText: "Button2"
            onButtonClicked: {
                console.log("Clicked on button2")
            }
            Layout.alignment: Qt.AlignHCenter
        }

        MButton2 {
            id: button3Id
            buttonText: "Button3"
            onButtonClicked: {
                console.log("Clicked on button3")
            }
            Layout.alignment: Qt.AlignHCenter
        }

        MButton2 {
            id: button4Id
            buttonText: "Button4"
            onButtonClicked: {
                console.log("Clicked on button4")
            }
            Layout.alignment: Qt.AlignHCenter
        }

        function onbuttonClicked(bText) { console.log(bText + "Clicked") }

/*  Move outside GridLayout   
        Button {
            id: buttonId
            text: "Click me!"
            signal change_click(bool toVal)
            onClicked : { change_click(true) }
        }
        
        Component.onCompleted: {
            buttonId.change_click.connect(button1Id.change)
        }
*/
    }

    Button {
        id: buttonId
        text: "Click me!"
        signal change_click(bool toVal)
        onClicked : { change_click(true) }
    }
        
    Component.onCompleted: {
        buttonId.change_click.connect(button1Id.changeState)
        button1Id.buttonClicked.connect(mGridLayoutId.onbuttonClicked)
    }

}
