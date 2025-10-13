import pydicom
import numpy as np
import os

def readDICOMHeader(dicomfile):
    info={}
    info["PatientName"] = dicomfile.PatientName
    info["Rows"] = dicomfile.Rows
    info["Columns"] = dicomfile.Columns
    info["VerticalPixelSize"] = dicomfile[0x0014, 0x6023].value
    info["HorizontalPixelSize"] = dicomfile[0x0014, 0x6024].value
    info["PixelSize"] = str(round(info["VerticalPixelSize"],2))+"/"+str(round(info["HorizontalPixelSize"],2))
    info["ScanType"] = 1
    info["ImageType"] = "dcm"
    info["StudyInstanceUID"] = dicomfile.StudyInstanceUID
    info["SeriesInstanceUID"] = dicomfile.SeriesInstanceUID
    info["SOPInstanceUID"] = dicomfile.SOPInstanceUID
    info["InstanceNumber"] = dicomfile.InstanceNumber
    info["TableAngle"] = dicomfile.TableAngle
    info["TableTraverse"] = dicomfile.TableTraverse
    info["DistanceSourceToDetector"] = dicomfile.DistanceSourceToDetector
    info["DistanceSourceToPatient"] = dicomfile.DistanceSourceToPatient
    info["StudyDescription"] = dicomfile.StudyDescription
    info["SeriesDescription"] = dicomfile.SeriesDescription
    return info


def loadDICOMImage(url):
    dicomfile = pydicom.dcmread(url)
    info = readDICOMHeader(dicomfile)
    return dicomfile.pixel_array, info

def loadDICOMImages(url):
    dcm_files = [f for f in os.listdir(url) if f.endswith('.dcm')]
    dcm_files.sort()  # 按文件名排序
    file_count = len(dcm_files)
    g = None
    for i, file in enumerate(dcm_files):
        filename=os.path.join(url, file)
        tempdata , info =loadDICOMImage(filename)
        if g is None:
            g = np.zeros((file_count,info['Rows'],info['Columns']))
        g[i] = tempdata.copy()
    return g

def makeDICOMFromExample(in_url, out_url, g):
    dcm_files = [f for f in os.listdir(in_url) if f.endswith('.dcm')]
    dcm_files.sort()  # 按文件名排序
    for i, file in enumerate(dcm_files):
        in_filename=os.path.join(in_url, file)
        out_filename=os.path.join(out_url, file)
        dicom = pydicom.dcmread(in_filename)
        dicom.PixelData = g[i].tobytes()
        dicom.save_as(out_filename,enforce_file_format=True)
