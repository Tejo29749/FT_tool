import sys
import time
import os

def appendQutsPaths():
    if sys.platform.startswith("linux"):
        sys.path.append('/opt/qcom/QUTS/Support/python')
        sys.path.append('/opt/qcom/QUTS/Support/python/ThriftGenFiles')
    elif sys.platform.startswith("win"):
        sys.path.append("C:\\Program Files (x86)\\Qualcomm\\QUTS\\Support\\python")
        sys.path.append("C:\\Program Files (x86)\\Qualcomm\\QUTS\\Support\\python\\ThriftGenFiles")
        sys.path.append("C:\\Program Files\\Qualcomm\\QUTS\\Support\\python")
        sys.path.append("C:\\Program Files\\Qualcomm\\QUTS\\Support\\python\\ThriftGenFiles")
    elif sys.platform.startswith("darwin"):
        sys.path.append('/Applications/Qualcomm/QUTS/QUTS.app/Contents/Support/python')
        sys.path.append('/Applications/Qualcomm/QUTS/QUTS.app/Contents/Support/python/ThriftGenFiles')
