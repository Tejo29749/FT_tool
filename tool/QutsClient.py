# -----------------------------------------------------------------------------
# QutsClient.py
#
# Contains the entry point for starting and connecting to QUTS server
#
# Copyright (c) 2018-2021 Qualcomm Technologies, Incorporated.
# Qualcomm Proprietary.
# All Rights Reserved.
# -----------------------------------------------------------------------------
import os
from threading import Thread
import time
import datetime
import sys
import threading
import signal
import getpass

from threading import Lock
from struct import pack, unpack

from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.protocol import TProtocolDecorator
from thrift.protocol.TProtocol import TProtocolBase
from thrift.server import TServer
from thrift import TMultiplexedProcessor
from thrift.Thrift import TType
from thrift.Thrift import TMessageType

from thrift.compat import binary_to_str, str_to_binary
import types

from six.moves import queue
import logging
import socket
import thrift.protocol.TBinaryProtocol
from thrift.transport import TTransport
from thrift.server.TServer import TSimpleServer

import tempfile

import pathUtility
pathUtility.appendQutsPaths()

import QutsService.QutsService
import QutsService.constants

import DeviceManager.DeviceManager
import DeviceManager.constants
import UtilityService.UtilityService
import UtilityService.constants

import ClientCallback.ClientCallbackServer
import ClientCallback.ClientCallback
import ClientCallback.constants
import LogSession.LogSession
import Common.ttypes


#Platform specific path for Active QUTSService Port File
if sys.platform.startswith("linux"):
    QUTS_SERVICE_PORT_FILE = '/opt/Qualcomm/QUTS/ActiveQutsServicePort'
elif sys.platform.startswith("win"):
    QUTS_SERVICE_PORT_FILE = r"C:\ProgramData\Qualcomm\QUTS\ActiveQutsServicePort"
elif sys.platform.startswith("darwin"):
    QUTS_SERVICE_PORT_FILE = '/Library/Application Support/Qualcomm/QUTS/ActiveQutsServicePort'
	
QUTS_STOP_EXCEPTION_MESSAGE = r"Invalid API call. Check if a Quts API call was made after stop() was invoked."
MAX_QUTSSERVICE_CONN_RETRY_COUNT = 3 #Max attempts for retrying QutsService Connection 

LICENSE_ERROR = False

class ResponseInfo:
    def __init__(self):
        self.responseEvent = threading.Event()
        self.response = None
        self.name = None
        self.type = None
        self.seqid = None

class ServerClientSocket(TTransport.TServerTransportBase):
    def __init__(self, hostname, port):
        self.socket = TSocket.TSocket(hostname, port)
        self.socket.open()

    def accept(self):
        if not self.socket.isOpen():
            raise TTransport.TTransportException(TTransport.TTransportException.NOT_OPEN)
        return self.socket

    def close(self):
        self.socket.close()

class CallbackProxy():
    def __init__(self, server):
        self.server = server;

    def serve(self):
        try:
            self.server.serve()
        except TTransport.TTransportException:
            pass

class TAcceleratedBufferedTransportFactory(TTransport.TBufferedTransportFactory):

    def getTransport(self, trans):
        buffersize = (512 * 1024)
        buffered = TTransport.TBufferedTransport(trans, buffersize)
        return buffered


class QutsTProtocolDecorator():
    def __init__(self, protocol):
        TProtocolBase(protocol)
        self.protocol = protocol       

    def __getattr__(self, name):
        if hasattr(self.protocol, name):
            member = getattr(self.protocol, name)
            if type(member) in [
                types.MethodType,
                types.FunctionType,
                types.LambdaType,
                types.BuiltinFunctionType,
                types.BuiltinMethodType,
            ]:
                return lambda *args, **kwargs: self._wrap(member, args, kwargs)
            else:
                return member
        raise AttributeError(name)

    def _wrap(self, func, args, kwargs):
        if isinstance(func, types.MethodType):
            result = func(*args, **kwargs)
        else:
            result = func(self.protocol, *args, **kwargs)
        return result
        
        
class QutsTMultiplexedProtocol(QutsTProtocolDecorator):

    SEPARATOR = ":"
    def __init__(self, protocol, serviceName):
        QutsTProtocolDecorator.__init__(self, protocol)
        self.serviceName = serviceName

    def writeMessageBegin(self, name, type, seqid):
        if (type == TMessageType.CALL or
                type == TMessageType.ONEWAY):
            self.protocol.writeMessageBegin(
                self.serviceName + QutsTMultiplexedProtocol.SEPARATOR + name,
                type,
                seqid
            )
        else:
            self.protocol.writeMessageBegin(name, type, seqid)
                


class QutsClient:
    def __init__(self, clientName, hostname='127.0.0.1', registrationPort=QutsService.constants.QUTS_REGISTRATION_PORT, multithreadedClient = False, disableQutsSignalHandler = False, qutsOperatingMode = Common.ttypes.QutsOperatingMode.DEVICE_DISCOVERY):
        if sys.version_info.major < 3:
            print('Current Python version is not supported = ')
            print(sys.version_info)
            raise Exception("\n Error *************** Please install Python3.8 and above. Try using command >python3 UserScript.py *******************")

        self.transport = None
        self.serverThread = None
        self.callbackProxy = None
        self.callbackServer = None
        self.callbackClientServer = None
        socket = None
        transport = None
        protocol = None
        registerClient = None
        buffersize = (512*1024)
        qutsServiceConnectStatus = False
        retryCount = 0
        port = 0
        
        if(not multithreadedClient):            
            self.multithreadedClient = False
        else:            
            self.multithreadedClient = True
        
        print("\nStart Time: ", datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        
        while retryCount <= MAX_QUTSSERVICE_CONN_RETRY_COUNT:
            try:           
                socket = TSocket.TSocket(hostname, registrationPort)
                socket.setTimeout(120000)
                transport = TTransport.TBufferedTransport(socket, buffersize)
                protocol = TBinaryProtocol.TBinaryProtocol(transport)
                protocol = QutsTMultiplexedProtocol(protocol, QutsService.constants.QUTS_SERVICE_NAME)
                registerClient = QutsService.QutsService.Client(protocol)
                logging.getLogger('thrift.transport.TSocket').setLevel(logging.CRITICAL)
                socket.open()
                logging.getLogger('thrift.transport.TSocket').setLevel(logging.WARNING)
		
                #Special Handling for Linux using current user login
                if sys.platform.startswith("linux"):
                    qutsClientInfo = Common.ttypes.ClientInfo(clientName,"",False,"",getpass.getuser(),qutsOperatingMode)
                    port = registerClient.registerSecureClient(qutsClientInfo)
                else:
                    qutsClientInfo = Common.ttypes.ClientInfo(clientName, "", False, "", "",qutsOperatingMode)
                    port = registerClient.registerSecureClient(qutsClientInfo)
                
                qutsServiceConnectStatus = True
                break
            except:
                try:
                  logging.getLogger('thrift.transport.TSocket').setLevel(logging.WARNING)           
                  portFile = open(QUTS_SERVICE_PORT_FILE, "rb")           
                  bytes = portFile.read(4)
                  registrationPort = int.from_bytes(bytes, sys.byteorder) 
                  print("\nRetrying connect to quts on port: ", registrationPort , "\n")
		   
                  socket = TSocket.TSocket(hostname, registrationPort)
                  socket.setTimeout(120000)
                  transport = TTransport.TBufferedTransport(socket, buffersize)
                  protocol = TBinaryProtocol.TBinaryProtocol(transport)
                  protocol = QutsTMultiplexedProtocol(protocol, QutsService.constants.QUTS_SERVICE_NAME)
                  registerClient = QutsService.QutsService.Client(protocol)
                  socket.open()
		   
                  #Special Handling for Linux using current user login
                  if sys.platform.startswith("linux"):
                    qutsClientInfo = Common.ttypes.ClientInfo(clientName,"",False,"",getpass.getuser(),qutsOperatingMode)
                    port = registerClient.registerSecureClient(qutsClientInfo)
                  else:
                    qutsClientInfo = Common.ttypes.ClientInfo(clientName, "", False, "", "",qutsOperatingMode)
                    port = registerClient.registerSecureClient(qutsClientInfo)
                  
                  if (port == QutsService.constants.UTS_INVALID_LICENSE_ERROR_CODE):
                    raise QutsInvalidLicenseException(QutsService.constants.UTS_INVALID_LICENSE_ERROR_CODE, "Invalid QUTS license, please check Qualcomm Package Manager.")

                  if (port == QutsService.constants.UTS_DB_UPDATING_ERROR_CODE):
                    raise QutsDbUpdatingException(QutsService.constants.UTS_DB_UPDATING_ERROR_CODE, "QUTS is updating DB, please try connecting again later.")
                  
                  qutsServiceConnectStatus = True
                  break
                except:
                     print("\nCould not connect to QutsService on port : ", registrationPort, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], "\n")
            
            if not qutsServiceConnectStatus:
                print("\nRetrying connection to QutsService..",datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], "\n")
                time.sleep(3)
                retryCount+=1       
        
        #Check QutsService connection status
        if not qutsServiceConnectStatus:
           raise Exception("Could not connect to QutsService after multiple retry attempts...")
               
        print("\nEnd of port and client setup: ", datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
        
        if (0 == port):
            raise Exception("Tried and failed to allocate client in Quts.")
			
        self.clientId = port
        registerClient = None
        protocol = None
        socket = None

        socket = TSocket.TSocket(hostname, port)
        socket.setTimeout(10000000)
        transport.close()
        transport = TTransport.TBufferedTransport(socket, buffersize)

        if(not multithreadedClient):
            self.bin_protocol = TBinaryProtocol.TBinaryProtocol(transport)            
        else:
            self.bin_protocol = QutsThreadedBinaryProtocol(transport)            

        protocol = QutsTMultiplexedProtocol(self.bin_protocol,
                                                             DeviceManager.constants.DEVICE_MANAGER_SERVICE_NAME)
        protocolUtilityService = QutsTMultiplexedProtocol(self.bin_protocol,
                                                                           UtilityService.constants.UTILITY_SERVICE_NAME)
        if (port == QutsService.constants.UTS_INVALID_LICENSE_ERROR_CODE):
            global LICENSE_ERROR
            LICENSE_ERROR = True
            print("\n License Error ")
            raise QutsInvalidLicenseException(QutsService.constants.UTS_INVALID_LICENSE_ERROR_CODE, "Invalid QUTS license, please check Qualcomm Package Manager.")
            
        socket.open()
        
        self.deviceManager = DeviceManager.DeviceManager.Client(protocol)
        self.utilityService = UtilityService.UtilityService.Client(protocolUtilityService)

        self.callbackClientServer = ClientCallback.ClientCallbackServer.ClientCallbackServer()
        processor = TMultiplexedProcessor.TMultiplexedProcessor()
        processor.registerProcessor(ClientCallback.constants.CLIENT_CALLBACK_SERVICE_NAME,
                                    ClientCallback.ClientCallback.Processor(self.callbackClientServer))
        callbackPort = port + 1
        self.transport = ServerClientSocket(hostname, callbackPort)
        tfactory = TAcceleratedBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()

        self.callbackServer = QutsTSimpleServer(processor, self.transport, tfactory, pfactory)
        self.callbackProxy = CallbackProxy(self.callbackServer)

        self.serverThread = Thread(target=self.callbackProxy.serve)
        self.serverThread.daemon = True
        self.serverThread.start()
        self.protocol = protocol

        if (not disableQutsSignalHandler and threading.current_thread().__class__.__name__  == '_MainThread'):
            signal.signal(signal.SIGINT, self.signalHandler)
            signal.signal(signal.SIGTERM, self.signalHandler)
		
    def signalHandler(self, sig, frame):
        self.stop()
        time.sleep(2)
        sys.exit()
		



    def __del__(self):
        self.stop()		
        if(LICENSE_ERROR == False):
          self.transport.close()               
        self.transport = None
        self.serverThread = None
        self.callbackProxy = None
        self.callbackServer = None
        self.callbackClientServer = None

    def stop(self):
        if (self.multithreadedClient):
            print("Stopping multithreaded client")
            self.bin_protocol.isStopSignaled = True
            
        self.clearCallbacks()


    def getDeviceManager(self):
        return self.deviceManager

    def getUtilityService(self):
        return self.utilityService

    def createService(self, serviceName, deviceHandle):
        identifier = self.deviceManager.createService(serviceName, deviceHandle)
        protocol = QutsTMultiplexedProtocol(self.bin_protocol, identifier)

        return protocol

    def openLogSession(self, files):
        identifier = self.deviceManager.openLogSession(files)
        protocol = QutsTMultiplexedProtocol(self.bin_protocol, identifier)
        return LogSession.LogSession.Client(protocol)

    def openLogSessionWithAdvanceOptions(self, files, openFileOptions):
        identifier = self.deviceManager.openLogSessionWithAdvanceOptions(files, openFileOptions)
        protocol = QutsTMultiplexedProtocol(self.bin_protocol, identifier)
        return LogSession.LogSession.Client(protocol)

    def openLogSessionWithOptions(self, openFileOptions):
        identifier = self.deviceManager.openLogSessionWithOptions(openFileOptions)
        protocol = QutsTMultiplexedProtocol(self.bin_protocol, identifier)
        return LogSession.LogSession.Client(protocol)
        
    def getActiveLogSession(self):
        identifier = self.deviceManager.getActiveLogSession()
        protocol = QutsTMultiplexedProtocol(self.bin_protocol, identifier)
        return LogSession.LogSession.Client(protocol)

#region CallbackFunction
    #Callback implementation, Do not modify this region.
    def setOnMessageCallback(self, callback):
        self.callbackClientServer.onMessageCallback = callback

    def setOnDeviceConnectedCallback(self, callback):
        self.callbackClientServer.onDeviceConnectedCallback = callback

    def setOnDeviceDisconnectedCallback(self, callback):
        self.callbackClientServer.onDeviceDisconnectedCallback = callback

    def setOnDeviceModeChangeCallback(self, callback):
        self.callbackClientServer.onDeviceModeChangeCallback = callback

    def setOnProtocolAddedCallback(self, callback):
        self.callbackClientServer.onProtocolAddedCallback = callback

    def setOnProtocolRemovedCallback(self, callback):
        self.callbackClientServer.onProtocolRemovedCallback = callback

    def setOnProtocolStateChangeCallback(self, callback):
        self.callbackClientServer.onProtocolStateChangeCallback = callback

    def setOnProtocolFlowControlStatusChangeCallback(self, callback):
        self.callbackClientServer.onProtocolFlowControlStatusChangeCallback = callback

    def setOnProtocolLockStatusChangeCallback(self, callback):
        self.callbackClientServer.onProtocolLockStatusChangeCallback = callback

    def setOnProtocolMbnDownloadStatusChangeCallback(self, callback):
        self.callbackClientServer.onProtocolMbnDownloadStatusChangeCallback = callback

    def setOnClientCloseRequestCallback(self, callback):
        self.callbackClientServer.onClientCloseRequestCallback = callback

    def setOnMissingQShrinkHashFileCallback(self, callback):
        self.callbackClientServer.onMissingQShrinkHashFileCallback = callback

    def setOnLogSessionMissingQShrinkHashFileCallback(self, callback):
        self.callbackClientServer.onLogSessionMissingQShrinkHashFileCallback = callback

    def setOnAsyncResponseCallback(self, callback):
        self.callbackClientServer.onAsyncResponseCallback = callback

    def setOnDataQueueUpdatedCallback(self, callback):
        self.callbackClientServer.onDataQueueUpdatedCallback = callback

    def setOnDataViewUpdatedCallback(self, callback):
        self.callbackClientServer.onDataViewUpdatedCallback = callback

    def setOnServiceAvailableCallback(self, callback):
        self.callbackClientServer.onServiceAvailableCallback = callback

    def setOnServiceEndedCallback(self, callback):
        self.callbackClientServer.onServiceEndedCallback = callback

    def setOnServiceEventCallback(self, callback):
        self.callbackClientServer.onServiceEventCallback = callback

    def setOnImageManagementServiceEventCallback(self, callback):
        self.callbackClientServer.onImageManagementServiceEventCallback = callback

    def setOnDeviceConfigServiceEventCallback(self, callback):
        self.callbackClientServer.onDeviceConfigServiceEventCallback = callback

    def setOnQShrinkStateUpdated(self, callback):
        self.callbackClientServer.onQShrinkStateUpdatedCallback = callback

    def setOnDecryptionKeyStatusUpdateCallback(self, callback):
        self.callbackClientServer.onDecryptionKeyStatusUpdateCallback = callback

    def setOnLogSessionDecryptionKeyStatusUpdateCallback(self, callback):
        self.callbackClientServer.onLogSessionDecryptionKeyStatusUpdateCallback = callback

    def setOnServiceLockUpdateCallback(self, callback):
        self.callbackClientServer.onServiceLockUpdateCallback = callback

    def setOnRestrictedLogLicenseStatusUpdateCallback(self, callback):
        self.callbackClientServer.onRestrictedLogLicenseStatusUpdateCallback = callback

    def setOnQspsMessageCallback(self, callback):
        self.callbackClientServer.onQspsMessageCallback = callback

    def setOnHyperVisorDataChangedCallback(self, callback):
        self.callbackClientServer.onHyperVisorDataChangedCallback = callback

    #Callback implementation, Do not modify this region.
    def clearCallbacks(self):
        if (self.callbackClientServer):
            self.callbackClientServer.onMessageCallback = None
            self.callbackClientServer.onDeviceConnectedCallback = None
            self.callbackClientServer.onDeviceDisconnectedCallback = None
            self.callbackClientServer.onDeviceModeChangeCallback = None
            self.callbackClientServer.onProtocolAddedCallback = None
            self.callbackClientServer.onProtocolRemovedCallback = None
            self.callbackClientServer.onProtocolStateChangeCallback = None
            self.callbackClientServer.onProtocolFlowControlStatusChangeCallback = None
            self.callbackClientServer.onProtocolLockStatusChangeCallback = None
            self.callbackClientServer.onProtocolMbnDownloadStatusChangeCallback = None
            self.callbackClientServer.onClientCloseRequestCallback = None
            self.callbackClientServer.onMissingQShrinkHashFileCallback = None
            self.callbackClientServer.onLogSessionMissingQShrinkHashFileCallback = None
            self.callbackClientServer.onAsyncResponseCallback = None
            self.callbackClientServer.onDataQueueUpdatedCallback = None
            self.callbackClientServer.onDataViewUpdatedCallback = None
            self.callbackClientServer.onServiceAvailableCallback = None
            self.callbackClientServer.onServiceEndedCallback = None
            self.callbackClientServer.onServiceEventCallback = None
            self.callbackClientServer.onImageManagementServiceEventCallback = None
            self.callbackClientServer.onDeviceConfigServiceEventCallback = None
            self.callbackClientServer.onQShrinkStateUpdatedCallback = None
            self.callbackClientServer.onDecryptionKeyStatusUpdateCallback = None
            self.callbackClientServer.onLogSessionDecryptionKeyStatusUpdateCallback = None
            self.callbackClientServer.onServiceLockUpdateCallback = None
            self.callbackClientServer.onRestrictedLogLicenseStatusUpdateCallback = None
            self.callbackClientServer.onQspsMessageCallback = None
            self.callbackClientServer.onHyperVisorDataChangedCallback = None
#endregion //CallbackFunction

class QutsThreadedBinaryProtocol(object):
    def __init__(self, transport):        
		
        self.binaryProtocol = TBinaryProtocol.TBinaryProtocol(transport)

        self.transport = transport
        self.outstandingRequestsMutex = threading.Lock()
        self.writeMutex = threading.Lock()
        self.responseMutex = threading.Lock()
        self.seqIdMutex = threading.Lock()
        self.readMutex = threading.Lock()

        self.newRequestEvent = threading.Event()

        self.outstandingRequests = 0
        self.seqId = 0
        self.seqIdResponseDict = None
        self.response = None

        self.locked = False
        self.isStopSignaled = False

        self.buffer = []
        self.receiveThread = None

        self._fast_encode = self.binaryProtocol._fast_encode
        self._fast_decode = self.binaryProtocol._fast_decode
        self.trans = self.binaryProtocol.trans




    def __del__(self):
        self.isStopSignaled = True

    def readMessage(self, ftype, buffer):
        if (ftype == TType.BOOL):
            value = self.binaryProtocol.readBool()
            buffer.append(value)
        if (ftype == TType.BYTE):
            value = self.binaryProtocol.readByte()
            buffer.append(value)
        if (ftype == TType.STRING):
            value = self.binaryProtocol.readBinary() # Leave it in binary format here, can do string conversion later only when needed in readString(). From *_result
                                                     # object in recv_<API name>(), the ReadBinary() or ReadString() is called based on whether the field
                                                     # in the result is a binary or string format respectively. So handle binary to string conversion at that point
                                                     # in ReadString() when we know it needs to be converted to string and leave as binary in ReadBinary()
            buffer.append(value)
        if (ftype == TType.I64):
            value = self.binaryProtocol.readI64()
            buffer.append(value)
        if (ftype == TType.I32):
            value = self.binaryProtocol.readI32()
            buffer.append(value)
        if (ftype == TType.I16):
            value = self.binaryProtocol.readI16()
            buffer.append(value)
        if (ftype == TType.DOUBLE):
            value = self.binaryProtocol.readDouble()
            buffer.append(value)
        if (ftype == TType.STRUCT):
            self.binaryProtocol.readStructBegin()
            while True:
                (fname, ftype, fid) = self.binaryProtocol.readFieldBegin()
                buffer.append(ftype)
                if ftype == TType.STOP:
                    break
                buffer.append(fid)
                self.readMessage(ftype, buffer)
                self.binaryProtocol.readFieldEnd()
            self.binaryProtocol.readStructEnd()
        if (ftype == TType.LIST):
            (etype, size) = self.binaryProtocol.readListBegin()
            buffer.append(etype)
            buffer.append(size)
            for i in range(size):
                self.readMessage(etype, buffer)
            self.binaryProtocol.readListEnd()
        if (ftype == TType.SET):
            (etype, size) = self.binaryProtocol.readSetBegin()
            buffer.append(etype)
            buffer.append(size)
            for i in range(size):
                self.readMessage(etype, buffer)
            self.binaryProtocol.readSetEnd()
        if (ftype == TType.MAP):
            (keyType,valueType, size) = self.binaryProtocol.readMapBegin()
            buffer.append(keyType)
            buffer.append(valueType)
            buffer.append(size)
            for i in range(size):
                self.readMessage(keyType, buffer)
                self.readMessage(valueType, buffer)
            self.binaryProtocol.readMapEnd()


    def writeMessageEnd(self):
        if(self.isStopSignaled):
            raise Exception(QUTS_STOP_EXCEPTION_MESSAGE)
        result = self.binaryProtocol.writeMessageEnd()
        self.writeMutex.release()
        
        tid = threading.get_ident()        

        self.outstandingRequestsMutex.acquire()
        self.outstandingRequests += 1

        self.newRequestEvent.set()
        self.outstandingRequestsMutex.release()

        return result

    def writeMessageBegin(self, name, type, seqid):
        if(self.isStopSignaled):
            raise Exception(QUTS_STOP_EXCEPTION_MESSAGE)
        tid = threading.get_ident()
        if(TMessageType.CALL != type):
            self.seqIdMutex.acquire()
            val =  self.binaryProtocol.writeMessageBegin(name, type, seqid)
            self.seqIdMutex.release()
            return val
        else:
            self.writeMutex.acquire()
            self.seqIdMutex.acquire()

            self.locked = True
            self.seqId += 1
            try:
                self.responseMutex.acquire()

                if not self.seqIdResponseDict:
                   self.seqIdResponseDict = {}
                self.seqIdResponseDict[self.seqId] = ResponseInfo()
                self.responseMutex.release()

                return self.binaryProtocol.writeMessageBegin(name, type, self.seqId)
            except Exception as e:
                err = str(e)
                self.responseMutex.release()                
                raise Exception("Exception in writeMessageBegin, exception info = ", err)

    def stop(self):
        self.isStopSignaled = True

    def onRunReceiveData(self):
        tid = threading.get_ident()
        while (not self.isStopSignaled):
            while (self.outstandingRequests == 0):
                self.newRequestEvent.wait(.01)
                if (self.isStopSignaled):
                    break

            if (self.isStopSignaled):
                break

            (fname, mtype, seqid) = self.binaryProtocol.readMessageBegin()

            pBuffer = []
            self.readMessage(TType.STRUCT, pBuffer)

            self.outstandingRequestsMutex.acquire()
            self.outstandingRequests -= 1
            self.newRequestEvent.clear()
            self.outstandingRequestsMutex.release()

            
            self.responseMutex.acquire()
            

            if(seqid in self.seqIdResponseDict):
                self.seqIdResponseDict[seqid].response = pBuffer
                self.seqIdResponseDict[seqid].responseEvent.set()
                self.seqIdResponseDict[seqid].name = fname
                self.seqIdResponseDict[seqid].type = mtype
                self.seqIdResponseDict[seqid].seqid = seqid

            logMessage = "\nonRunReceiveData: event set for seqid {0}".format(seqid)
           

            self.responseMutex.release()
        

           

    def readMessageEnd(self):
        self.readMutex.release();
        return 0

    def readMessageBegin(self):
        tid = threading.get_ident()
        if not self.receiveThread:
           self.receiveThread = threading.Thread(target=self.onRunReceiveData)		
        if (not self.receiveThread.is_alive() and not self.isStopSignaled):
            self.receiveThread.daemon = True
            self.receiveThread.start() 		

        if(self.isStopSignaled):
            raise Exception(QUTS_STOP_EXCEPTION_MESSAGE)

        waitingForSeqId = 0
        if (self.locked):
            waitingForSeqId = self.seqId
            self.locked = False
            
            self.seqIdMutex.release()

        if (not (waitingForSeqId in self.seqIdResponseDict)):
            errorMessage = "Could not find seqid {0} in dictionary".format(waitingForSeqId)
            raise Exception(errorMessage)

        

        while (not self.seqIdResponseDict[waitingForSeqId].responseEvent.is_set()):
            self.seqIdResponseDict[waitingForSeqId].responseEvent.wait(.01)
            if(self.isStopSignaled):
                raise Exception(QUTS_STOP_EXCEPTION_MESSAGE)

        

        if (self.seqIdResponseDict[waitingForSeqId].response is not None):
            
            self.readMutex.acquire();

        responseObj = self.seqIdResponseDict[waitingForSeqId]

        self.responseMutex.acquire()
       
        self.seqIdResponseDict.pop(waitingForSeqId, None)
        self.responseMutex.release()

        if (responseObj.response is None):
            return 0

        self.responseObj = responseObj
        self.response = responseObj.response
        return (responseObj.name, responseObj.type, responseObj.seqid)

    def readFieldBegin(self):
        type = self.readByte()
        if type == TType.STOP:
            return (None, type, 0)
        id = self.readI16()
        return (None, type, id)

    def readStructBegin(self):
        pass

    def readByte(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            return val
        else:
            pass

    def readBool(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            if (0 ==  val or False == val):
                return False
            else:
                return True
        else:
            pass

    def readI16(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            return val
        else:
            pass

    def readI32(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            return val
        else:
            pass

    def readI64(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            return val
        else:
           pass

    def readDouble(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            return val
        else:
            pass

    def readString(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            strValue = binary_to_str(val)
            return strValue
        else:
            pass

    def _check_string_length(self, length):
        self.binaryProtocol._check_length(self.binaryProtocol.string_length_limit, length)

    def _check_container_length(self, length):
        self.binaryProtocol._check_length(self.binaryProtocol.container_length_limit, length)

    def writeStructBegin(self, name):
        pass

    def writeStructEnd(self):
        pass

    def writeFieldBegin(self, name, type, id):
        self.binaryProtocol.writeFieldBegin(name, type, id)

    def writeFieldEnd(self):
        pass

    def writeFieldStop(self):
        self.binaryProtocol.writeByte(TType.STOP)

    def writeMapBegin(self, ktype, vtype, size):
        self.binaryProtocol.writeMapBegin(ktype, vtype, size)

    def writeMapEnd(self):
        pass

    def writeListBegin(self, etype, size):
        self.binaryProtocol.writeListBegin(etype, size)

    def writeListEnd(self):
        pass

    def writeSetBegin(self, etype, size):
        self.binaryProtocol.writeSetBegin(etype, size)

    def writeSetEnd(self):
        pass

    def writeBool(self, bool):
        self.binaryProtocol.writeBool(bool)

    def writeString(self, data):
        self.binaryProtocol.writeString(data)

    def writeByte(self, byte):
        self.binaryProtocol.writeByte(byte)

    def writeI16(self, i16):
        self.binaryProtocol.writeI16(i16)

    def writeI32(self, i32):
        self.binaryProtocol.writeI32(i32)

    def writeI64(self, i64):
        self.binaryProtocol.writeI64(i64)

    def writeDouble(self, dub):
        self.binaryProtocol.writeDouble(dub)

    def writeBinary(self, str):
        self.binaryProtocol.writeBinary(str)

    def readStructEnd(self):
        pass

    def readFieldEnd(self):
        pass

    def readMapBegin(self):
        ktype = self.readByte()
        vtype = self.readByte()
        size = self.readI32()
        self._check_container_length(size)
        return (ktype, vtype, size)

    def readMapEnd(self):
        pass

    def readListBegin(self):
        etype = self.readByte()
        size = self.readI32()
        self._check_container_length(size)
        return (etype, size)

    def readListEnd(self):
        pass

    def readSetBegin(self):
        etype = self.readByte()
        size = self.readI32()
        self._check_container_length(size)
        return (etype, size)

    def readSetEnd(self):
        pass

    def readBinary(self):
        if (self.response != None and len(self.response) != 0):
            val = self.response.pop(0)
            return val
        else:
            pass

def readFile(filePath):
    with open(filePath, mode='rb') as file:
        return file.read()



class QutsTSimpleServer(TSimpleServer):
    """Wrapper to thrift TSimpleServer to prevent error message on exit."""

    def __init__(self, *args):
        TSimpleServer.__init__(self, *args)

    def serve(self):
        self.serverTransport.listen()
        bRun = True
        while bRun:            
            client = self.serverTransport.accept()
            if not client:
                continue
            trans = self.inputTransportFactory.getTransport(client)            
            prot = self.inputProtocolFactory.getProtocol(trans)            
            try:
                while bRun:
                    self.processor.process(prot, prot)
            except socket.error as e:
                print("\nCallback server closed. ") # This is currently only used for call back server, so print this specific message 
                bRun = False				
            except TTransport.TTransportException:
                pass			
            except Exception as x:                
                print("QutsTSimpleServer::serve() exception: " , x)

            trans.close()

class QutsInvalidLicenseException(Exception):
    """Exception raised for invalid/expired QUTS license.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class QutsDbUpdatingException(Exception):
    """Exception raised when QUTS is busy updating DBs.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
