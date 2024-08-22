# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

import pymongo
from bson import ObjectId
import os, glob, json

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import Qt, QObject, QFileInfo, QAbstractTableModel, QModelIndex, QDir, QUrl, qDebug, Signal, Slot, QRunnable, QThreadPool, Property
from PySide6.QtQuick import QQuickView

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


    #_win_source = QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), 'dbwin.qml'))

class MAINApp(QObject):
    
    def __init__(self, exec_param=None, *args, **kwds):
        super().__init__(*args, **kwds)
        
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

        self.db = client['KorGuide']
        self.collection = self.db['ReluRes']

        # Saturate TableModel   
        results = self.collection.find({}, {"patient_id": 1, "patient_name": 1, "study_uid": 1, "study_date": 1, "_id": 1 })
        self.allres = list(results)
        my_TableModel = TableModel()
        my_TableModel.fill_row(self.allres)
        print(len(self.allres))
        print(my_TableModel.nrow())

        
        #qmlRegisterType(TableModel,"TableModel",1,0,'my_TableModel')

        engine = QQmlApplicationEngine()
        qml_file = Path(__file__).resolve().parent / "dbwin.qml"
        engine.rootContext().setContextProperty("my_TableModel",my_TableModel)
        engine.load(QUrl.fromLocalFile(os.path.abspath(qml_file)))

        if not engine.rootObjects():
            print("cannot create QML window")
            sys.exit(-1)

        # Connect 
        # Connect TableView.selectedRow to fill_study
        #my_TableModel.selected.connect(self.fill_study)        


    @Slot(int) #TableView selectedRow(int) signal handler
    def fill_study(self, row=0):
        """ Find row in allres and emit signals to fill text(patientName,StudyDate), 
            to list of 9 bool's, 32 bool's to on/off button """
        print (self.allres[row]['_id'])

        filter={
            '_id': ObjectId(self.allres[row]['_id'])
        }
        result = self.collection.find( filter=filter )
        print (result)

        # Make 
        print(result['patient_name'], result['study_date'])
        if (os.path.exists(os.path.join(result['path'],'cvt'))): print(os.path.join(result['path'],'cvt'))
        if (os.path.exists(result['lower_path'])): print(result['lower_path'])
        if (os.path.exists(result['upper_path'])): print(result['upper_path'])
        if (os.path.exists(result['mandible_path'])): print(result['mandible_path'])
        if (os.path.exists(result['maxillary_path'])): print(result['maxillary_path'])
        if (os.path.exists(result['left_sinus_path'])): print(result['left_sinus_path'])
        if (os.path.exists(result['right_sinus_path'])): print(result['right_sinus_path'])
        if (os.path.exists(result['left_nerve_path'])): print(result['left_nerve_path'])
        if (os.path.exists(result['right_nerve_path'])): print(result['right_nerve_path'])

        teeth_list =  result['teeth']
        print(teeth_list)
        for x in teeth_list: # for each teeth number, missing, toothpath
            print(x["missing"], x["number"], x["tooth_path"])









    


