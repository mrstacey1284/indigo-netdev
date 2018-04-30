## Indigo plugin for monitoring network devices

import logging
import socket

import arp
import wrapper
import clients
import utils

################################################################################
class Plugin(indigo.PluginBase):

    wrappers = dict()
    arp_cache = None

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self._loadPluginPrefs(pluginPrefs)

        self.arp_cache = arp.ArpCache()

    #---------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    #---------------------------------------------------------------------------
    def refreshAllDevices(self):
        # update all enabled and configured devices
        for id in self.wrappers:
            wrap = self.wrappers[id]
            wrap.updateStatus()

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        self.arp_cache.rebuildArpCache()

    #---------------------------------------------------------------------------
    def validatePrefsConfigUi(self, values):
        errors = indigo.Dict()

        utils.validateConfig_Int('refreshInterval', values, errors, min=60, max=3600)
        utils.validateConfig_Int('connectionTimeout', values, errors, min=0, max=300)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def validateDeviceConfigUi(self, values, typeId, devId):
        errors = indigo.Dict()

        if typeId == 'service':
            wrapper.Service.validateConfig(values, errors)
        elif typeId == 'ping':
            wrapper.Ping.validateConfig(values, errors)
        elif typeId == 'http':
            wrapper.HTTP.validateConfig(values, errors)
        elif typeId == 'local':
            wrapper.Local.validateConfig(values, errors)
        elif typeId == 'ssh':
            wrapper.SSH.validateConfig(values, errors)
        elif typeId == 'macos':
            wrapper.macOS.validateConfig(values, errors)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def closedPrefsConfigUi(self, values, canceled):
        if canceled: return
        self._loadPluginPrefs(values)

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        typeId = device.deviceTypeId

        self.logger.debug(u'Starting device - %s [%s]', device.name, typeId)

        wrap = None

        if typeId == 'service':
            wrap = wrapper.Service(device)
        elif typeId == 'ping':
            wrap = wrapper.Ping(device)
        elif typeId == 'http':
            wrap = wrapper.HTTP(device)
        elif typeId == 'local':
            wrap = wrapper.Local(device, self.arp_cache)
        elif typeId == 'ssh':
            wrap = wrapper.SSH(device)
        elif typeId == 'macos':
            wrap = wrapper.macOS(device)
        else:
            self.logger.error(u'unknown device type: %s', typeId)

        self.wrappers[device.id] = wrap

        # XXX we might want to make sure the device status is updated here...
        # the problem with that is it makes for a long plugin startup if all
        # devices update status - especially things like ping and http.
        # !! when status is updated here, start the thread loop with a sleep !!
        #if device.configured: wrap.updateStatus()

    #---------------------------------------------------------------------------
    def deviceStopComm(self, device):
        self.logger.debug(u'Stopping device: %s', device.name)

        self.wrappers.pop(device.id, None)

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
    def _loadPluginPrefs(self, values):
        # setup logging system
        logLevel = values.get('logLevel', None)
        if logLevel is None:
            self.logLevel = 20
        else:
            self.logLevel = int(logLevel)
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u'{logLevel} - %s', self.logLevel)

        # global socket connection timeout - XXX does this affect all modules?
        timeoutVal = values.get('connectionTimeout', None)
        if timeoutVal is None:
            socket.setdefaulttimeout(5)
        else:
            socket.setdefaulttimeout(int(timeoutVal))
        self.logger.debug(u'{connectionTimeout} - %d sec', socket.getdefaulttimeout())

        # read refresh interval
        refreshVal = values.get('refreshInterval', None)
        if refreshVal is None:
            self.refreshInterval = 180
        else:
            self.refreshInterval = int(refreshVal)
        self.logger.debug(u'{refreshInterval} - %d seconds', self.refreshInterval)

    #---------------------------------------------------------------------------
    def _runLoopStep(self):
        self.rebuildArpCache()
        self.refreshAllDevices()

        # sleep for the configured timeout
        self.sleep(self.refreshInterval)

    #---------------------------------------------------------------------------
    # Relay / Dimmer Action callback
    def actionControlDimmerRelay(self, action, device):
        act = action.deviceAction
        self.logger.debug(u'actionControlDimmerRelay[%s] - %s', act, device.name)

        wrap = self.wrappers[device.id]

        #### TURN ON ####
        if act == indigo.kDimmerRelayAction.TurnOn:
            wrap.turnOn()

        #### TURN OFF ####
        elif act == indigo.kDimmerRelayAction.TurnOff:
            wrap.turnOff()

        #### TOGGLE ####
        elif act == indigo.kDimmerRelayAction.Toggle:
            if device.onState:
                wrap.turnOff()
            else:
                wrap.turnOn()

    #---------------------------------------------------------------------------
    # General Action callback
    def actionControlGeneral(self, action, device):
        act = action.deviceAction
        self.logger.debug(u'actionControlGeneral[%s] - %s', act, device.name)

        wrap = self.wrappers[device.id]

        #### STATUS REQUEST ####
        if act == indigo.kDeviceGeneralAction.RequestStatus:
            wrap.updateStatus()

        #### BEEP ####
        elif act == indigo.kDeviceGeneralAction.Beep:
            pass

