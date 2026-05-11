import sys
import numpy
import subprocess, time
from PIL import Image as im

import pymongo
import os
from bson import ObjectId

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QUrl, Signal, Slot
from PySide6.QtQuick import QQuickView

from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer
import vtkmodules.vtkRenderingOpenGL2
import vtkmodules.vtkInteractionStyle
import vtkmodules.util.numpy_support
import QVTKRenderWindowInteractor as QVTK
QVTKRenderWindowInteractor = QVTK.QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionWidgets import vtkBoxWidget
import ScanDirectory

import vtk
import nibabel as nib

if QVTK.PyQtImpl == 'PySide6':
    from PySide6.QtWidgets import QApplication, QMainWindow

uri = os.environ.get("MONGO_URI")
if not uri:
    raise RuntimeError("MONGO_URI environment variable is not set")

# (mongo_path_field, buttonStatus_index, stl_opacity)
_STL_MODELS = {
    "Mandible":    ("mandible_path",    1, 0.3),
    "Maxiilary":   ("maxilla_path",     2, 0.3),
    "Upper":       ("upper_path",       3, 0.3),
    "Left Sinus":  ("left_sinus_path",  4, 1.0),
    "Right Sinus": ("right_sinus_path", 5, 1.0),
    "Lower":       ("lower_path",       6, 0.3),
    "Left Nerve":  ("left_nerve_path",  7, 1.0),
    "Right Nerve": ("right_nerve_path", 8, 1.0),
}


class TableModel(QAbstractTableModel):
    selected = Signal(int)
    changeButtonStatus = Signal(list)
    clickedButton = Signal(str)
    segment = Signal()
    rendermode = Signal()
    renderDirection = Signal()
    captureScreen = Signal()
    saveComment = Signal(str)
    dataChanged = Signal(QModelIndex, QModelIndex)

    COLUMN_NAMES = ["patient_ID", "patient_Name", "studyUID", "studyDate", "Comment"]

    def __init__(self):
        QAbstractTableModel.__init__(self)
        self.rows = []

    def rowCount(self, parent):
        return len(self.rows)

    def columnCount(self, parent):
        return len(self.COLUMN_NAMES)

    def fill_row(self, studies):
        for x in studies:
            self.rows.append(list(x.values())[1:])

    def update_comment(self, row, comment_str):
        self.rows[row]['comment'] = comment_str

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if not 0 <= index.row() < len(self.rows):
            return None
        if role == Qt.DisplayRole:
            return self.rows[index.row()][index.column()]
        return None

    def headerData(self, section, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            headers = ["Patient ID", "Patient Name", "Study UID", "Study Date", "Comment"]
            if 0 <= section < len(headers):
                return headers[section]
        return None


class Extent:
    def __init__(self, x1, x2, y1, y2, z1, z2):
        self.x1, self.x2 = x1, x2
        self.y1, self.y2 = y1, y2
        self.z1, self.z2 = z1, z2

    def vertices(self):
        for x in (self.x1, self.x2):
            for y in (self.y1, self.y2):
                for z in (self.z1, self.z2):
                    yield (x, y, z)


from scipy.ndimage import label
MIN_CONNECTED_VOXEL = 5000


def find_connected_elements_3d(m, v):
    mask = (m == v)
    labeled_array, num_features = label(mask)
    return [numpy.argwhere(labeled_array == i) for i in range(1, num_features + 1)]


def calculate_3d_extent(np_image, value):
    connected_indices = find_connected_elements_3d(np_image, value)
    print("num of connected_indices:", len(connected_indices))

    indices = None
    for i, group in enumerate(connected_indices):
        print(value, i, group.shape)
        if group.shape[0] >= MIN_CONNECTED_VOXEL:
            indices = group if indices is None else numpy.concatenate((indices, group), axis=0)

    if indices is not None:
        x1, x2 = numpy.min(indices[:, 0]), numpy.max(indices[:, 0])
        y1, y2 = numpy.min(indices[:, 1]), numpy.max(indices[:, 1])
        z1, z2 = numpy.min(indices[:, 2]), numpy.max(indices[:, 2])
        return x1, x2, y1, y2, z1, z2
    return 0, 0, 0, 0, 0, 0


class MAINApp(QQuickView):

    def __init__(self, exec_param=None, *args, **kwds):
        super().__init__(*args, **kwds)

        try:
            client = pymongo.MongoClient(uri)
        except pymongo.errors.ConfigurationError as e:
            print(e, "An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
            sys.exit(1)

        try:
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)

        self.db = client['KorGuide']
        self.collection = self.db['ReluRes']

        self.screenshotCount = 0
        self.rendermode = 3
        self.renderDir = 1
        self.makeNifti = True
        self.spacing = [.0, .0, .0]

        results = self.collection.aggregate([
            {'$project': {
                'path': 1,
                'missing_teeth_numbers': {
                    '$filter': {
                        'input': '$teeth',
                        'as': 'tooth',
                        'cond': {'$eq': ['$$tooth.missing', True]}
                    }
                }
            }},
            {'$addFields': {
                'missing_teeth_numbers': {
                    '$map': {'input': '$missing_teeth_numbers', 'as': 'tooth', 'in': '$$tooth.number'}
                },
                'missing_teeth_count': {'$size': '$missing_teeth_numbers'}
            }},
            {'$match': {'missing_teeth_count': {'$lte': 6}}},
            {'$project': {'_id': 1, 'path': 1, 'missing_teeth_numbers': 1}}
        ])

        res = list(results)
        self.allres = []
        for rec in res:
            for tooth_num in rec["missing_teeth_numbers"]:
                if tooth_num in (35, 45):
                    docs = list(self.collection.find(
                        {'_id': rec["_id"]},
                        {"patient_id": 1, "patient_name": 1, "study_uid": 1, "study_date": 1, "comment": 1, "_id": 1}
                    ))
                    self.allres.append(*docs)

        self.studyUID = None
        self.my_TableModel = TableModel()
        self.my_TableModel.fill_row(self.allres)

        self.rootContext().setContextProperty("my_TableModel", self.my_TableModel)
        _win_source = QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), 'dbwin.qml'))
        self.setSource(_win_source)

        self.setResizeMode(QQuickView.SizeRootObjectToView)
        self.setTitle("Relu Result Viewer")
        self.resize(640, 960)
        self.setPosition(40, 40)

        self.window = QMainWindow()
        self.window.resize(960, 960)
        self.widget = QVTKRenderWindowInteractor(self.window)
        self.window.setCentralWidget(self.widget)
        self.ren = vtkRenderer()
        self.widget.GetRenderWindow().AddRenderer(self.ren)
        self.ren.SetUseDepthPeeling(True)
        self.ren.UseDepthPeelingForVolumesOn()

        self.window.move(680, 10)
        self.window.show()

        self.istyle = vtk.vtkInteractorStyleTrackballCamera()
        self.widget._Iren.SetInteractorStyle(self.istyle)
        self.widget.Initialize()
        self.widget.Start()
        print(self.widget.width(), self.widget.height())

        self.volume = None
        self._camera_initialized = False
        self._stl_meshes = {}
        self._stl_actors = {}
        self.box_widgets = []
        self.wcs_extent = []

        self.my_TableModel.selected.connect(self.set_buttons_status)
        self.my_TableModel.clickedButton.connect(self.add_model)
        self.my_TableModel.segment.connect(self.segment)
        self.my_TableModel.rendermode.connect(self.renderMode)
        self.my_TableModel.renderDirection.connect(self.renderDirection)
        self.my_TableModel.captureScreen.connect(self.captureScreen)
        self.my_TableModel.saveComment.connect(self.saveComment)

    def _cleanup_scene(self):
        if self.volume:
            self.ren.RemoveVolume(self.volume)
            self.volume = None
        for bw in self.box_widgets:
            bw.Off()
        self.box_widgets.clear()
        for actor in self._stl_actors.values():
            self.ren.RemoveActor(actor)
        self._stl_meshes.clear()
        self._stl_actors.clear()
        self._camera_initialized = False
        self.wcs_extent = []

    @Slot(int)
    def set_buttons_status(self, row=0):
        results = self.collection.find(filter={'_id': ObjectId(self.allres[row]['_id'])})
        res = list(results)
        self.rowNum = row
        self.currentRow = res[0]
        self.studyUID = self.currentRow['study_uid']
        print("Current studyUID:", self.studyUID)

        self._cleanup_scene()

        rec = res[0]
        print(rec['patient_name'], rec['study_date'])
        self.buttonStatus = [0] * 41

        if os.path.exists(os.path.join(rec['path'], 'cvt')):
            print(os.path.join(rec['path'], 'cvt'))
            self.buttonStatus[0] = 1

        for path_field, btn_idx, _ in _STL_MODELS.values():
            p = rec.get(path_field, '')
            if p and os.path.exists(p):
                print(p)
                self.buttonStatus[btn_idx] = 1

        print(self.buttonStatus)

        for i, tooth in enumerate(rec['teeth'], start=9):
            if not tooth["missing"] and os.path.exists(tooth["tooth_path"]):
                print(i, tooth["missing"], tooth["number"], tooth["tooth_path"])
                self.buttonStatus[i] = 1

        print(self.buttonStatus)
        self.my_TableModel.changeButtonStatus.emit(self.buttonStatus)

    def _setup_camera(self):
        fp = numpy.array(self.ren.GetActiveCamera().GetFocalPoint())
        dist = self.ren.GetActiveCamera().GetDistance()
        self.ren.GetActiveCamera().SetPosition(fp[0], fp[1] - dist, fp[2])
        self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
        self.ren.GetActiveCamera().ParallelProjectionOn()
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()
        print("Renderwindow size:", self.widget.GetRenderWindow().GetSize())
        self._camera_initialized = True

    def _toggle_stl(self, name, path_field, btn_idx, opacity):
        if self.buttonStatus[btn_idx] == 1:
            if name not in self._stl_meshes:
                reader = vtk.vtkSTLReader()
                reader.SetFileName(self.currentRow[path_field])
                reader.MergingOn()
                reader.Update()
                self._stl_meshes[name] = reader.GetOutput()
                print("Open", self.currentRow[path_field], self._stl_meshes[name].GetBounds())
            mapper = vtkPolyDataMapper()
            mapper.SetInputDataObject(self._stl_meshes[name])
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetOpacity(opacity)
            self._stl_actors[name] = actor
            self.ren.AddActor(actor)
            self.buttonStatus[btn_idx] = 2
        elif self.buttonStatus[btn_idx] == 2:
            self.ren.RemoveActor(self._stl_actors.pop(name))
            self.buttonStatus[btn_idx] = 1

    @Slot(str)
    def add_model(self, name):
        print(name + " Clicked! ")

        if name == 'CT':
            if self.buttonStatus[0] == 1:
                if self.makeNifti:
                    os.makedirs(os.path.join(self.currentRow['path'], 'segment'), exist_ok=True)
                self.min_npV, self.max_npV, self.adjThresholds, self.spacing, self.volume = \
                    ScanDirectory.load_dicom(os.path.join(self.currentRow['path'], 'cvt'), 3, True)
                self.ren.AddVolume(self.volume)
                self.buttonStatus[0] = 2
            elif self.buttonStatus[0] == 2:
                self.ren.RemoveVolume(self.volume)
                self.buttonStatus[0] = 1
        elif name in _STL_MODELS:
            path_field, btn_idx, opacity = _STL_MODELS[name]
            self._toggle_stl(name, path_field, btn_idx, opacity)

        self.my_TableModel.changeButtonStatus.emit(self.buttonStatus)

        if not self._camera_initialized and (self.volume or self._stl_actors):
            self._setup_camera()

        self.widget.update()

    @Slot()
    def segment(self):
        print("segment")

        input_dir = os.path.join(self.currentRow['path'], 'segment')
        output_dir = os.path.join(self.currentRow['path'], 'output')
        os.makedirs(output_dir, exist_ok=True)

        if not (os.path.exists(output_dir) and os.path.exists(input_dir)):
            print("Error, directories not exist")
            return

        os.environ['nnUNet_raw'] = '.'
        os.environ['nnUNet_results'] = '.'
        os.environ['nnUNet_preprocessed'] = '.'

        nnunet_command = (
            f"nnUNetv2_predict -i {input_dir}/ -o {output_dir}/ "
            "-d Dataset111_453CT -tr nnUNetTrainer -p nnUNetPlans "
            "-c 3d_fullres -f 0 -npp 1 -nps 1 -step_size 0.5 -device cuda --disable_tta"
        )
        start_time = time.time()
        subprocess.run(nnunet_command, shell=True)
        print("segmentation time:", time.time() - start_time)

        outfile = os.path.join(output_dir, "Dental_0001.nii.gz")
        img = nib.load(outfile)
        npImage = img.get_fdata().transpose(2, 1, 0)
        unique_labels = numpy.unique(npImage)

        self.wcs_extent = []
        xo, yo, zo = self.volume.GetOrigin()

        for i in range(1, 6):
            if i not in unique_labels:
                self.wcs_extent.append([.0, .0, .0, .0, .0, .0])
            else:
                k1, k2, j1, j2, i1, i2 = calculate_3d_extent(npImage, i)
                x1, x2 = i1 * self.spacing[0] + xo, i2 * self.spacing[0] + xo
                y1, y2 = j1 * self.spacing[1] + yo, j2 * self.spacing[1] + yo
                z1, z2 = k1 * self.spacing[2] + zo, k2 * self.spacing[2] + zo
                self.wcs_extent.append([x1, x2, y1, y2, z1, z2])
                print(self.wcs_extent[-1], self.volume.GetBounds())

        self.box_widgets = []
        for extent in self.wcs_extent[:4]:
            bw = vtkBoxWidget()
            bw.SetInteractor(self.widget)
            bw.SetProp3D(self.volume)
            bw.SetPlaceFactor(1.0)
            bw.PlaceWidget(extent)
            bw.On()
            self.box_widgets.append(bw)

    def _apply_bone_tf(self, colorFun, opacityFun, include_soft_tissue, width_s=80):
        mn, mx = self.min_npV, self.max_npV
        t0, t1, t2 = self.adjThresholds

        colorFun.AddRGBPoint(mn, 0.3, 0.3, 1.0, 0.5, 0.0)
        colorFun.AddRGBPoint(t0, 0.95, 0.95, 0.85, 0.5, 0.0)
        colorFun.AddRGBPoint((t0 + t2) / 2, 0.75, 0.4, 0.35, 0.5, 0.0)
        colorFun.AddRGBPoint(t2, 0.95, 0.84, 0.19, 0.5, 0.0)
        colorFun.AddRGBPoint(mx, 0.78, 0.78, 0.92, 0.5, 0.0)

        opacityFun.AddPoint(mn, 0, 0.5, 0.0)
        if include_soft_tissue:
            opacityFun.AddPoint(t0, 0.0, 0.5, 0.0)
            opacityFun.AddPoint(t0 + width_s / 2.0, 0.5, 0.5, 0.0)
            opacityFun.AddPoint(t0 + width_s, 0.0, 0.5, 0.0)
        opacityFun.AddPoint(t1, 0, 0.5, 0.0)
        opacityFun.AddPoint(t2, 0.5, 0.5, 0.0)
        opacityFun.AddPoint(mx, 0.75, 0.5, 0.0)

    def _apply_composite_shading(self, mapper, prop):
        prop.ShadeOn()
        mapper.SetBlendModeToComposite()
        prop.SetAmbient(0.2)
        prop.SetDiffuse(1.0)
        prop.SetSpecular(0.0)
        prop.SetSpecularPower(1.0)
        prop.SetScalarOpacityUnitDistance(0.8919)

    @Slot()
    def renderMode(self):
        print("Rendering Mode")
        mapper = self.volume.GetMapper()
        prop = self.volume.GetProperty()
        colorFun = vtk.vtkColorTransferFunction()
        opacityFun = vtk.vtkPiecewiseFunction()

        if self.rendermode == 3:       # currently Bone1 → switch to Bone2
            self._apply_bone_tf(colorFun, opacityFun, include_soft_tissue=False)
            self._apply_composite_shading(mapper, prop)
            self.rendermode = 5
        elif self.rendermode == 5:     # currently Bone2 → switch to MIP
            opacityWindow, opacityLevel = 2048, 1024
            colorFun.AddRGBSegment(0.0, 1.0, 1.0, 1.0, 255.0, 1.0, 1.0, 1.0)
            opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                                  opacityLevel + 0.5 * opacityWindow, 1.0)
            mapper.SetBlendModeToMaximumIntensity()
            self.rendermode = 1
        elif self.rendermode == 1:     # currently MIP → switch to Bone1
            self._apply_bone_tf(colorFun, opacityFun, include_soft_tissue=True)
            self._apply_composite_shading(mapper, prop)
            self.rendermode = 3

        prop.SetColor(colorFun)
        prop.SetScalarOpacity(opacityFun)
        self.widget.update()

    @Slot()
    def renderDirection(self):
        fp = numpy.array(self.ren.GetActiveCamera().GetFocalPoint())
        dist = self.ren.GetActiveCamera().GetDistance()

        if self.renderDir == 3:        # Superior → Anterior
            self.ren.GetActiveCamera().SetPosition(fp[0], fp[1] - dist, fp[2])
            self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
            self.renderDir = 1
        elif self.renderDir == 1:      # Anterior → Left
            self.ren.GetActiveCamera().SetPosition(fp[0] + dist, fp[1], fp[2])
            self.ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
            self.renderDir = 2
        elif self.renderDir == 2:      # Left → Superior
            self.ren.GetActiveCamera().SetPosition(fp[0], fp[1], fp[2] + dist)
            self.ren.GetActiveCamera().SetViewUp(0.0, 1.0, 0.0)
            self.renderDir = 3

        self.ren.GetActiveCamera().ParallelProjectionOn()
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()
        self.widget.update()

    # Corner indices per view direction for bounding-box projection
    _VIEW_CORNERS = {1: (0, 5), 2: (4, 7), 3: (1, 7)}

    def _get_corner_display(self, extent):
        coordinate = vtk.vtkCoordinate()
        coordinate.SetCoordinateSystemToWorld()
        coords = []
        for vertex in Extent(*extent).vertices():
            coordinate.SetValue(vertex)
            coords.append(coordinate.GetComputedDisplayValue(self.ren))
        return coords

    def _crop_margins(self, disp_coords):
        x, y = self.widget.GetRenderWindow().GetSize()
        i_min, i_max = self._VIEW_CORNERS[self.renderDir]
        x1, y1 = disp_coords[i_min]
        x2, y2 = disp_coords[i_max]
        dx = x1 if x1 < x - x2 else x - x2
        dy = y1 if y1 < y - y2 else y - y2
        return dx, dy

    @Slot()
    def captureScreen(self):
        print("Capture")
        x, y = self.widget.GetRenderWindow().GetSize()

        vol_bounds = self.volume.GetBounds()
        vol_coords = self._get_corner_display(vol_bounds)
        for i, (vertex, coord) in enumerate(zip(Extent(*vol_bounds).vertices(), vol_coords)):
            print(i, vertex, coord)

        winToImageFilter = vtk.vtkWindowToImageFilter()
        winToImageFilter.SetInput(self.widget.GetRenderWindow())
        winToImageFilter.SetInputBufferTypeToRGB()
        winToImageFilter.Update()
        imgArray = vtkmodules.util.numpy_support.vtk_to_numpy(
            winToImageFilter.GetOutput().GetPointData().GetScalars()
        ).reshape(x, y, 3)

        dx, dy = self._crop_margins(vol_coords)
        croppedArray = numpy.flipud(imgArray[dy:y - dy + 1, dx:x - dx + 1, :])

        scrFileName = "%s_%d%d%d.png" % (self.studyUID, self.rendermode, self.renderDir, self.screenshotCount)
        txtFileName = "%s_%d%d%d.txt" % (self.studyUID, self.rendermode, self.renderDir, self.screenshotCount)
        print("Save to", scrFileName)
        self.screenshotCount += 1

        xx = x - 2 * dx - 1
        yy = y - 2 * dy - 1

        if self.wcs_extent:
            i_min, i_max = self._VIEW_CORNERS[self.renderDir]
            with open(txtFileName, "w") as txtFile:
                for j, seg_extent in enumerate(self.wcs_extent):
                    dp = self._get_corner_display(seg_extent)
                    xx1 = dp[i_min][0]
                    yy1 = y - dp[i_min][1] - 1
                    xx2 = dp[i_max][0]
                    yy2 = y - dp[i_max][1] - 1
                    cx = (xx1 + xx2 - 2 * dx) / (2 * xx)
                    cy = (yy1 + yy2 - 2 * dy) / (2 * yy)
                    width = (xx2 - xx1) / xx
                    height = (yy1 - yy2) / yy
                    print("Segment:", j, cx, cy, width, height)
                    txtFile.write(f"{j} {cx} {cy} {width} {height}\n")

        im.fromarray(croppedArray).save(scrFileName)

    @Slot(str)
    def saveComment(self, commentText):
        print("saveComment")
        if commentText:
            self.collection.update_one(
                {"_id": ObjectId(self.currentRow['_id'])},
                [{"$set": {"comment": commentText}}]
            )
            self.my_TableModel.update_comment(self.rowNum, commentText)
            index = QModelIndex(self.rowNum)
            self.my_TableModel.dataChanged.emit(index, index)
