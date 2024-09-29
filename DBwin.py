import sys
import numpy
from pathlib import Path
import subprocess, time

import pymongo
import os, glob, json
from bson import ObjectId

from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import Qt, QObject, QFileInfo, QAbstractTableModel, QModelIndex, QDir, QUrl, qDebug, Signal, Slot, QRunnable, QThreadPool, Property
from PySide6.QtQuick import QQuickView

from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
# load implementations for rendering and interaction factory classes
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle
import QVTKRenderWindowInteractor as QVTK
QVTKRenderWindowInteractor = QVTK.QVTKRenderWindowInteractor
import ScanDirectory 

import vtk

if QVTK.PyQtImpl == 'PySide6':
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMainWindow

# Mongo Atlas URI
uri = "mongodb+srv://kaster:spain123@testaiguide.imucr3f.mongodb.net/?retryWrites=true&w=majority&appName=testAIGuide"

class TableModel(QAbstractTableModel):
    selected = Signal(int)
    changeButtonStatus = Signal(list)
    clickedButton = Signal(str)
    segment = Signal()
    rendermode = Signal()
    captureScreen = Signal()
    saveComment = Signal(str)

    COLUMN_NAMES = ["patient_ID", "patient_Name", "studyUID", "studyDate", "Comment"]

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
            #print(list(x.values())[1:])

    def data(self, index, role=Qt.DisplayRole):
        """ Depending on the index and role given, return data. If not 
            returning data, return None (PySide equivalent of QT's 
            "invalid QVariant").
        """
        if not index.isValid():
            return None

        if not 0 <= index.row() < len(self.rows):
            return None
        
        #print(str(Qt.DisplayRole)+"Role: "+str(role))

        if role == Qt.DisplayRole:
            patient_id = self.rows[index.row()][0]
            patient_name = self.rows[index.row()][1]
            study_uid = self.rows[index.row()][2]
            study_date = self.rows[index.row()][3]
            comment = self.rows[index.row()][4]
            if index.column() == 0:
                return patient_id
            elif index.column() == 1:
                return patient_name
            elif index.column() == 2:
                return study_uid
            elif index.column() == 3:
                return study_date
            elif index.column() == 4:
                return comment
            
        
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
            elif section == 4:
                return "Comment"
        
        return None



class MAINApp(QQuickView):
    
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

        self.screenshotCount = 0
        self.rendermode = 3
        self.makeNifti = True

        # Saturate TableModel   
        results = self.collection.find({}, {"patient_id": 1, "patient_name": 1, "study_uid": 1, "study_date": 1, "comment": 1, "_id": 1 })
        self.allres = list(results)
        #print(self.allres)
        self.my_TableModel = TableModel()
        self.my_TableModel.fill_row(self.allres)

        self.rootContext().setContextProperty("my_TableModel",self.my_TableModel)
        _win_source = QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), 'dbwin.qml'))
        self.setSource(_win_source)

        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.setTitle("Relu Result Viewer")
        self.resize(640, 960)
        self.setPosition(40,40)
        #self.setProperty("x",40)
        #self.setProperty("y",40)

        self.window = QMainWindow()
        self.window.resize(960,960)
        self.widget = QVTKRenderWindowInteractor(self.window)
        self.window.setCentralWidget(self.widget)
        self.ren = vtkRenderer()
        self.widget.GetRenderWindow().AddRenderer(self.ren)
        self.ren.SetUseDepthPeeling(True)
        self.ren.UseDepthPeelingForVolumesOn()

        # show the widget
        self.window.move(680,10)
        self.window.show()

        self.istyle = vtk.vtkInteractorStyleTrackballCamera()
        self.widget._Iren.SetInteractorStyle(self.istyle)

        self.widget.Initialize()
        self.widget.Start()

        # models 
        self.nModel = 0
        self.volume = None
        self.mandible = None
        self.maxilla = None
        self.upper = None
        self.lower = None
        self.lSinus = None
        self.rSinus = None
        self.lNerve = None
        self.rNerve = None

        # Connect TableView.selectedRow to fill_study
        self.my_TableModel.selected.connect(self.set_buttons_status)
        self.my_TableModel.clickedButton.connect(self.add_model)
        self.my_TableModel.segment.connect(self.segment)
        self.my_TableModel.rendermode.connect(self.renderMode)
        self.my_TableModel.captureScreen.connect(self.captureScreen)
        self.my_TableModel.saveComment.connect(self.saveComment)

    @Slot(int) #TableView selectedRow(int) signal handler
    def set_buttons_status(self, row=0):
        """ Find row in allres and emit signals to fill text(patientName,StudyDate), 
            to list of 9 bool's, 32 bool's to on/off button """

        filter={
            '_id': ObjectId(self.allres[row]['_id'])
        }
        results = self.collection.find( filter=filter )
        res = list(results)
        self.currentRow = res[0]
        #print(self.currentRow['_id'])

        #Clean up the model
        self.nModel = 0
        if (self.volume): 
            self.ren.RemoveVolume(self.volume)
            self.volume = None
        if (self.mandible):
            self.mandible = None
            self.ren.RemoveActor(self.mandibleActor)
        if (self.maxilla):
            self.maxilla = None
            self.ren.RemoveActor(self.maxillaActor)
        if (self.upper):
            self.upper = None
            self.ren.RemoveActor(self.upperActor)
        if (self.lower):
            self.lower = None
            self.ren.RemoveActor(self.lowerActor)
        if (self.lSinus): 
            self.lSinus = None
            self.ren.RemoveActor(self.lSinusActor)
        if (self.rSinus): 
            self.rSinus = None
            self.ren.RemoveActor(self.rSinusActor)
        if (self.lNerve): 
            self.lNerve = None
            self.ren.RemoveActor(self.lNerveActor)
        if (self.rNerve):
            self.rNerve = None
            self.ren.RemoveActor(self.rNerveActor)
   
        # Make 
        print(res[0]['patient_name'], res[0]['study_date'])
        self.buttonStatus = [0] * 41

        if (os.path.exists(os.path.join(res[0]['path'],'cvt'))): 
            print(os.path.join(res[0]['path'],'cvt'))
            self.buttonStatus[0]=1
        if (len(res[0]['lower_path'])!=0 and os.path.exists(res[0]['lower_path'])): 
            print(res[0]['lower_path'])
            self.buttonStatus[6]=1
        if (len(res[0]['upper_path'])!=0 and os.path.exists(res[0]['upper_path'])): 
            print(res[0]['upper_path'])
            self.buttonStatus[3]=1
        if (len(res[0]['mandible_path'])!=0 and os.path.exists(res[0]['mandible_path'])): 
            print(res[0]['mandible_path'])
            self.buttonStatus[1]=1
        if (len(res[0]['maxilla_path'])!=0 and os.path.exists(res[0]['maxilla_path'])):
            print(res[0]['maxilla_path'])
            self.buttonStatus[2]=1
        if (len(res[0]['left_sinus_path'])!=0 and os.path.exists(res[0]['left_sinus_path'])): 
            print(res[0]['left_sinus_path'])
            self.buttonStatus[4]=1
        if (len(res[0]['right_sinus_path'])!=0 and os.path.exists(res[0]['right_sinus_path'])): 
            print(res[0]['right_sinus_path'])
            self.buttonStatus[5]=1
        if (len(res[0]['left_nerve_path'])!=0 and os.path.exists(res[0]['left_nerve_path'])): 
            print(res[0]['left_nerve_path'])
            self.buttonStatus[7]=1
        if (len(res[0]['right_nerve_path'])!=0 and os.path.exists(res[0]['right_nerve_path'])): 
            print(res[0]['right_nerve_path'])
            self.buttonStatus[8]=1

        print (self.buttonStatus)

        teeth_list =  res[0]['teeth']

        i=9
        for x in teeth_list: # for each teeth number, missing, toothpath
            #print(x["missing"], x["number"], x["tooth_path"])
            if (not x["missing"] and os.path.exists(x["tooth_path"])):
                print(i,x["missing"], x["number"], x["tooth_path"])
                self.buttonStatus[i]=1
            i+=1

        print (self.buttonStatus)

        self.my_TableModel.changeButtonStatus.emit(self.buttonStatus)


    @Slot(str)
    def add_model(self, name):
        print(name + " Clicked! ")   
        # in case name = 'ct'
        if (name == 'CT'):
            if (self.buttonStatus[0]==1):
                # load_ct_data
                if (self.volume==None): 
                    if self.makeNifti:
                        outdir = os.path.join(self.currentRow['path'],'segment')
                        if not os.path.exists(outdir):
                            os.makedirs(outdir)
                self.min_npV, self.max_npV, self.adjThresholds, self.volume = ScanDirectory.load_dicom(os.path.join(self.currentRow['path'],'cvt'), 3, self.makeNifti)
                self.ren.AddVolume(self.volume)
                self.buttonStatus[0]=2
                self.nModel+=1
            elif (self.buttonStatus[0]==2):
                # hide volume and 
                self.ren.RemoveVolume(self.volume)
                self.buttonStatus[0]=1    
        elif (name == "Mandible"):    
            # Handle Mandible button click
            if (self.buttonStatus[1]==1):
                # load mandible.stl
                if (self.mandible==None):
                    self.nModel+=1
                    reader = vtk.vtkSTLReader()
                    reader.SetFileName(self.currentRow['mandible_path'])
                    reader.MergingOn()
                    reader.Update()
                    self.mandible = reader.GetOutput()
                    print("Open "+self.currentRow['mandible_path'])                    
                self.mandibleMapper = vtkPolyDataMapper()
                self.mandibleMapper.SetInputDataObject(self.mandible)
                self.mandibleActor = vtkActor()
                self.mandibleActor.GetProperty().SetOpacity(0.3)
                self.mandibleActor.SetMapper(self.mandibleMapper)
                self.ren.AddActor(self.mandibleActor)
                self.buttonStatus[1]=2
            elif (self.buttonStatus[1]==2):
                # hide mandible.stl
                self.ren.RemoveActor(self.mandibleActor)
                self.buttonStatus[1]=1
        elif (name == "Maxiilary"):    
            if self.buttonStatus[2] == 1:
                if (self.maxilla==None):
                    self.nModel+=1
                    # load maxilla.stl
                    reader = vtk.vtkSTLReader()
                    reader.SetFileName(self.currentRow['maxilla_path'])
                    reader.MergingOn()
                    reader.Update()
                    self.maxilla = reader.GetOutput()
                    print("Open " + self.currentRow['maxilla_path'])
                self.maxillaMapper = vtkPolyDataMapper()
                self.maxillaMapper.SetInputDataObject(self.maxilla)
                self.maxillaActor = vtkActor()
                self.maxillaActor.SetMapper(self.maxillaMapper)
                self.maxillaActor.GetProperty().SetOpacity(0.3)
                self.ren.AddActor(self.maxillaActor)
                self.buttonStatus[2] = 2
            elif self.buttonStatus[2] == 2:
                # hide maxilla.stl
                self.ren.RemoveActor(self.maxillaActor)
                self.buttonStatus[2] = 1 
        elif (name == "Upper"):
            if self.buttonStatus[3] == 1:
                if (self.upper == None):
                    self.nModel+=1
                    # load upper.stl
                    reader = vtk.vtkSTLReader()
                    reader.SetFileName(self.currentRow['upper_path'])
                    reader.MergingOn()
                    reader.Update()
                    self.upper = reader.GetOutput()
                    print("Open " + self.currentRow['upper_path'])
                self.upperMapper = vtkPolyDataMapper()
                self.upperMapper.SetInputDataObject(self.upper)
                self.upperActor = vtkActor()
                self.upperActor.SetMapper(self.upperMapper)
                self.upperActor.GetProperty().SetOpacity(0.3)
                self.ren.AddActor(self.upperActor)
                self.buttonStatus[3] = 2
            elif self.buttonStatus[3] == 2:
                # hide upper.stl
                self.ren.RemoveActor(self.upperActor)
                self.buttonStatus[3] = 1                
        elif (name == "Left Sinus"):    
                if self.buttonStatus[4] == 1:
                    if (self.lSinus==None):
                        self.nModel+=1
                        reader = vtk.vtkSTLReader()
                        reader.SetFileName(self.currentRow['left_sinus_path'])
                        reader.MergingOn()
                        reader.Update()
                        self.lSinus = reader.GetOutput()
                        print("Open " + self.currentRow['left_sinus_path'])
                    self.lSinusMapper = vtkPolyDataMapper()
                    self.lSinusMapper.SetInputDataObject(self.lSinus)
                    self.lSinusActor = vtkActor()
                    self.lSinusActor.SetMapper(self.lSinusMapper)
                    self.ren.AddActor(self.lSinusActor)
                    self.buttonStatus[4] = 2
                elif self.buttonStatus[4] == 2:
                    self.ren.RemoveActor(self.lSinusActor)
                    self.buttonStatus[4] = 1
        elif (name == "Right Sinus"):    
                if self.buttonStatus[5] == 1:
                    if (self.rSinus==None):
                        self.nModel+=1
                        reader = vtk.vtkSTLReader()
                        reader.SetFileName(self.currentRow['right_sinus_path'])
                        reader.MergingOn()
                        reader.Update()
                        self.rSinus = reader.GetOutput()
                        print("Open " + self.currentRow['right_sinus_path'])
                    self.rSinusMapper = vtkPolyDataMapper()
                    self.rSinusMapper.SetInputDataObject(self.rSinus)
                    self.rSinusActor = vtkActor()
                    self.rSinusActor.SetMapper(self.rSinusMapper)
                    self.ren.AddActor(self.rSinusActor)
                    self.buttonStatus[5] = 2
                elif self.buttonStatus[5] == 2:
                    self.ren.RemoveActor(self.rSinusActor)
                    self.buttonStatus[5] = 1 
        elif (name == "Lower"):    
                if self.buttonStatus[6] == 1:
                    if (self.lower == None):
                        self.nModel+=1
                        reader = vtk.vtkSTLReader()
                        reader.SetFileName(self.currentRow['lower_path'])
                        reader.MergingOn()
                        reader.Update()
                        self.lower = reader.GetOutput()
                        print("Open " + self.currentRow['lower_path'])
                    self.lowerMapper = vtkPolyDataMapper()
                    self.lowerMapper.SetInputDataObject(self.lower)
                    self.lowerActor = vtkActor()
                    self.lowerActor.SetMapper(self.lowerMapper)
                    self.lowerActor.GetProperty().SetOpacity(0.3)
                    self.ren.AddActor(self.lowerActor)
                    self.buttonStatus[6] = 2
                elif self.buttonStatus[6] == 2:
                    self.ren.RemoveActor(self.lowerActor)
                    self.buttonStatus[6] = 1
        elif (name == "Left Nerve"):    
                if self.buttonStatus[7] == 1:
                    if (self.lNerve == None):
                        self.nModel+=1
                        reader = vtk.vtkSTLReader()
                        reader.SetFileName(self.currentRow['left_nerve_path'])
                        reader.MergingOn()
                        reader.Update()
                        self.lNerve = reader.GetOutput()
                        print("Open " + self.currentRow['left_nerve_path'])
                    self.lNerveMapper = vtkPolyDataMapper()
                    self.lNerveMapper.SetInputDataObject(self.lNerve)
                    self.lNerveActor = vtkActor()
                    self.lNerveActor.SetMapper(self.lNerveMapper)
                    self.ren.AddActor(self.lNerveActor)
                    self.buttonStatus[7] = 2
                elif self.buttonStatus[7] == 2:
                    self.ren.RemoveActor(self.lNerveActor)
                    self.buttonStatus[7] = 1  
        elif (name == "Right Nerve"):
                if self.buttonStatus[8] == 1:
                    if (self.rNerve==None):
                        self.nModel+=1
                        reader = vtk.vtkSTLReader()
                        reader.SetFileName(self.currentRow['right_nerve_path'])
                        reader.MergingOn()
                        reader.Update()
                        self.rNerve = reader.GetOutput()
                        print("Open " + self.currentRow['right_nerve_path'])
                    self.rNerveMapper = vtkPolyDataMapper()
                    self.rNerveMapper.SetInputDataObject(self.rNerve)
                    self.rNerveActor = vtkActor()
                    self.rNerveActor.SetMapper(self.rNerveMapper)
                    self.ren.AddActor(self.rNerveActor)
                    self.buttonStatus[8] = 2
                elif self.buttonStatus[8] == 2:
                    self.ren.RemoveActor(self.rNerveActor)
                    self.buttonStatus[8] = 1

        self.my_TableModel.changeButtonStatus.emit(self.buttonStatus)        

        #DICOM is LPS (to L to P to Superior)
        # from Anterior to Posterior Viewpoint, DICOM is LPS
        if (self.nModel == 1):
            # 1st entering, setup camera   
            fp = numpy.array(self.ren.GetActiveCamera().GetFocalPoint())
            p = numpy.array(self.ren.GetActiveCamera().GetPosition())
            dist = self.ren.GetActiveCamera().GetDistance()
            print(fp,p,dist)
            # from Anterior 
            self.ren.GetActiveCamera().SetPosition(fp[0], fp[1] - dist, fp[2])
            self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0);
            # from Left
            #self.ren.GetActiveCamera().SetPosition(fp[0]+dist, fp[1], fp[2])
            #self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0);
            # from Head
            #self.ren.GetActiveCamera().SetPosition(fp[0], fp[1], fp[2]+dist)
            #self.ren.GetActiveCamera().SetViewUp(0.0, 1.0, 0.0);
            self.ren.GetActiveCamera().ParallelProjectionOn()
            self.ren.GetActiveCamera().GetViewTransformMatrix()
            #print(self.ren.GetActiveCamera().GetViewTransformMatrix())
            self.ren.ResetCameraClippingRange()
            self.ren.ResetCamera()

            # world coordinate bounding box () - (x1,y1,z1,x2,y2,z2)->(x1,y2,z1),(x2,y1,z1),(x2,y2,z1), (x1,y1,z2), (x1,y2,z2), (x2,y1,z2)
            #print(self.window.)
            print("Renderwindow size:",self.widget.GetRenderWindow().GetSize())
            xy = self.volume.GetBounds()
            print(xy)
            coordinate = vtk.vtkCoordinate()
            coordinate.SetCoordinateSystemToWorld()
            coordinate.SetValue(xy[0],xy[2],xy[4])
            #coordinate.SetValue(xy[1],xy[3],xy[5])
            #coordinate.SetValue(-55.313, -52.437, -33.75)
            viewCoord = coordinate.GetComputedViewportValue(self.ren)
            dispCoord = coordinate.GetComputedDisplayValue(self.ren)
            print(viewCoord, dispCoord) 

        self.widget.update()

    @Slot()
    def segment(self):
        print("segment")

        # Define your directories
        input_dir = os.path.join(self.currentRow['path'],'segment')
        output_dir = os.path.join(self.currentRow['path'],'output')
        os.makedirs(output_dir, exist_ok=True)
        if os.path.exists(output_dir) and os.path.exists(input_dir):
            start_time = time.time()

            os.environ['nnUNet_raw'] = '.'
            os.environ['nnUNet_results'] = '.'
            os.environ['nnUNet_preprocessed'] = '.'

            # Command to run the nnUNetv2_predict script
            nnunet_command = (
                f"nnUNetv2_predict -i {input_dir}/ -o {output_dir}/ "
                "-d Dataset111_453CT -tr nnUNetTrainer -p nnUNetPlans "
                "-c 3d_fullres -f 0 -npp 1 -nps 1 -step_size 0.5 -device cuda --disable_tta"
            )
            # Execute the command
            subprocess.run(nnunet_command, shell=True) #, executable="/bin/bash"
            end_time = time.time()
            print("segmentation time:", end_time-start_time)
        else:
            print("Error, directories not exist")


    @Slot()
    def renderMode(self):
        print("Rendering Mode")
        opacityWindow = 2048 #(max_npV-min_npV)/4.0
        opacityLevel = 1024 #(max_npV-min_npV)/2.0

        mapper = self.volume.GetMapper()
        property = self.volume.GetProperty()
        colorFun = vtk.vtkColorTransferFunction()
        opacityFun = vtk.vtkPiecewiseFunction()
        gradientFun = vtk.vtkPiecewiseFunction()

        if self.rendermode == 3: # Rendering 5 and change mode
            colorFun.AddRGBPoint(self.min_npV, 0.3, 0.3, 1.0, 0.5, 0.0)
            colorFun.AddRGBPoint(self.adjThresholds[0], 0.95, 0.95, 0.85, 0.5, 0.0)
            colorFun.AddRGBPoint((self.adjThresholds[0]+self.adjThresholds[2])/2, 0.75, 0.4, 0.35, 0.5, 0.0)
            colorFun.AddRGBPoint(self.adjThresholds[2], .95, .84, .19, .5, 0.0)
            colorFun.AddRGBPoint(self.max_npV, 0.78, 0.78, 0.92, .5, 0.0)
      
            width_s=80
            opacityFun.AddPoint(self.min_npV, 0, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            # Right
            opacityFun.AddPoint(self.adjThresholds[1], 0, .5, .0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            opacityFun.AddPoint(self.adjThresholds[2], 0.5, .5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            opacityFun.AddPoint(self.max_npV, .75, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            
            
            gradientFun.AddPoint(self.min_npV, 1.0, 0.5,.0)
            gradientFun.AddPoint(self.min_npV + (self.max_npV-self.min_npV)*0.2,.0,0.5,.0)
            #gradientFun.AddPoint(28.,.0,0.0,.0)
            gradientFun.AddPoint(self.max_npV,1.0,0.5,.0)

            property.ShadeOn()
            mapper.SetBlendModeToComposite()
            property.SetAmbient(0.2)
            property.SetDiffuse(1.0)
            property.SetSpecular(0.0)
            property.SetSpecularPower(1.0)
            property.SetScalarOpacityUnitDistance(0.8919)    
            self.rendermode = 5

        elif self.rendermode == 5: # Rendering 1 and change mode
            colorFun.AddRGBSegment(0.0, 1.0, 1.0, 1.0, 255.0, 1.0, 1.0, 1.0)
            opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0, opacityLevel + 0.5 * opacityWindow, 1.0)
            mapper.SetBlendModeToMaximumIntensity()            
            self.rendermode = 1

        elif self.rendermode == 1: # Rendering 3 and change mode
            width_s=80
            width_l=160

            colorFun.AddRGBPoint(self.min_npV, 0.3, 0.3, 1.0, 0.5, 0.0)
            colorFun.AddRGBPoint(self.adjThresholds[0], 0.95, 0.95, 0.85, 0.5, 0.0)
            colorFun.AddRGBPoint((self.adjThresholds[0]+self.adjThresholds[2])/2, 0.75, 0.4, 0.35, 0.5, 0.0)
            colorFun.AddRGBPoint(self.adjThresholds[2], .95, .84, .19, .5, 0.0)
            colorFun.AddRGBPoint(self.max_npV, 0.78, 0.78, 0.92, .5, 0.0)
        
            opacityFun.AddPoint(self.min_npV, 0, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            # Right
            opacityFun.AddPoint(self.adjThresholds[0], .0, .5, .0)
            opacityFun.AddPoint(self.adjThresholds[0]+width_s/2.0, 0.5, .5, .0)
            opacityFun.AddPoint(self.adjThresholds[0]+width_s, 0.0, .5, .0)
            opacityFun.AddPoint(self.adjThresholds[1], 0, .5, .0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            opacityFun.AddPoint(self.adjThresholds[2], 0.5, .5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            opacityFun.AddPoint(self.max_npV, .75, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
            
            gradientFun.AddPoint(self.min_npV, 1.0, 0.5,.0)
            gradientFun.AddPoint(self.min_npV + (self.max_npV-self.min_npV)*0.2,.0,0.5,.0)
            #gradientFun.AddPoint(28.,.0,0.0,.0)
            gradientFun.AddPoint(self.max_npV,1.0,0.5,.0)

            property.ShadeOn()
            mapper.SetBlendModeToComposite()
            property.SetAmbient(0.2)
            property.SetDiffuse(1.0)
            property.SetSpecular(0.0)
            property.SetSpecularPower(1.0)
            property.SetScalarOpacityUnitDistance(0.8919)             
            self.rendermode = 3
        
        property.SetColor(colorFun)
        property.SetScalarOpacity(opacityFun)
        #property.SetGradientOpacity(gradientFun)
        self.widget.update()

    @Slot()
    def captureScreen(self):
        print("Capture")
        winToImageFilter = vtk.vtkWindowToImageFilter()
        winToImageFilter.SetInput(self.widget.GetRenderWindow())
        winToImageFilter.Update()
        scrFileName = "scr_%d%d.png" % (self.rendermode, self.screenshotCount)
        print("Save to ",scrFileName)
        self.screenshotCount += 1
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(scrFileName)
        writer.SetInputData(winToImageFilter.GetOutput())
        writer.Write()

    @Slot(str)
    def saveComment(self, commentText):
        print("saveComment")
        if len(commentText) != 0:
            # self.currentRow = objid in mongodb
            # update comment 
            self.collection.update_one( { "_id": ObjectId(self.currentRow['_id'])}, [ { "$set" : { "comment": commentText } }] )