import sys, os
import time

import gdcm
import numpy
import vtk
from skimage.filters import threshold_multiotsu

import nibabel as nib

# GDCM PixelFormat → numpy dtype
_GDCM_NP_TYPES = {
    gdcm.PixelFormat.UINT8:   numpy.uint8,
    gdcm.PixelFormat.INT8:    numpy.int8,
    gdcm.PixelFormat.UINT16:  numpy.uint16,
    gdcm.PixelFormat.INT16:   numpy.int16,
    gdcm.PixelFormat.UINT32:  numpy.uint32,
    gdcm.PixelFormat.INT32:   numpy.int32,
    gdcm.PixelFormat.FLOAT32: numpy.float32,
    gdcm.PixelFormat.FLOAT64: numpy.float64,
}


def _gdcm_dtype(gdcm_pixel_format):
    return _GDCM_NP_TYPES[gdcm_pixel_format.GetScalarType()]


def gdcm_to_numpy(image):
    pf = image.GetPixelFormat()
    assert pf.GetScalarType() in _GDCM_NP_TYPES, "Unsupported pixel format %s" % pf
    assert pf.GetSamplesPerPixel() == 1, "SamplesPerPixel != 1"
    dtype = _gdcm_dtype(pf)
    raw = image.GetBuffer().encode("utf-8", errors="surrogateescape")
    volume = numpy.frombuffer(raw, dtype=dtype)
    if image.GetNumberOfDimensions() == 2:
        return volume.reshape(image.GetDimension(0), image.GetDimension(1))
    return volume.reshape(image.GetDimension(2), image.GetDimension(0), image.GetDimension(1))


def _parse_ds_values(gdcm_value):
    return [float(n) for n in str(gdcm_value).split('\\')]


def GetSpacingDirOrigin(ds):
    TAG_SHARED_FG  = gdcm.Tag(0x5200, 0x9229)
    TAG_PER_FRAME  = gdcm.Tag(0x5200, 0x9230)
    TAG_PLANE_ORI  = gdcm.Tag(0x0020, 0x9116)
    TAG_PIXEL_MEAS = gdcm.Tag(0x0028, 0x9110)
    TAG_IOP        = gdcm.Tag(0x0020, 0x0037)
    TAG_PIX_SPACE  = gdcm.Tag(0x0028, 0x0030)
    TAG_SLICE_THCK = gdcm.Tag(0x0018, 0x0050)
    TAG_PLANE_POS  = gdcm.Tag(0x0020, 0x9113)
    TAG_IMG_POS    = gdcm.Tag(0x0020, 0x0032)

    imageOrientation = None
    pixelSpacing = None
    sliceThickness = None
    pos0 = pos1 = None

    if ds.FindDataElement(TAG_SHARED_FG):
        sq = ds.GetDataElement(TAG_SHARED_FG).GetValueAsSQ()
        if sq.GetNumberOfItems():
            nested = sq.GetItem(1).GetNestedDataSet()

            if nested.FindDataElement(TAG_PLANE_ORI):
                sq2 = nested.GetDataElement(TAG_PLANE_ORI).GetValueAsSQ()
                if sq2.GetNumberOfItems():
                    n2 = sq2.GetItem(1).GetNestedDataSet()
                    if n2.FindDataElement(TAG_IOP):
                        imageOrientation = _parse_ds_values(n2.GetDataElement(TAG_IOP).GetValue())
                        print("Image Orientation", imageOrientation)
                    else:
                        print("No Image Orientation")

            if nested.FindDataElement(TAG_PIXEL_MEAS):
                sq2 = nested.GetDataElement(TAG_PIXEL_MEAS).GetValueAsSQ()
                if sq2.GetNumberOfItems():
                    n2 = sq2.GetItem(1).GetNestedDataSet()
                    if n2.FindDataElement(TAG_PIX_SPACE):
                        pixelSpacing = _parse_ds_values(n2.GetDataElement(TAG_PIX_SPACE).GetValue())
                        print("PixelSpacing", pixelSpacing)
                    else:
                        print("No Pixel Spacing")
                    if n2.FindDataElement(TAG_SLICE_THCK):
                        sliceThickness = _parse_ds_values(n2.GetDataElement(TAG_SLICE_THCK).GetValue())
                        print("SliceThickness", sliceThickness)
                    else:
                        print("No Slice Thickness")

    if ds.FindDataElement(TAG_PER_FRAME):
        sq = ds.GetDataElement(TAG_PER_FRAME).GetValueAsSQ()
        nFrame = sq.GetNumberOfItems()

        def _read_pos(frame_item):
            nested = frame_item.GetNestedDataSet()
            if not nested.FindDataElement(TAG_PLANE_POS):
                return None
            sq2 = nested.GetDataElement(TAG_PLANE_POS).GetValueAsSQ()
            if not sq2.GetNumberOfItems():
                return None
            n2 = sq2.GetItem(1).GetNestedDataSet()
            if not n2.FindDataElement(TAG_IMG_POS):
                return None
            return _parse_ds_values(n2.GetDataElement(TAG_IMG_POS).GetValue())

        pos0 = _read_pos(sq.GetItem(1))
        pos1 = _read_pos(sq.GetItem(nFrame))
        if pos0:
            print("ImagePosition", pos0)
        if pos1:
            print("ImagePosition", pos1)

    if imageOrientation is None or pos0 is None or pos1 is None:
        return -1

    cosineX = numpy.array(imageOrientation[0:3])
    cosineY = numpy.array(imageOrientation[3:6])
    normal = numpy.cross(cosineX, cosineY)
    dist = (numpy.dot(normal, pos1) - numpy.dot(normal, pos0)) / (nFrame - 1)
    bFlip = dist < 0
    origin = pos1 if bFlip else pos0
    return imageOrientation, sliceThickness, origin, pixelSpacing, abs(dist), bFlip, pos0, pos1


def numpy2VTK(img, spacing=[1.0, 1.0, 1.0], origin=[0.0, 0.0, 0.0],
              dirCosines=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0]):
    importer = vtk.vtkImageImport()
    img_data = img.astype('int16')
    img_string = img_data.tobytes()
    dim = img.shape
    print(len(img_string), dim)

    importer.CopyImportVoidPointer(img_string, len(img_string))
    importer.SetDataScalarType(vtk.VTK_SHORT)
    importer.SetNumberOfScalarComponents(1)

    ext = importer.GetDataExtent()
    importer.SetDataExtent(ext[0], ext[0] + dim[2] - 1,
                           ext[2], ext[2] + dim[1] - 1,
                           ext[4], ext[4] + dim[0] - 1)
    importer.SetWholeExtent(ext[0], ext[0] + dim[2] - 1,
                            ext[2], ext[2] + dim[1] - 1,
                            ext[4], ext[4] + dim[0] - 1)
    importer.SetDataSpacing(*spacing)
    importer.SetDataOrigin(*origin)

    cosX = numpy.array(dirCosines[0:3])
    cosY = numpy.array(dirCosines[3:6])
    cosZ = numpy.cross(cosX, cosY)
    R = numpy.transpose([cosX, cosY, cosZ])
    importer.SetDataDirection(R.flatten())
    return importer


def load_dicom(directory, blendType=3, makenifti=False):
    TAG_PATIENT_ID   = gdcm.Tag(0x0010, 0x0020)
    TAG_PATIENT_NAME = gdcm.Tag(0x0010, 0x0010)
    TAG_STUDY_ID     = gdcm.Tag(0x0020, 0x0010)
    TAG_STUDY_UID    = gdcm.Tag(0x0020, 0x000d)
    TAG_SERIES_UID   = gdcm.Tag(0x0020, 0x000e)
    TAG_SERIES_NUM   = gdcm.Tag(0x0020, 0x0011)
    TAG_NUM_FRAMES   = gdcm.Tag(0x0028, 0x0008)
    TAG_IMG_POS      = gdcm.Tag(0x0020, 0x0032)
    TAG_PIX_SPACE    = gdcm.Tag(0x0028, 0x0030)
    TAG_IOP          = gdcm.Tag(0x0020, 0x0037)
    TAG_SAMPLES_PX   = gdcm.Tag(0x0028, 0x0002)
    TAG_PHOTOMETRIC  = gdcm.Tag(0x0028, 0x0004)
    TAG_ROWS         = gdcm.Tag(0x0028, 0x0010)
    TAG_COLS         = gdcm.Tag(0x0028, 0x0011)
    TAG_BIT_STORED   = gdcm.Tag(0x0028, 0x0101)
    TAG_MEDIA_SOP    = gdcm.Tag(0x0002, 0x0002)
    TAG_MEDIA_INST   = gdcm.Tag(0x0002, 0x0003)
    TAG_XFER_SYNTAX  = gdcm.Tag(0x0002, 0x0010)
    TAG_SOP_CLASS    = gdcm.Tag(0x0008, 0x0016)
    TAG_SOP_INST     = gdcm.Tag(0x0008, 0x0018)
    TAG_SHARED_FG    = gdcm.Tag(0x5200, 0x9229)
    TAG_PER_FRAME    = gdcm.Tag(0x5200, 0x9230)
    TAG_WIN_CENTER   = gdcm.Tag(0x0028, 0x1050)
    TAG_WIN_WIDTH    = gdcm.Tag(0x0028, 0x1051)
    TAG_RESCALE_INT  = gdcm.Tag(0x0028, 0x1052)
    TAG_RESCALE_SLP  = gdcm.Tag(0x0028, 0x1053)
    TAG_RESCALE_TYPE = gdcm.Tag(0x0028, 0x1054)

    t0 = time.time()

    d = gdcm.Directory()
    if d.Load(directory) == 0:
        return None
    filenames = d.GetFilenames()

    gdcm.Trace.WarningOff()

    sp = gdcm.Scanner.New()
    s = sp.__ref__()
    for tag in (TAG_PATIENT_ID, TAG_PATIENT_NAME, TAG_STUDY_ID, TAG_STUDY_UID,
                TAG_SERIES_UID, TAG_SERIES_NUM, TAG_NUM_FRAMES, TAG_IMG_POS,
                TAG_PIX_SPACE, TAG_IOP, TAG_SAMPLES_PX, TAG_PHOTOMETRIC,
                TAG_ROWS, TAG_COLS, TAG_BIT_STORED, TAG_MEDIA_SOP,
                TAG_MEDIA_INST, TAG_XFER_SYNTAX, TAG_SOP_CLASS, TAG_SOP_INST,
                TAG_SHARED_FG, TAG_PER_FRAME):
        s.AddTag(tag)

    if not s.Scan(filenames):
        sys.exit(1)
    print("success True")
    print("Time to Scan Directory and Dicom files", time.time() - t0)

    series_list = []
    for dFile in filenames:
        if s.IsKey(dFile):
            val = s.GetValue(dFile, TAG_SERIES_UID)
            if val and val not in series_list:
                series_list.append(val)

    if len(series_list) != 1:
        return None

    series_uid = series_list[0]
    series_imgfiles = s.GetAllFilenamesFromTagToValue(TAG_SERIES_UID, series_uid)
    print("-" * 71)
    print(series_uid, ", # of Files: ", len(series_imgfiles))

    # --- single-file (possibly multiframe) ---
    if len(series_imgfiles) == 1:
        image_file = series_imgfiles[0]
        nFrame = int(s.GetValue(image_file, TAG_NUM_FRAMES))

        if nFrame <= 1:
            print("Single image file with unique series id", image_file, nFrame)
            return None

        print("Read Multiframe", image_file, nFrame)
        reader = gdcm.ImageReader()
        reader.SetFileName(image_file)
        if not reader.Read():
            print("Cannot read image", image_file)
            return None

        image = reader.GetImage()
        npVolume = gdcm_to_numpy(image).copy()
        print("Shape of Volume:", npVolume.shape)

        w, d, h = image.GetDimension(0), image.GetDimension(1), image.GetDimension(2)
        result = GetSpacingDirOrigin(reader.GetFile().GetDataSet())
        if result == -1:
            return None
        dirCosines, sliceThickness, origin, pixelSpacing, dz, bFlip, pos0, pos1 = result
        print(dirCosines, sliceThickness, origin, pixelSpacing, dz, bFlip)

        dx, dy = pixelSpacing[0], pixelSpacing[1]
        if bFlip:
            npVolume = numpy.flip(npVolume, 0)

        is_multiframe = nFrame

        print("Samples per Pixel:",        s.GetValue(image_file, TAG_SAMPLES_PX))
        print("Photometric Representation:", s.GetValue(image_file, TAG_PHOTOMETRIC))
        print("Rows:", s.GetValue(image_file, TAG_ROWS))
        print("Columns:", s.GetValue(image_file, TAG_COLS))
        print("BitStored:", s.GetValue(image_file, TAG_BIT_STORED))

        iRescaleSlope, iRescaleIntercept = 1.0, -1024.0
        iWindowCenter, iWindowWidth = 1024, 4092

        s_slp = s.GetValue(image_file, TAG_RESCALE_SLP)
        s_int = s.GetValue(image_file, TAG_RESCALE_INT)
        s_wc  = s.GetValue(image_file, TAG_WIN_CENTER)
        s_ww  = s.GetValue(image_file, TAG_WIN_WIDTH)
        print("RescaleSlope:", s_slp, "RescaleIntercept:", s_int)
        print("WindowCenter:", s_wc, "WindowWidth:", s_ww)

        if s_wc: iWindowCenter = s_wc
        if s_ww: iWindowWidth = s_ww
        if s_int: iRescaleIntercept = s_int
        if s_slp: iRescaleSlope = s_slp

    # --- multi-file series ---
    else:
        is_multiframe = 0

        series_files = []
        for f in series_imgfiles:
            posV = _parse_ds_values(s.GetValue(f, TAG_IMG_POS))
            series_files.append([f, posV])

        origin = series_files[0][1]
        pixelSpacing = _parse_ds_values(s.GetValue(series_files[0][0], TAG_PIX_SPACE))
        dirCosines   = _parse_ds_values(s.GetValue(series_files[0][0], TAG_IOP))
        rowCosine    = numpy.array(dirCosines[:3])
        colCosine    = numpy.array(dirCosines[3:])
        sliceCosine  = numpy.cross(rowCosine, colCosine)

        for f in series_files:
            f.append([numpy.dot(numpy.array(f[1]) - numpy.array(origin), sliceCosine)])

        sorted_series_files = sorted(series_files, key=lambda item: item[2])

        if len(sorted_series_files) > 1:
            dists = [
                numpy.linalg.norm(numpy.array(sorted_series_files[i][1]) -
                                  numpy.array(sorted_series_files[i - 1][1]))
                for i in range(1, len(sorted_series_files))
            ]
            avg_slice_distance = numpy.mean(dists)
        else:
            avg_slice_distance = None

        dx, dy = pixelSpacing[0], pixelSpacing[1]
        dz = avg_slice_distance

        reader = gdcm.ImageReader()
        reader.SetFileName(sorted_series_files[0][0])
        if not reader.Read():
            print("Cannot read image", sorted_series_files[0][0])

        image = reader.GetImage()
        pf = image.GetPixelFormat()
        assert pf.GetScalarType() in _GDCM_NP_TYPES, "Unsupported pixel format %s" % pf
        w, d, h = image.GetDimension(0), image.GetDimension(1), len(sorted_series_files)

        dtype = _gdcm_dtype(pf)
        npVolume = numpy.zeros((h, w, d), dtype=dtype)
        print(w, d, h, dtype, dx, dy, dz)

        for i in range(h):
            reader = gdcm.ImageReader()
            reader.SetFileName(sorted_series_files[i][0])
            if not reader.Read():
                print("Cannot read image", sorted_series_files[i][0])
            image = reader.GetImage()
            raw = image.GetBuffer().encode("utf-8", errors="surrogateescape")
            npVolume[i, :, :] = numpy.frombuffer(raw, dtype=dtype).reshape(w, d).copy()

        first = sorted_series_files[0][0]
        print("Pixel Spacing:", pixelSpacing, avg_slice_distance)
        print("Image Orientation:", dirCosines)
        print("Origin:", origin)
        print("Samples per Pixel:",        s.GetValue(first, TAG_SAMPLES_PX))
        print("Photometric Representation:", s.GetValue(first, TAG_PHOTOMETRIC))
        print("Rows:", s.GetValue(first, TAG_ROWS))
        print("Columns:", s.GetValue(first, TAG_COLS))
        print("BitStored:", s.GetValue(first, TAG_BIT_STORED))

        max_npV = npVolume.max()
        min_npV = npVolume.min()

        iRescaleSlope = 1
        iRescaleIntercept = 0 if min_npV < 0 else -1024
        iWindowCenter, iWindowWidth = 1024, 4092

        s_slp = s.GetValue(first, TAG_RESCALE_SLP)
        s_int = s.GetValue(first, TAG_RESCALE_INT)
        s_wc  = s.GetValue(first, TAG_WIN_CENTER)
        s_ww  = s.GetValue(first, TAG_WIN_WIDTH)
        print("RescaleSlope:", s_slp, "RescaleIntercept:", s_int)
        print("RescaleType:", s.GetValue(first, TAG_RESCALE_TYPE))
        print("WindowCenter:", s_wc, "WindowWidth:", s_ww)

        if s_wc: iWindowCenter = s_wc
        if s_ww: iWindowWidth = s_ww
        if s_int: iRescaleIntercept = s_int
        if s_slp: iRescaleSlope = s_slp

        if s_int or (max_npV - min_npV) >= 4096:
            print("16bit data and rescale intercept", s_int, s_slp)

    # --- common post-load ---
    direction_x = dirCosines[0:3]
    direction_y = dirCosines[3:6]

    max_npV = npVolume.max()
    min_npV = npVolume.min()
    print("min, max, rescaleSlope, Intercept:", min_npV, max_npV, iRescaleSlope, iRescaleIntercept)

    dataImporter = numpy2VTK(npVolume, [dx, dy, dz], origin, dirCosines)
    dataImporter.Update()

    npVolume[npVolume < (min_npV + 0.005 * (max_npV - min_npV))] = 0

    t0 = time.time()
    npVol = npVolume * (256.0 / (max_npV - min_npV))
    thresholds = threshold_multiotsu(npVol, 4)
    adjThresholds = [
        t * ((max_npV - min_npV) / 256.0) * iRescaleSlope + iRescaleIntercept
        for t in thresholds
    ]
    print(adjThresholds, time.time() - t0)

    if makenifti:
        t0 = time.time()
        parent_dir = os.path.dirname(os.path.abspath(directory))
        output_directory = os.path.join(parent_dir, "segment")
        os.makedirs(output_directory, exist_ok=True)

        npImage = npVolume.transpose(2, 1, 0)

        if is_multiframe != 0:
            step = [(pos0[i] - pos1[i]) / (1 - h) for i in range(3)]
        else:
            p0 = sorted_series_files[0][1]
            p1 = sorted_series_files[h - 1][1]
            step = [(p0[i] - p1[i]) / (1 - h) for i in range(3)]

        affine = numpy.array([
            [-direction_x[0] * dy, -direction_y[0] * dx, -step[0], -origin[0]],
            [-direction_x[1] * dy, -direction_y[1] * dx, -step[1], -origin[1]],
            [ direction_x[2] * dy,  direction_y[2] * dx,  step[2],  origin[2]],
            [0, 0, 0, 1]
        ])

        nii_image = nib.Nifti1Image(npImage, affine)
        nii_image.header.set_slope_inter(1, 0)
        nii_image.header.set_xyzt_units(2)
        nifti_file = os.path.join(output_directory, "Dental_0001_0000.nii.gz")
        nib.save(nii_image, nifti_file)
        print("Saving nifti file", time.time() - t0)

    xMin, xMax, yMin, yMax, zMin, zMax = dataImporter.GetWholeExtent()
    xSp, ySp, zSp = dataImporter.GetDataSpacing()
    x0, y0, z0 = dataImporter.GetDataOrigin()
    center = [x0 + xSp * 0.5 * (xMin + xMax),
              y0 + ySp * 0.5 * (yMin + yMax),
              z0 + zSp * 0.5 * (zMin + zMax)]
    print(xMin, xMax, yMin, yMax, zMin, zMax, xSp, ySp, zSp, x0, y0, z0, center)

    shiftScale = vtk.vtkImageShiftScale()
    shiftScale.SetScale(iRescaleSlope)
    shiftScale.SetShift(iRescaleIntercept)
    shiftScale.SetOutputScalarTypeToInt()
    shiftScale.ClampOverflowOn()
    shiftScale.SetInputConnection(dataImporter.GetOutputPort())
    shiftScale.Update()

    rowCosine   = numpy.array(direction_x)
    colCosine   = numpy.array(direction_y)
    sliceCosine = numpy.cross(rowCosine, colCosine)

    rotation_matrix = numpy.column_stack((rowCosine, colCosine, sliceCosine))
    transform_matrix = numpy.eye(3)
    transform_matrix[:3, :3] = rotation_matrix.T

    mat = vtk.vtkMatrix4x4()
    for i in range(3):
        for j in range(3):
            mat.SetElement(i, j, transform_matrix[i, j])
        mat.SetElement(i, 3, -origin[i])

    volume = vtk.vtkVolume()
    mapper = vtk.vtkOpenGLGPUVolumeRayCastMapper()
    mapper.SetInputConnection(shiftScale.GetOutputPort())
    volume.SetUserMatrix(mat)

    colorFun   = vtk.vtkColorTransferFunction()
    opacityFun = vtk.vtkPiecewiseFunction()
    prop = vtk.vtkVolumeProperty()
    prop.SetColor(colorFun)
    prop.SetScalarOpacity(opacityFun)
    prop.SetInterpolationTypeToLinear()

    opacityWindow, opacityLevel = 2048, 1024
    mn = min_npV * iRescaleSlope + iRescaleIntercept
    mx = max_npV * iRescaleSlope + iRescaleIntercept
    t0_adj, t1_adj, t2_adj = adjThresholds

    if blendType == 0:   # MIP
        colorFun.AddRGBSegment(0.0, 1.0, 1.0, 1.0, 255.0, 1.0, 1.0, 1.0)
        opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                              opacityLevel + 0.5 * opacityWindow, 1.0)
        mapper.SetBlendModeToMaximumIntensity()

    elif blendType == 1:  # Composite, no shading
        colorFun.AddRGBSegment(opacityLevel - 0.5 * opacityWindow, 0.0, 0.0, 0.0,
                               opacityLevel + 0.5 * opacityWindow, 1.0, 1.0, 1.0)
        opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                              opacityLevel + 0.5 * opacityWindow, 1.0)
        mapper.SetBlendModeToComposite()
        prop.ShadeOff()

    elif blendType == 2:  # Composite, shading on
        colorFun.AddRGBSegment(opacityLevel - 0.5 * opacityWindow, 0.0, 0.0, 0.0,
                               opacityLevel + 0.5 * opacityWindow, 1.0, 1.0, 1.0)
        opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0,
                              opacityLevel + 0.5 * opacityWindow, 1.0)
        mapper.SetBlendModeToComposite()
        prop.ShadeOn()

    elif blendType in (3, 5):  # CT Bone1 / CT Bone2
        width_s = 80
        colorFun.AddRGBPoint(mn, 0.3, 0.3, 1.0, 0.5, 0.0)
        colorFun.AddRGBPoint(t0_adj, 0.95, 0.95, 0.85, 0.5, 0.0)
        colorFun.AddRGBPoint((t0_adj + t2_adj) / 2, 0.75, 0.4, 0.35, 0.5, 0.0)
        colorFun.AddRGBPoint(t2_adj, 0.95, 0.84, 0.19, 0.5, 0.0)
        colorFun.AddRGBPoint(mx, 0.78, 0.78, 0.92, 0.5, 0.0)

        opacityFun.AddPoint(mn, 0, 0.5, 0.0)
        if blendType == 3:  # Bone1: include soft-tissue peak
            opacityFun.AddPoint(t0_adj, 0.0, 0.5, 0.0)
            opacityFun.AddPoint(t0_adj + width_s / 2.0, 0.5, 0.5, 0.0)
            opacityFun.AddPoint(t0_adj + width_s, 0.0, 0.5, 0.0)
        opacityFun.AddPoint(t1_adj, 0, 0.5, 0.0)
        opacityFun.AddPoint(t2_adj, 0.5, 0.5, 0.0)
        opacityFun.AddPoint(mx, 0.75, 0.5, 0.0)

        prop.ShadeOn()
        mapper.SetBlendModeToComposite()
        prop.SetAmbient(0.2)
        prop.SetDiffuse(1.0)
        prop.SetSpecular(0.0)
        prop.SetSpecularPower(1.0)
        prop.SetScalarOpacityUnitDistance(0.8919)

    volume.SetMapper(mapper)
    volume.SetProperty(prop)

    return mn, mx, adjThresholds, [dx, dy, dz], volume
