#! /usr/bin/env python

import logging
import socket
import telnetlib

################################################################################
class Plugin(indigo.PluginBase):

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self._initializeLogging(pluginPrefs)

        self.objects = dict()

    #---------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    #---------------------------------------------------------------------------
    def validatePrefsConfigUi(self, values):
        errors = indigo.Dict()

        self._validatePrefs_Int('refreshInterval', values, errors, min=1, max=3600)
        self._validatePrefs_Int('connectionTimeout', values, errors, min=0, max=300)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def closedPrefsConfigUi(self, values, canceled):
        if canceled: return

        self._initializeLogging(values)

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        typeId = device.deviceTypeId

        self.logger.debug(u'Starting device - %s [%s]', device.name, typeId)

        if typeId == 'service':
            obj = NetworkServiceDevice(device)
            self.objects[device.id] = obj

        elif typeId == 'ssh':
            obj = ServerDevice_SSH(device)
            self.objects[device.id] = obj

        elif typeId == 'telnet':
            obj = ServerDevice_Telnet(device)
            self.objects[device.id] = obj

        else:
            self.logger.error('unknown device type: %s', typeId)

    #---------------------------------------------------------------------------
    def deviceStopComm(self, device):
        self.logger.debug(u'Stopping device: %s', device.name)

        self.objects.pop(device.id, None)

    #---------------------------------------------------------------------------
    def runConcurrentThread(self):
        self.logger.debug(u'Thread Started')

        try:

            while not self.stopThread:
                self._runLoopStep()

        except self.StopThread:
            pass

        self.logger.debug(u'Thread Stopped')

    #---------------------------------------------------------------------------
    def _initializeLogging(self, values):
        levelTxt = values.get('logLevel', None)

        if levelTxt is None:
            self.logLevel = 20
        else:
            self.logLevel = int(levelTxt)

        self.indigo_log_handler.setLevel(self.logLevel)

    #---------------------------------------------------------------------------
    def _validatePrefs_Int(self, key, values, errors, min=None, max=None):
        textVal = values.get(key, None)
        if textVal is None:
            errors[key] = '%s is required' % key
            return False

        intVal = None

        try:
            intVal = int(textVal)
        except:
            errors[key] = '%s must be an integer' % key
            return False

        if min is not None and intVal < min:
            errors[key] = '%s must be greater than %d' % (key, min)
            return False

        if max is not None and intVal > max:
            errors[key] = '%s must be less than %d' % (key, max)
            return False

        return True

    #---------------------------------------------------------------------------
    def _runLoopStep(self):
        # devices are updated when comms start, so we'll start with a sleep
        refreshInterval = int(self.pluginPrefs.get('refreshInterval', 60))
        self.logger.debug(u'Next update in %d seconds', refreshInterval)
        self.sleep(refreshInterval)

        # update all enabled and configured devices
        for id in self.objects:
            obj = self.objects[id]
            obj.updateStatus()

    #---------------------------------------------------------------------------
    # Relay / Dimmer Action callback
    def actionControlDimmerRelay(self, action, device):
        act = action.deviceAction
        self.logger.debug(u'actionControlDimmerRelay[%s] - %s', act, device.name)

        obj = self.objects[device.id]

        #### TURN ON ####
        if act == indigo.kDimmerRelayAction.TurnOn:
            obj.turnOn()

        #### TURN OFF ####
        elif act == indigo.kDimmerRelayAction.TurnOff:
            obj.turnOff()

        #### TOGGLE ####
        elif act == indigo.kDimmerRelayAction.Toggle:
            if device.onState:
                obj.turnOff()
            else:
                obj.turnOn()

    #---------------------------------------------------------------------------
    # General Action callback
    def actionControlGeneral(self, action, device):
        act = action.deviceAction
        self.logger.debug(u'actionControlGeneral[%s] - %s', act, device.name)

        obj = self.objects[device.id]

        #### STATUS REQUEST ####
        if act == indigo.kDeviceGeneralAction.RequestStatus:
            obj.updateStatus()

        #### BEEP ####
        elif act == indigo.kDeviceGeneralAction.Beep:
            pass

################################################################################
# a generic service running on a specific port
class NetworkServiceDevice():

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger(u'Plugin.NetworkServiceDevice')

        self.address = device.pluginProps['address']
        self.port = int(device.pluginProps['port'])

        self.device = device
        self.updateStatus()

    #---------------------------------------------------------------------------
    # sub-classes should override this for their specific device states
    def updateStatus(self):
        device = self.device

        if self._hostIsReachable():
            self.logger.debug('%s is AVAILABLE', device.name)

            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')

        else:
            self.logger.debug('%s is UNAVAILABLE', device.name)

            device.updateStateOnServer('active', False)
            device.updateStateOnServer('status', 'Inactive')

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def _hostIsReachable(self):
        self.logger.debug('checking host - %s:%d', self.address, self.port)

        ret = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.address, self.port))
            sock.close()
            ret = True
        except:
            ret = False

        return ret

################################################################################
# a network service that supports on / off state (relay device)
class ServerDevice(NetworkServiceDevice):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        NetworkServiceDevice.__init__(self, device)
        self.logger = logging.getLogger(u'Plugin.ServerDevice')

    #---------------------------------------------------------------------------
    # default behavior; subclasses should provide correct implementation
    def turnOff(self):
        self.logger.warn('Cannot turn off device: %s', self.device.name)

    #---------------------------------------------------------------------------
    # default behavior; subclasses should provide correct implementation
    def turnOn(self):
        self.logger.warn('Cannot turn on device: %s', self.device.name)

    #---------------------------------------------------------------------------
    # basic check to see if the server is responding
    def updateStatus(self):
        device = self.device

        if self._hostIsReachable():
            self.logger.debug('%s is AVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'on')

        else:
            self.logger.debug('%s is UNAVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'off')

################################################################################
class ServerDevice_SSH(ServerDevice):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        ServerDevice.__init__(self, device)
        self.logger = logging.getLogger(u'Plugin.ServerDevice_SSH')

################################################################################
class ServerDevice_Telnet(ServerDevice):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        ServerDevice.__init__(self, device)
        self.logger = logging.getLogger(u'Plugin.ServerDevice_Telnet')

