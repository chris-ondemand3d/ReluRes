# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

import pymongo
import os, glob, json

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import Qt, QObject, QFileInfo, QAbstractTableModel, QModelIndex, QDir, QUrl, qDebug, Signal, Slot, QRunnable, QThreadPool, Property

import DBwin

# Mongo Atlas URI
uri = "mongodb+srv://kaster:spain123@testaiguide.imucr3f.mongodb.net/?retryWrites=true&w=majority&appName=testAIGuide"

class TableModel(QAbstractTableModel):
    selected = Signal(int)
    COLUMN_NAMES = ["patient_ID", "patient_Name", "studyUID", "studyDate"]

    def __init__(self):
        QAbstractTableModel.__init__(self)
        #super(TableModel, self).__init__(parent)
        self.rows = []
    
    def rowCount(self, parent):
        return len(self.rows)

    def columnCount(self, parent):
        return len(self.COLUMN_NAMES)

    def fill_row(self, studies):
        for x in studies:
            self.rows.append(list(x.values())[1:])
            print(list(x.values()))

    def data(self, index, role=Qt.DisplayRole):
        """ Depending on the index and role given, return data. If not 
            returning data, return None (PySide equivalent of QT's 
            "invalid QVariant").
        """
        if not index.isValid():
            return None

        if not 0 <= index.row() < len(self.rows):
            return None
        """
        row = index.row()
        if (role <= Qt.UserRole):
            value = self.rows[row][index.column()]
        else:
            columnIdx = int(role) - int(Qt.UserRole) - 1
            #modelIndex = self.index(index.row(), columnIdx)
            #value = QAbstractTableModel.data(self,modelIndex,Qt.DisplayRole)
            value = self.rows[row][columnIdx]
        """
        
        #print(str(Qt.DisplayRole)+"Role: "+str(role))

        if role == Qt.DisplayRole:
            patient_id = self.rows[index.row()][0]
            patient_name = self.rows[index.row()][1]
            study_uid = self.rows[index.row()][2]
            study_date = self.rows[index.row()][3]

            if index.column() == 0:
                return patient_id
            elif index.column() == 1:
                return patient_name
            elif index.column() == 2:
                return study_uid
            elif index.column() == 3:
                return study_date
        
        return None

    def headerData(self, section, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        """ Set the headers to be displayed. """
        if role != Qt.DisplayRole:
            # print(str(Qt.DisplayRole)+"Role: "+str(role))
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return "Patient ID"
            elif section == 1:
                return "Patient Name"
            elif section == 2:
                return "Study UID"
            elif section == 3:
                return "Study Date"
        
        return None

    def nrow(self):
        return len(self.rows)    



if __name__ == "__main__":
    # qmlRegisterType<TableModel>("TableModel", 0, 1, "TableModel");

    app = QGuiApplication(sys.argv)

    try:    
        client = pymongo.MongoClient(uri)    
    # return a friendly error if a URI error is thrown     
    except pymongo.errors.ConfigurationError:    
        print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")    
        sys.exit(1)    

    # Send a ping to confirm a successful connection    
    try:    
        client.admin.command('ping')    
        print("Pinged your deployment. You successfully connected to MongoDB!")    
    except Exception as e:    
        print(e)    

    db = client['KorGuide']    
    collection = db['ReluRes']    

    # Saturate TableModel       
    results = collection.find({}, {"patient_id": 1, "patient_name": 1, "study_uid": 1, "study_date": 1, "_id": 1 })    
    allres = list(results)    
    my_TableModel = TableModel()    
    my_TableModel.fill_row(allres)    
    print(len(allres))    
    print(my_TableModel.nrow())            

    #qmlRegisterType(TableModel,"TableModel",1,0,'my_TableModel')    

    engine = QQmlApplicationEngine()    
    qml_file = Path(__file__).resolve().parent / "dbwin.qml"    
    engine.rootContext().setContextProperty("my_TableModel",my_TableModel)    
    engine.load(QUrl.fromLocalFile(os.path.abspath(qml_file)))    

    if not engine.rootObjects():    
        print("cannot create QML window")    
        sys.exit(-1)    


    sys.exit(app.exec())


