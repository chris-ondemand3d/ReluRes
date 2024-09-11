import QtQuick

Rectangle {
    id: rootId
    width: 35
    height: 40
    property bool clickable: false 
    property color rectColor: rootId.clickable ? "skyblue" : "gray"
    property alias buttonText: buttonTextId.text
    signal buttonClicked(string text)

    border { color: "darkblue"; width : 3}
    function changeState(toVal) { 
        // console.log("enter")
        state = toVal ? "Clickable" : "Unclickable"
    } 
    
    Text {
        id: buttonTextId
        text: "Button"
        anchors.centerIn: parent
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            //console.log("Clicked on :"+ buttonTextId.text)
            if (rootId.clickable) rootId.buttonClicked(rootId.buttonText)
        }
    }

    state : "Unclickable"

    states: [
        State {
            name: "Clickable"
            PropertyChanges {
                target: rootId
                color: "skyblue"
                clickable: true
            }
        },
        State {
            name: "Unclickable"
            PropertyChanges {
                target: rootId
                color: "gray"
                clickable: false
            }
        },
        State {
            name: "Loaded"
            PropertyChanges {
                target: rootId
                color: "orange"
                clickable: true
            }
        }
    ]

}