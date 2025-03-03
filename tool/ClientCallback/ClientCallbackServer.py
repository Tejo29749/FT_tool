# -----------------------------------------------------------------------------
# ClientCallbackServer.py
#
# Contains the implementation of the thrift callback client for QUTS
#
# Copyright (c) 2023 Qualcomm Technologies, Incorporated.
# Qualcomm Proprietary.
# All Rights Reserved.
# -----------------------------------------------------------------------------


class ClientCallbackServer:
    def __init__(self):
#region CallbackMember
        #Callback implementation, Do not modify this region.
        self.onMessageCallback = None
        self.onDeviceConnectedCallback = None
        self.onDeviceDisconnectedCallback = None
        self.onDeviceModeChangeCallback = None
        self.onProtocolAddedCallback = None
        self.onProtocolRemovedCallback = None
        self.onProtocolStateChangeCallback = None
        self.onProtocolFlowControlStatusChangeCallback = None
        self.onProtocolLockStatusChangeCallback = None
        self.onProtocolMbnDownloadStatusChangeCallback = None
        self.onClientCloseRequestCallback = None
        self.onMissingQShrinkHashFileCallback = None
        self.onLogSessionMissingQShrinkHashFileCallback = None
        self.onAsyncResponseCallback = None
        self.onDataQueueUpdatedCallback = None
        self.onDataViewUpdatedCallback = None
        self.onServiceAvailableCallback = None
        self.onServiceEndedCallback = None
        self.onServiceEventCallback = None
        self.onImageManagementServiceEventCallback = None
        self.onDeviceConfigServiceEventCallback = None
        self.onQShrinkStateUpdatedCallback = None
        self.onDecryptionKeyStatusUpdateCallback = None
        self.onLogSessionDecryptionKeyStatusUpdateCallback = None
        self.onServiceLockUpdateCallback = None
        self.onRestrictedLogLicenseStatusUpdateCallback = None
        self.onQspsMessageCallback = None
        self.onHyperVisorDataChangedCallback = None
#endregion //CallbackMember

#region CallbackFunction
    #Callback implementation, Do not modify this region.
    def onMessage(self, level, location, title, description):
        if(self.onMessageCallback != None):
            self.onMessageCallback(level, location, title, description)

    def onDeviceConnected(self, deviceInfo):
        if(self.onDeviceConnectedCallback != None):
            self.onDeviceConnectedCallback(deviceInfo)

    def onDeviceDisconnected(self, deviceInfo):
        if(self.onDeviceDisconnectedCallback != None):
            self.onDeviceDisconnectedCallback(deviceInfo)

    def onDeviceModeChange(self, deviceHandle, newMode):
        if(self.onDeviceModeChangeCallback != None):
            self.onDeviceModeChangeCallback(deviceHandle, newMode)

    def onProtocolAdded(self, deviceInfo, protocolInfo):
        if(self.onProtocolAddedCallback != None):
            self.onProtocolAddedCallback(deviceInfo, protocolInfo)

    def onProtocolRemoved(self, deviceInfo, protocolInfo):
        if(self.onProtocolRemovedCallback != None):
            self.onProtocolRemovedCallback(deviceInfo, protocolInfo)

    def onProtocolStateChange(self, protocolHandle, newState):
        if(self.onProtocolStateChangeCallback != None):
            self.onProtocolStateChangeCallback(protocolHandle, newState)

    def onProtocolFlowControlStatusChange(self, protocolHandle, dir, newStatus):
        if(self.onProtocolFlowControlStatusChangeCallback != None):
            self.onProtocolFlowControlStatusChangeCallback(protocolHandle, dir, newStatus)

    def onProtocolLockStatusChange(self, protocolHandle, newStatus):
        if(self.onProtocolLockStatusChangeCallback != None):
            self.onProtocolLockStatusChangeCallback(protocolHandle, newStatus)

    def onProtocolMbnDownloadStatusChange(self, protocolHandle, newStatus):
        if(self.onProtocolMbnDownloadStatusChangeCallback != None):
            self.onProtocolMbnDownloadStatusChangeCallback(protocolHandle, newStatus)

    def onClientCloseRequest(self, closeReason):
        if(self.onClientCloseRequestCallback != None):
            self.onClientCloseRequestCallback(closeReason)

    def onMissingQShrinkHashFile(self, protocolHandle, missingFileGuid):
        if(self.onMissingQShrinkHashFileCallback != None):
            self.onMissingQShrinkHashFileCallback(protocolHandle, missingFileGuid)

    def onLogSessionMissingQShrinkHashFile(self, logSessionInstance, protocolHandle, missingFileGuid):
        if(self.onLogSessionMissingQShrinkHashFileCallback != None):
            self.onLogSessionMissingQShrinkHashFileCallback(logSessionInstance, protocolHandle, missingFileGuid)

    def onAsyncResponse(self, protocolHandle, transactionId):
        if(self.onAsyncResponseCallback != None):
            self.onAsyncResponseCallback(protocolHandle, transactionId)

    def onDataQueueUpdated(self, queueName, queueSize):
        if(self.onDataQueueUpdatedCallback != None):
            self.onDataQueueUpdatedCallback(queueName, queueSize)

    def onDataViewUpdated(self, viewName, viewSize, finished):
        if(self.onDataViewUpdatedCallback != None):
            self.onDataViewUpdatedCallback(viewName, viewSize, finished)

    def onServiceAvailable(self, serviceName, deviceHandle):
        if(self.onServiceAvailableCallback != None):
            self.onServiceAvailableCallback(serviceName, deviceHandle)

    def onServiceEnded(self, serviceName, deviceHandle):
        if(self.onServiceEndedCallback != None):
            self.onServiceEndedCallback(serviceName, deviceHandle)

    def onServiceEvent(self, serviceName, eventId, eventDescription):
        if(self.onServiceEventCallback != None):
            self.onServiceEventCallback(serviceName, eventId, eventDescription)

    def onImageManagementServiceEvent(self, serviceName, deviceHandle, protocolHandle, eventId, eventDescription):
        if(self.onImageManagementServiceEventCallback != None):
            self.onImageManagementServiceEventCallback(serviceName, deviceHandle, protocolHandle, eventId, eventDescription)

    def onDeviceConfigServiceEvent(self, serviceName, deviceHandle, protocolHandle, eventId, eventDescription):
        if(self.onDeviceConfigServiceEventCallback != None):
            self.onDeviceConfigServiceEventCallback(serviceName, deviceHandle, protocolHandle, eventId, eventDescription)

    def onQShrinkStateUpdated(self, protocolHandle, newState):
        if(self.onQShrinkStateUpdatedCallback != None):
            self.onQShrinkStateUpdatedCallback(protocolHandle, newState)

    def onDecryptionKeyStatusUpdate(self, protocolHandle, keyInfo):
        if(self.onDecryptionKeyStatusUpdateCallback != None):
            self.onDecryptionKeyStatusUpdateCallback(protocolHandle, keyInfo)

    def onLogSessionDecryptionKeyStatusUpdate(self, logSesssionInstance, protocolHandle, keyInfo):
        if(self.onLogSessionDecryptionKeyStatusUpdateCallback != None):
            self.onLogSessionDecryptionKeyStatusUpdateCallback(logSesssionInstance, protocolHandle, keyInfo)

    def onServiceLockUpdate(self, lockInfo, lockState):
        if(self.onServiceLockUpdateCallback != None):
            self.onServiceLockUpdateCallback(lockInfo, lockState)

    def onRestrictedLogLicenseStatusUpdate(self, restrictedLogLicenseInfo):
        if(self.onRestrictedLogLicenseStatusUpdateCallback != None):
            self.onRestrictedLogLicenseStatusUpdateCallback(restrictedLogLicenseInfo)

    def onQspsMessage(self, profilerMessage):
        if(self.onQspsMessageCallback != None):
            self.onQspsMessageCallback(profilerMessage)

    def onHyperVisorDataChanged(self, protocolHandle, hyperVisorConfiguration):
        if(self.onHyperVisorDataChangedCallback != None):
            self.onHyperVisorDataChangedCallback(protocolHandle, hyperVisorConfiguration)

#endregion //CallbackFunction
