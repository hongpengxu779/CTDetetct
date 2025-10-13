import sys
import os
import time
import numpy as np
from leapctype import *

def makeAttenuationRadiographs(leapct, g, air_scan=None, dark_scan=None, ROI=None, isAttenuationData=False):
    # 该函数为直接复制，仅对其中ROI部分的内存进行优化，防止爆内存
    if g is None:
        print('Error: no data given')
        return False
    if len(g.shape) != 3:
        print('Error: input data must by 3D')
        return False
    if dark_scan is not None:
        if isinstance(dark_scan, int) or isinstance(dark_scan, float):
            # print('dark is constant')
            pass
        elif len(dark_scan.shape) != 2 or g.shape[1] != dark_scan.shape[0] or g.shape[2] != dark_scan.shape[1]:
            print('Error: dark scan image size is invalid')
            return False
    if air_scan is not None:
        if isinstance(air_scan, int) or isinstance(air_scan, float):
            # print('air is constant')
            pass
        elif len(air_scan.shape) != 2 or g.shape[1] != air_scan.shape[0] or g.shape[2] != air_scan.shape[1]:
            print('Error: air scan image size is invalid')
            return False
    if ROI is not None:
        if ROI[0] < 0 or ROI[2] < 0 or ROI[1] < ROI[0] or ROI[3] < ROI[2] or ROI[1] >= g.shape[1] or ROI[3] >= g.shape[2]:
            print('Error: invalid ROI')
            return False

    # 检查是否有torch库
    has_torch = False
    try:
        import torch
        has_torch = True
    except ImportError:
        has_torch = False

    if has_torch == True and type(air_scan) is torch.Tensor:
        minAir = torch.min(air_scan[air_scan > 0.0])
        air_scan[air_scan <= 0.0] = minAir
    elif type(air_scan) is np.ndarray:
        minAir = np.min(air_scan[air_scan > 0.0])
        air_scan[air_scan <= 0.0] = minAir

    if isAttenuationData:
        if ROI is None:
            return True
        else:
            leapct.expNeg(g)

    # Perform Flat Fielding
    if dark_scan is not None:
        if air_scan is not None:
            if isinstance(dark_scan, int) or isinstance(dark_scan, float):
                air_scan = air_scan - dark_scan
                if isinstance(air_scan, int) or isinstance(air_scan, float):
                    g[:] = (g[:] - dark_scan) / air_scan
                else:
                    g[:] = (g[:] - dark_scan) / air_scan[None, :, :]
            else:
                g[:] = (g[:] - dark_scan[None, :, :]) / (air_scan - dark_scan)[None, :, :]
        else:
            if isinstance(dark_scan, int) or isinstance(dark_scan, float):
                g[:] = g[:] - dark_scan
            else:
                g[:] = g[:] - dark_scan[None, :, :]
    else:
        if isinstance(air_scan, int) or isinstance(air_scan, float):
            g[:] = g[:] / air_scan
        elif air_scan is not None:
            g[:] = g[:] / air_scan[None, :, :]

    # Perform Flux Correction
    g[g <= 100.0] = 100.0
    if ROI is not None:
        g -= g.min()
        if has_torch == True and type(g) is torch.Tensor:
            postageStamp = torch.mean(g[:, ROI[0]:ROI[1] + 1, ROI[2]:ROI[3] + 1], axis=(1, 2))
        else:
            postageStamp = np.mean(g[:, ROI[0]:ROI[1] + 1, ROI[2]:ROI[3] + 1], axis=(1, 2))
        print('ROI mean: ' + str(np.mean(postageStamp)) + ', standard deviation: ' + str(np.std(postageStamp)))
        for i in range(g.shape[0]):
            # g[:,:,:] = g[:,:,:] / postageStamp[:,None,None]
            g[i] = g[i] / postageStamp[i, None, None]

    # Convert to attenuation
    if np.isnan(g).any():
        print('some nans exist')
    g[g <= 0.0] = 2.0 ** -16
    leapct.negLog(g)

    return True