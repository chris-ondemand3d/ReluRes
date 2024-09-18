###########################################################################################
#
#  Program: Console app to scan directory, load dicom series, and render the series volume
#  using GDCM (Grassroots DICOM). A DICOM library ( > 2.8.6 version required by performance)
#
#  Copyright (c) 2006-2011 Mathieu Malaterre
#  All rights reserved.
#  See Copyright.txt or http://gdcm.sourceforge.net/Copyright.html for details.
#
#     This software is distributed WITHOUT ANY WARRANTY; without even
#     the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the above copyright notice for more information.
#
###########################################################################################

import sys
import time

import gdcm
import numpy
import vtk
import matplotlib.pyplot as plt
#import cv2
import SimpleITK as sitk
from scipy import ndimage
from scipy.signal import argrelextrema
from skimage import data
from skimage.filters import threshold_multiotsu

class ProgressWatcher(gdcm.SimpleSubjectWatcher):
    def ShowProgress(self, sender, event):
        pe = gdcm.ProgressEvent.Cast(event)
        #print(pe.GetProgress())

    def EndFilter(self):
        pass  # print ("Yay ! I am done")

def get_gdcm_to_numpy_typemap():
    """Returns the GDCM Pixel Format to numpy array type mapping."""
    _gdcm_np = {gdcm.PixelFormat.UINT8: numpy.uint8,
                gdcm.PixelFormat.INT8: numpy.int8,
                # gdcm.PixelFormat.UINT12 :numpy.uint12,
                # gdcm.PixelFormat.INT12  :numpy.int12,
                gdcm.PixelFormat.UINT16: numpy.uint16,
                gdcm.PixelFormat.INT16: numpy.int16,
                gdcm.PixelFormat.UINT32: numpy.uint32,
                gdcm.PixelFormat.INT32: numpy.int32,
                # gdcm.PixelFormat.FLOAT16:numpy.float16,
                gdcm.PixelFormat.FLOAT32: numpy.float32,
                gdcm.PixelFormat.FLOAT64: numpy.float64}
    return _gdcm_np


def get_numpy_array_type(gdcm_pixel_format):
    """Returns a numpy array typecode given a GDCM Pixel Format."""
    return get_gdcm_to_numpy_typemap()[gdcm_pixel_format]


def gdcm_to_numpy(image):
    """Converts a GDCM image to a numpy array.
    """
    pf = image.GetPixelFormat()

    assert pf.GetScalarType() in get_gdcm_to_numpy_typemap().keys(), "Unsupported array type %s" % pf
    assert pf.GetSamplesPerPixel() == 1, "SamplesPerPixel is not 1" % pf.GetSamplesPerPixel()
    shape = image.GetDimension(0) * image.GetDimension(1)
    if image.GetNumberOfDimensions() == 3:
        shape = shape * image.GetDimension(2)

    dtype = get_numpy_array_type(pf.GetScalarType())
    gdcm_array = image.GetBuffer().encode("utf-8", errors="surrogateescape")
    volume = numpy.frombuffer(gdcm_array, dtype=dtype)

    if image.GetNumberOfDimensions() == 2:
        result = volume.reshape(image.GetDimension(0), image.GetDimension(1))
    elif image.GetNumberOfDimensions() == 3:
        result = volume.reshape(image.GetDimension(2), image.GetDimension(0), image.GetDimension(1))

    #    result.shape = shape
    return result

def toList(a):
	s = str(a)
	numbers = s.split('\\')
	float_numbers = [float(num) for num in numbers]
	return float_numbers

def getKey(item):
    return item[3]

def GetSpacingDirOrigin(ds):
    sSFG = gdcm.Tag(0x5200, 0x9229) # Shared Functional Group 
    sPFFG = gdcm.Tag(0x5200,0x9230) # Per frame Functional Group
    if ds.FindDataElement( sSFG ):		
        sis = ds.GetDataElement( sSFG )
        sqsis = sis.GetValueAsSQ()
        if sqsis.GetNumberOfItems():
            item1 = sqsis.GetItem(1)
            nestedds = item1.GetNestedDataSet()
            sPOS = gdcm.Tag(0x0020,0x9116) # Plane Orientation Sequence
            sPMS = gdcm.Tag(0x0028,0x9110) # Pixel Measure Sequence
            if nestedds.FindDataElement( sPOS ):
                prcs = nestedds.GetDataElement( sPOS )
                sqprcs = prcs.GetValueAsSQ()
                if sqprcs.GetNumberOfItems():
                    item2 = sqprcs.GetItem(1)
                    nestedds2 = item2.GetNestedDataSet()
                    sIOP = gdcm.Tag(0x0020,0x0037) #Image Orientation Patient
                    if nestedds2.FindDataElement( sIOP ):
                        cm = nestedds2.GetDataElement( sIOP )
                        imageOrientation = toList(cm.GetValue())
                        bIO = True
                        print("Image Orientation",imageOrientation)
                    else:
                        bIO = False
                        print("No Image Orientation")        
            if nestedds.FindDataElement( sPMS ):
                prcs = nestedds.GetDataElement( sPMS )
                sqprcs = prcs.GetValueAsSQ()
                if sqprcs.GetNumberOfItems():
                    item2 = sqprcs.GetItem(1)
                    nestedds2 = item2.GetNestedDataSet()
                    sPS = gdcm.Tag(0x0028,0x0030) #Pixel Spacing
                    if nestedds2.FindDataElement( sPS ):
                        cm = nestedds2.GetDataElement( sPS )
                        pixelSpacing = toList(cm.GetValue())
                        bPS = True
                        print("PixelSpacing",pixelSpacing)
                    else:
                        bPS = False
                        print("No Pixel Spacing")
                    sST = gdcm.Tag(0x0018,0x0050) # SLice Thickness
                    if nestedds2.FindDataElement( sST ):
                        cm = nestedds2.GetDataElement( sST )
                        sliceThickness = toList(cm.GetValue())
                        bST = True
                        print("SliceThickness",sliceThickness)
                    else:
                        bST = False
                        print("No Slice Thickness")

    if ds.FindDataElement( sPFFG ):
        sis = ds.GetDataElement( sPFFG )
        sqsis = sis.GetValueAsSQ()
        nFrame = sqsis.GetNumberOfItems()

        item = sqsis.GetItem(1)
        nestedds = item.GetNestedDataSet()
        sPPS = gdcm.Tag(0x0020,0x9113) # Plane Position Sequence
        if nestedds.FindDataElement( sPPS ):
            prcs = nestedds.GetDataElement( sPPS )
            sqprcs = prcs.GetValueAsSQ()
            if sqprcs.GetNumberOfItems():
                item2 = sqprcs.GetItem(1)
                nestedds2 = item2.GetNestedDataSet()
                sIP = gdcm.Tag(0x0020,0x0032)
                if nestedds2.FindDataElement( sIP ):
                    cm = nestedds2.GetDataElement( sIP )
                    pos0 = toList(cm.GetValue())
                    print("ImagePosition",pos0)
                else:
                    print(i,"No Image Position")

        item = sqsis.GetItem(nFrame)
        nestedds = item.GetNestedDataSet()
        sPPS = gdcm.Tag(0x0020,0x9113) # Plane Position Sequence
        if nestedds.FindDataElement( sPPS ):
            prcs = nestedds.GetDataElement( sPPS )
            sqprcs = prcs.GetValueAsSQ()
            if sqprcs.GetNumberOfItems():
                item2 = sqprcs.GetItem(1)
                nestedds2 = item2.GetNestedDataSet()
                sIP = gdcm.Tag(0x0020,0x0032)
                if nestedds2.FindDataElement( sIP ):
                    cm = nestedds2.GetDataElement( sIP )
                    bOri = True
                    pos1 = toList(cm.GetValue())
                    print("ImagePosition",pos1)
                else:
                    print("No Image Position")
                    bOri = False
    if (bIO and bOri):
        cosineX = numpy.array(imageOrientation[0:3])
        cosineY = numpy.array(imageOrientation[3:6])
        normal = numpy.cross(cosineX, cosineY)
        posV0 = numpy.array(pos0)
        posV1 = numpy.array(pos1)
        dist = (numpy.dot(normal,posV1)-numpy.dot(normal,posV0))/(nFrame-1)
        if (dist<0):
            bFlip = True
            origin = pos1
        else:
            bFlip = False
            origin= pos0
        return imageOrientation,sliceThickness,origin,pixelSpacing,abs(dist),bFlip        
    else:
        return -1

def GetZSpacing(dataset, tag, directionCosines):
    if (not dataset.FindDataElement(tag)):
        return -1
    sqi = dataset.GetDataElement(tag).GetValueAsSQ()
    nItems = sqi.GetNumberOfItems()
    if (not sqi or nItems == 0):
        return -2
    cosineX = numpy.array(directionCosines[0:3])
    cosineY = numpy.array(directionCosines[3:6])
    normal = numpy.cross(cosineX, cosineY)
    dist = numpy.zeros(nItems)

    for i in range(nItems):
        # print(i+1, "th item: in ", nItems, ":")
        item = sqi.GetItem(i + 1)
        subds = item.GetNestedDataSet()

        # Plane Position Sequence
        tpms = gdcm.Tag(0x0020, 0x9113)
        if (not subds.FindDataElement(tpms)):
            return -3

        sqi2 = subds.GetDataElement(tpms).GetValueAsSQ()
        if (not sqi2 or sqi2.GetNumberOfItems() == 0):
            return -4

        item2 = sqi2.GetItem(1)
        subds2 = item2.GetNestedDataSet()

        tps = gdcm.Tag(0x0020, 0x0032)
        if (not subds2.FindDataElement(tps)):
            print("Not exist 0020,0032")

        de2 = subds2.GetDataElement(tps)
        posV = toList(str(de2.GetValue()))
        pos = numpy.array(posV)
        dist[i] = numpy.dot(normal, pos)

    prev = dist[0]
    sum = 0
    for i in range(nItems - 1):
        sum = sum + (dist[i + 1] - prev)
        prev = dist[i + 1]

    return sum / (nItems - 1)


def numpy2VTK(img, spacing=[1.0, 1.0, 1.0], origin=[0.0,0.0,0.0],dirCosines=[1.0,0.0,0.0,0.0,1.0,0.0]):
    # evolved from code from Stou S.,
    # on http://www.siafoo.net/snippet/314
    # This function, as the name suggests, converts numpy array to VTK
    # Check origin, direction, spacing

    importer = vtk.vtkImageImport()

    img_data = img.astype('int16')
    img_string = img_data.tobytes()  # type short
    dim = img.shape

    # vtkData = numpy_support.numpy_to_vtk(num_array=img_data.ravel(), deep=True, array_type=vtk.VTK_UNSIGNED_INT)

    print(len(img_string), dim)
    # for i in range(100):
    #    prStr = ""
    #    for j in range(100):
    #       prStr += ' ' + str(img_string[(100+i)*375*375 + (100+j)*375 + 100])
    #    print(prStr)

    importer.CopyImportVoidPointer(img_string, len(img_string))  # (dim[0]*dim[1]*dim[2])
    importer.SetDataScalarType(vtk.VTK_SHORT)
    importer.SetNumberOfScalarComponents(1)

    extent = importer.GetDataExtent()
    importer.SetDataExtent(extent[0], extent[0] + dim[2] - 1,
                           extent[2], extent[2] + dim[1] - 1,
                           extent[4], extent[4] + dim[0] - 1)
    importer.SetWholeExtent(extent[0], extent[0] + dim[2] - 1,
                            extent[2], extent[2] + dim[1] - 1,
                            extent[4], extent[4] + dim[0] - 1)

    importer.SetDataSpacing(spacing[0], spacing[1], spacing[2])
    importer.SetDataOrigin(origin[0],origin[1],origin[2])
    cosX = numpy.array(dirCosines[0:3])
    cosY = numpy.array(dirCosines[3:6])
    cosZ = numpy.cross(cosX, cosY)
    R=numpy.transpose([cosX,cosY,cosZ])
    importer.SetDataDirection(R.flatten()) 

    return importer


def show_mid_slice(img_numpy, title='img'):
   """
   Accepts an 3D numpy array and shows median slices in all three planes
   """
   assert img_numpy.ndim == 3
   n_i, n_j, n_k = img_numpy.shape

   # sagittal (left image)
   center_i1 = int((n_i - 1) / 2)
   # coronal (center image)
   center_j1 = int((n_j - 1) / 2)
   # axial slice (right image)
   center_k1 = int((n_k - 1) / 2)

   show_slices([img_numpy[center_i1, :, :],
                img_numpy[:, center_j1, :],
                img_numpy[:, :, center_k1]])
   plt.suptitle(title)

def show_slices(slices):
   """
   Function to display a row of image slices
   Input is a list of numpy 2D image slices
   """
   fig, axes = plt.subplots(1, len(slices))
   for i, slice in enumerate(slices):
       axes[i].imshow(slice, cmap="gray", origin="lower")
   plt.show()


def load_dicom(directory,blendType=2):

    # Define the set of tags we are interested in, may need more
    t1 = gdcm.Tag(0x10, 0x20);  # Patient ID
    t2 = gdcm.Tag(0x10, 0x10);  # Patient Name
    t3 = gdcm.Tag(0x20, 0x10);  # Study ID
    t4 = gdcm.Tag(0x20, 0x0d);  # Study Instance UID
    t5 = gdcm.Tag(0x20, 0x0e);  # Series Instance UID
    t6 = gdcm.Tag(0x20, 0x11);  # Series Number
    t7 = gdcm.Tag(0x28, 0x08);  # Number of Frames
    t8 = gdcm.Tag(0x20, 0x32);  # Image Position
    t10 = gdcm.Tag(0x28, 0x30);  # Pixel Spacing
    t11 = gdcm.Tag(0x20, 0x37);  # Image Orientation Patient
    t12 = gdcm.Tag(0x28, 0x02);  # Samples per pixel
    t13 = gdcm.Tag(0x28, 0x04);  # Photometric Interpretation
    t14 = gdcm.Tag(0x28, 0x10);  # Rows
    t15 = gdcm.Tag(0x28, 0x11);  # Column
    t16 = gdcm.Tag(0x28, 0x101);  # BitStored
    t17 = gdcm.Tag(0x02, 0x02);  # Media Storage SOP Class UID
    t18 = gdcm.Tag(0x02, 0x03);  # Media Storage SOP Instance UID
    t19 = gdcm.Tag(0x02, 0x10);  # Transfer Syntax
    t20 = gdcm.Tag(0x08, 0x16);  # SOP Class UID
    t21 = gdcm.Tag(0x08, 0x18);  # SOP Instance UID
    t22 = gdcm.Tag(0x5200, 0x9229);  # Shared functional group
    t23 = gdcm.Tag(0x5200, 0x9230);  # Per frame functional group
    t24 = gdcm.Tag(0x0028, 0x1050);  # WindowCenter
    t25 = gdcm.Tag(0x0028, 0x1051);  # WindowWidth
    t26 = gdcm.Tag(0x0028, 0x1052);  # Rescale Intercept
    t27 = gdcm.Tag(0x0028, 0x1053);  # Rescale Slope
    t28 = gdcm.Tag(0x0028, 0x1054);  # Rescale Type

    # for profiling
    currentTime = time.time()

    # Iterate over directory
    d = gdcm.Directory();
    nfiles = d.Load(directory);
    if (nfiles == 0): return None

    filenames = d.GetFilenames()
    # print("Files ", filenames)

    #  Get rid of any Warning while parsing the DICOM files
    gdcm.Trace.WarningOff()

    # instanciate Scanner:
    sp = gdcm.Scanner.New();
    s = sp.__ref__()
    w = ProgressWatcher(s, 'Watcher')

    s.AddTag(t1);
    s.AddTag(t2);
    s.AddTag(t3);
    s.AddTag(t4);
    s.AddTag(t5);
    s.AddTag(t6);
    s.AddTag(t7);
    s.AddTag(t8);
    s.AddTag(t10);
    s.AddTag(t11);
    s.AddTag(t12);
    s.AddTag(t13);
    s.AddTag(t14);
    s.AddTag(t15);
    s.AddTag(t16);
    s.AddTag(t17);
    s.AddTag(t18);
    s.AddTag(t19);
    s.AddTag(t20);
    s.AddTag(t21);
    s.AddTag(t22);
    s.AddTag(t23);

    b = s.Scan(filenames);
    if (not b): sys.exit(1);
    print("success", b);

    # for profiling
    print("Time to Scan Directory and Dicom files", time.time() - currentTime)
    currentTime = time.time()

    dicomfiles = []
    patient_list = []
    study_list = []
    series_list = []

    for dFile in filenames:
        if (s.IsKey(dFile)):  # existing DICOM file

            #print(dFile)
            is_multiframe = 0

            pttv = gdcm.PythonTagToValue(s.GetMapping(dFile))
            pttv.Start()
            # iterate until the end:
            while (not pttv.IsAtEnd()):
                # get current value for tag and associated value:
                # if tag was not found, then it was simply not added to the internal std::map
                # Warning value can be None
                tag = pttv.GetCurrentTag()
                value = pttv.GetCurrentValue()

                if (tag == t1):
                    # print ("PatientID->",value)
                    if (value not in patient_list): patient_list.append(value)
                    patient_id = value
                elif (tag == t2):
                    # print ("PatientName->",value)
                    pass
                elif (tag == t3):
                    # print ("StudyID->",value)
                    pass
                elif (tag == t4):
                    # print ("StudyInstanceUID->",value)
                    if (value not in study_list): study_list.append(value)
                    study_id = value
                elif (tag == t6):
                    # print ("SeriesNum->",value)
                    pass
                elif (tag == t5):
                    # print ("SeriesInstanceUID->",value)
                    if (value not in series_list): series_list.append(value)
                    series_id = value
                elif (tag == t7):
                    # print ("NumberOfFrame->",value)
                    if (int(value) > 1):
                        is_multiframe = int(value)
                    else:
                        is_multiframe = 0
                elif (tag == t8):
                    #print("Image Patient Position->",value)
                    pass
                elif (tag == t19):
                    # print("Transfer Syntax->",value)
                    pass
                elif (tag == t20):
                    # print("SOP Class UID->",value)
                    pass
                elif (tag == t21):
                    # print("SOP Instance UID->",value)
                    instance_id = value
                    pass
                elif (tag == t22):
                    #print("Shared Functional Group Sequence->",value)
                    pass
                # increment iterator
                pttv.Next()

                # dicomfiles.append('PatientID':patient_id,'StudyID':study_id, 'SeriesID':seriesID, 'Multiframe':is_multiframe)
            if (not study_id): print("Missing StudyUID ")
            if (not series_id): print("Missing SeriesUID")

            dicomfiles.append(
                {'PatientID': patient_id, 'StudyID': study_id, 'SeriesID': series_id, 'Multiframe': is_multiframe,
                 'InstanceUID': instance_id, 'FileName': dFile})
            
    if (len(series_list)>1 and len(series_list)==0): return None # many series or no series
    else:     
        series_uid = series_list[0]

        series_imgfiles = s.GetAllFilenamesFromTagToValue(t5, series_uid)
        print("-----------------------------------------------------------------------")
        print(series_uid, ", # of Files: ", len(series_imgfiles))

        if (len(series_imgfiles) == 1):  # Single file series-> multiframe, or just single image
            # check multiframe
            image_file = series_imgfiles[0]
            nFrame = int(s.GetValue(image_file, t7))

            # check scout image

            if (nFrame > 1): # Multiframe Image
                print("Read Multiframe", image_file, nFrame)

                reader = gdcm.ImageReader()
                reader.SetFileName(image_file)
                if (not reader.Read()):
                    print("Cannot read image", image_file)
                    return None
                else:
                    image = reader.GetImage()
                    npVolume = gdcm_to_numpy(image)
                    print("Shape of Volume:", npVolume.shape)

                    # Image Dimension
                    w, d, h = image.GetDimension(0), image.GetDimension(1), image.GetDimension(2)

                    # Get DirectionCosines, Origin, Spacing
                    f = reader.GetFile()
                    ds = f.GetDataSet()
                    
                    dirCosines, sliceThickness, origin, pixelSpacing, dz, bFlip = GetSpacingDirOrigin(ds)
                    print(dirCosines, sliceThickness, origin, pixelSpacing, dz, bFlip) 
                    dx = pixelSpacing[0]
                    dy = pixelSpacing[1]
                    if (bFlip):
                        npVolume = numpy.flip(npVolume,0)

                    print("Samples per Pixel:", s.GetValue(image_file, t12))
                    print("Photometric Representation:", s.GetValue(image_file, t13))
                    print("Rows:", s.GetValue(image_file, t14))
                    print("Columns:", s.GetValue(image_file, t15))
                    print("BitStored:", s.GetValue(image_file, t16))

                    # f = reader.GetFile()
                    # ds = f.GetDataSet()
                    # print(GetZSpacing(ds, t23, cosines))

                    # CT default value
                    iRescaleSlope = 1.0
                    iRescaleIntercept = -1024.0
                    iWindowCenter = 1024
                    iWindowWidth = 4092

                    print("RescaleSlope:", s.GetValue(image_file, t27))
                    print("RescaleIntercept:", s.GetValue(image_file, t26))
                    #print("RescaleType:", s.GetValue(image_file, t28))
                    print("WindowCenter:", s.GetValue(image_file, t24))
                    print("WindowWidth:", s.GetValue(image_file, t25))

                    s27 = s.GetValue(image_file, t27)
                    s26 = s.GetValue(image_file, t26)
                    # s28 = s.GetValue(image_file, t28)
                    s24 = s.GetValue(image_file, t24)
                    s25 = s.GetValue(image_file, t25)

                    if s24: iWindowCenter = s24
                    if s25: iWindowWidth = s25
                    if s26: iRescaleIntercept = s26
                    if s27: iRescaleSlope = s27

            else:  # nFrame == 1
                print("Single image file with unique series id", image_file, nFrame)
                reader = gdcm.ImageReader()
                reader.SetFileName(image_file)
                if (not reader.Read()):
                    print("Cannot read image", image_file)
                    return None
                else:
                    npVolume = gdcm_to_numpy(reader.GetImage())
                    print("Shape of Volume:", npVolume.shape)
                    return None

        else:  # multiple files in a series
            # Read Postion and sorting
            series_files = []
            for i in range(len(series_imgfiles)):
                # convert ImagePosition
                strIP = s.GetValue(series_imgfiles[i], t8)
                posV = toList(strIP)
                series_files.append([series_imgfiles[i], posV[0], posV[1], posV[2]])

            sorted_series_files = sorted(series_files, key=getKey, reverse=False)

            dx = sorted_series_files[1][1] - sorted_series_files[0][1]
            dy = sorted_series_files[1][2] - sorted_series_files[0][2]
            dz = sorted_series_files[1][3] - sorted_series_files[0][3]
            if (dx != 0 or dy != 0):
                print("Weird, Not simple axial format", dx, dy, dz)  # Not simple axial format
            else:
                print("Slice distance", dz)

            reader = gdcm.ImageReader()
            reader.SetFileName(sorted_series_files[0][0])
            if (not reader.Read()):
                print("Cannot read image", sorted_series_files[0][0])

            image = reader.GetImage()
            pf = image.GetPixelFormat()
            assert pf.GetScalarType() in get_gdcm_to_numpy_typemap().keys(), "Unsupported array type %s" % pf
            #assert pf.GetSamplesPerPixel() == 1, "Support only one samples"
            w, d, h = image.GetDimension(0), image.GetDimension(1), len(sorted_series_files)

            spacing = image.GetSpacing()
            dx = float(spacing[0])
            dy = float(spacing[1])

            dtype = get_numpy_array_type(pf.GetScalarType())
            npVolume = numpy.zeros((h, w, d), dtype=dtype)
            print(w, d, h, dtype,dx,dy,dz)

            for i in range(h):
                reader = gdcm.ImageReader()
                reader.SetFileName(sorted_series_files[i][0])
                if (not reader.Read()):
                    print("Cannot read image", sorted_series_files[i][0])

                image = reader.GetImage()
                gdcm_array = image.GetBuffer().encode("utf-8", errors="surrogateescape")
                result = numpy.frombuffer(gdcm_array, dtype=dtype)
                npVolume[i, :, :] = result.reshape(w, d).copy() #numpy.flipud(result.reshape(d, w).copy())

            # Load images to numpy
            # 1st file에서 image plane, pixel정보 추출
            print("Pixel Spacing:", s.GetValue(sorted_series_files[0][0], t10))
            print("Image Orientation:", s.GetValue(sorted_series_files[0][0], t11))
            print("Origin:",sorted_series_files[0][1],sorted_series_files[0][2],sorted_series_files[0][3])
            print("Samples per Pixel:", s.GetValue(sorted_series_files[0][0], t12))
            print("Photometric Representation:", s.GetValue(sorted_series_files[0][0], t13))
            print("Rows:", s.GetValue(sorted_series_files[0][0], t14))
            print("Columns:", s.GetValue(sorted_series_files[0][0], t15))
            print("BitStored:", s.GetValue(sorted_series_files[0][0], t16))
            
            dirCosines = toList(s.GetValue(sorted_series_files[0][0], t11))
            origin = [sorted_series_files[0][1],sorted_series_files[0][2],sorted_series_files[0][3]]

            # default value
            iRescaleSlope = 1
            if (npVolume.min() >= 0):
                iRescaleIntercept = -1023
            else:
                iRescaleIntercept = 0

            iWindowCenter = 1024
            iWindowWidth = 4092

            print("RescaleSlope:", s.GetValue(sorted_series_files[0][0], t27))
            print("RescaleIntercept:", s.GetValue(sorted_series_files[0][0], t26))
            print("RescaleType:", s.GetValue(sorted_series_files[0][0], t28))
            print("WindowCenter:", s.GetValue(sorted_series_files[0][0], t24))
            print("WindowWidth:", s.GetValue(sorted_series_files[0][0], t25))

            s27 = s.GetValue(sorted_series_files[0][0], t27)
            s26 = s.GetValue(sorted_series_files[0][0], t26)
            # s28 = s.GetValue(sorted_series_files[0][0], t28)
            s24 = s.GetValue(sorted_series_files[0][0], t24)
            s25 = s.GetValue(sorted_series_files[0][0], t25)

            if s24: iWindowCenter = s24
            if s25: iWindowWidth = s25
            if s26: iRescaleIntercept = s26
            if s27: iRescaleSlope = s27


        # npVolume = (npVolume*iRescaleSlope+iRescaleIntercept)

        # pyplot single slice
        x = numpy.arange(0.0, (w+1)*dx, dx)
        y = numpy.arange(0.0, (d+1)*dy, dy)
        z = numpy.arange(0.0, (h+1)*dz, dz)
        # show_mid_slice(npVolume,title="CenterSlice")
        show_slices([npVolume[10,:,:],npVolume[70,:,:],npVolume[120,:,:]])

        print(npVolume.min(),npVolume.max(), iRescaleSlope, iRescaleIntercept)
    
        direction_x = dirCosines[0:3]
        direction_y = dirCosines[3:6]
        direction_z = numpy.cross(direction_x,direction_y)
        #direction = numpy.direction_x,direction_y,direction_z
        print([dx, dy, dz], origin, direction_x,direction_y, direction_z)

        #start_time = time.time()
        #thresholds = threshold_multiotsu(npVolume,4)
        #end_time = time.time()
        #print(thresholds, end_time-start_time)

    """  Computing Laplace histogram  
        minVal = m = npVolume.min()
        maxVal = npVolume.max()
        if minVal<0: 
            maxVal = maxVal-minVal
            minVal=0 
        print(minVal, maxVal)

        #Transpose
        #npVolume = npVolume.transpose(2,1,0)
        #laplacian = cv2.Laplacian(npVolume, cv2.CV_64F)
        #laplace_volume = ndimage.gaussian_laplace(npVolume,sigma=1).reshape(h,d,w)
        # Using SimpleITK
        #sitk_volume = sitk.GetImageFromArray(npVolume)
        #float_image = sitk.Cast(sitk_volume, sitk.sitkFloat64)
        #laplacianfilter = sitk.LaplacianImageFilter()
        #laplacian_volume = laplacianfilter.Execute(float_image)
        #print(npVolume.shape, laplacian_volume.GetSize())

        G = numpy.zeros(maxVal - minVal + 1, dtype=numpy.float64)
        Gc = numpy.zeros(maxVal - minVal + 1, dtype=numpy.float64)
        
        for i in range(2,h-2):
            for j in range(2,d-2):
                for k in range(2,w-2):
                    intensity = npVolume[i,j,k]
                    #G[npVolume[i,j,k]]=G[npVolume[i,j,k]]+laplace_volume[i,j,k]
                    G[intensity-m]=G[intensity-m]+6*intensity-npVolume[i+2,j,k]-npVolume[i-2,j,k]-npVolume[i,j+2,k]-npVolume[i,j-2,k]-npVolume[i,j,k+2]-npVolume[i,j,k-2]
        highest_value = 0.0
        opt_i = (minVal+maxVal)/2
        for i in range(maxVal-1, minVal, -1):
            sum=0
            Gc[i]=G[i]+Gc[i+1]
            if (Gc[i]>highest_value): 
                highest_value=Gc[i]
                opt_i = i
        print(opt_i,highest_value)
        # Find all local maxima
        print(G.min(),G.max(),Gc.min(),Gc.max())
        max = argrelextrema(Gc,numpy.greater)
        print(max)
        bin = numpy.arange(minVal+2,maxVal-2)
        #fig = plt.figure()
        plt.subplot(121)
        plt.plot(bin,G[minVal+2:maxVal-2])
        plt.subplot(122)
        plt.plot(bin,Gc[minVal+2:maxVal-2])
        plt.show()    
    """
    # vtk data importer
    # For VTK to be able to use the data, it must be stored as a VTK-image. This can be done by the vtkImageImport-class which
    # imports raw data and stores it.
    dataImporter = vtk.vtkImageImport()
    dataImporter = numpy2VTK(npVolume, [dx, dy, dz], origin, dirCosines)
    dataImporter.Update()

    print(dataImporter.GetWholeExtent(), dataImporter.GetDataOrigin(), dataImporter.GetDataSpacing(), dataImporter.GetDataScalarTypeAsString())

    (xMin, xMax, yMin, yMax, zMin, zMax) = dataImporter.GetWholeExtent()
    (xSpacing, ySpacing, zSpacing) = dataImporter.GetDataSpacing()
    (x0, y0, z0) = dataImporter.GetDataOrigin()
    center = [x0 + xSpacing * 0.5 * (xMin + xMax),
              y0 + ySpacing * 0.5 * (yMin + yMax),
              z0 + zSpacing * 0.5 * (zMin + zMax)]
    print(xMin, xMax, yMin, yMax, zMin, zMax, xSpacing, ySpacing, zSpacing, center)
    print(iRescaleSlope, iRescaleIntercept, iWindowCenter, iWindowWidth)

    shiftScale = vtk.vtkImageShiftScale()
    shiftScale.SetScale(iRescaleSlope)
    shiftScale.SetShift(iRescaleIntercept)
    shiftScale.SetOutputScalarTypeToInt()
    shiftScale.SetInputConnection(dataImporter.GetOutputPort())
    shiftScale.Update()

    volume = vtk.vtkVolume()
    mapper = vtk.vtkSmartVolumeMapper()
    mapper.SetInputConnection(shiftScale.GetOutputPort())
    
    mat = vtk.vtkMatrix4x4()
    for i in range(3):
        mat.SetElement(i,0,direction_x[i])
        mat.SetElement(i,1,direction_y[i])
        mat.SetElement(i,2,direction_z[i])
        mat.SetElement(i,3,-origin[i])
        i=i+1

    volume.SetUserMatrix(mat)

    # Transfer Function
    colorFun = vtk.vtkColorTransferFunction()
    opacityFun = vtk.vtkPiecewiseFunction()

    # Create the property and attach the transfer functions
    property = vtk.vtkVolumeProperty()
    # property.SetIndependentComponents(independentComponents);
    property.SetColor(colorFun)
    property.SetScalarOpacity(opacityFun)
    property.SetInterpolationTypeToLinear()
    # Try other volume rendering options
    opacityWindow = 2048
    opacityLevel = 1280

    if (blendType == 0):  # MIP
        colorFun.AddRGBSegment(0.0, 1.0, 1.0, 1.0, 255.0, 1.0, 1.0, 1.0)
        opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0, opacityLevel + 0.5 * opacityWindow, 1.0)
        mapper.SetBlendModeToMaximumIntensity()
    elif (blendType == 1):  # ShadeOff
        colorFun.AddRGBSegment(opacityLevel - 0.5 * opacityWindow, 0.0, 0.0, 0.0, opacityLevel + 0.5 * opacityWindow,
                               1.0, 1.0, 1.0)
        opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0, opacityLevel + 0.5 * opacityWindow, 1.0)
        mapper.SetBlendModeToComposite()
        property.ShadeOff()
    elif (blendType == 2):  # Shade On
        colorFun.AddRGBSegment(opacityLevel - 0.5 * opacityWindow, 0.0, 0.0, 0.0, opacityLevel + 0.5 * opacityWindow,
                               1.0, 1.0, 1.0)
        opacityFun.AddSegment(opacityLevel - 0.5 * opacityWindow, 0.0, opacityLevel + 0.5 * opacityWindow, 1.0)
        mapper.SetBlendModeToComposite()
        property.ShadeOn()
    elif (blendType == 3):  # CT Bone1
        colorFun.AddRGBPoint(-3024, 0, 0, 0, 0.5, 0.0)
        colorFun.AddRGBPoint(-16, 0.73, 0.25, 0.30, 0.49, 0.61)
        colorFun.AddRGBPoint(641, .90, .82, .56, .5, 0.0)
        colorFun.AddRGBPoint(3071, 1, 1, 1, .5, 0.0)
        opacityFun.AddPoint(-3024, 0, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(400, 0, .49, .61) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(1000, .72, .5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(3071, .71, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        property.ShadeOn()
        mapper.SetBlendModeToComposite()
        property.SetAmbient(0.1)
        property.SetDiffuse(0.9)
        property.SetSpecular(0.2)
        property.SetSpecularPower(10.0)
        property.SetScalarOpacityUnitDistance(0.8919)
    elif (blendType == 5): # CT Bone2
        colorFun.AddRGBPoint(-3024, 0, 0, 0, 0.5, 0.0)
        colorFun.AddRGBPoint(-1195, 0.73, 0.25, 0.30, 0.5, 0.0)
        colorFun.AddRGBPoint(761, .90, .82, .56, .5, 0.0)
        colorFun.AddRGBPoint(1374, .90, .82, .56, .5, 0.0)
        colorFun.AddRGBPoint(3071, 1, 1, 1, .5, 0.0)
        property.ShadeOff()
        opacityFun.AddPoint(-3024, 0, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(199, 0, .49, .61) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(1000, .08, .5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(1734, .42, .5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        opacityFun.AddPoint(3071, .45, 0.5, 0.0) # IntensityValue, Opacity, Position of midpoint, sharpness of midpoint
        mapper.SetBlendModeToComposite()
        property.SetAmbient(0.1)
        property.SetDiffuse(0.9)
        property.SetSpecular(0.2)
        property.SetSpecularPower(10.0)
        property.SetScalarOpacityUnitDistance(0.8919)

    volume.SetMapper(mapper)
    volume.SetProperty(property)

    return volume