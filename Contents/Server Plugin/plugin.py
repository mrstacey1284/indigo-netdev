#! /usr/bin/env python

import logging
import shlex
import socket
import telnetlib
import subprocess
import threading

################################################################################
def validateConfig_String(key, values, errors, emptyOk=False):
    textVal = values.get(key, None)

    if textVal is None:
        errors[key] = '%s cannot be empty' % key
        return False

    if not emptyOk and len(textVal) == 0:
        errors[key] = '%s cannot be blank' % key
        return False

    return True

################################################################################
def validateConfig_Int(key, values, errors, min=None, max=None):
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
        errors[key] = '%s must be greater than or equal to %d' % (key, min)
        return False

    if max is not None and intVal > max:
        errors[key] = '%s must be less than or equal to %d' % (key, max)
        return False

    return True

################################################################################
class Plugin(indigo.PluginBase):

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self._loadPluginPrefs(pluginPrefs)
        self.objects = dict()

    #---------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    #---------------------------------------------------------------------------
    def validatePrefsConfigUi(self, values):
        errors = indigo.Dict()

        validateConfig_Int('refreshInterval', values, errors, min=1, max=3600)
        validateConfig_Int('connectionTimeout', values, errors, min=0, max=300)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def validateDeviceConfigUi(self, values, typeId, devId):
        errors = indigo.Dict()

        if typeId == 'service':
            NetworkServiceDevice.validateConfig(values, errors)

        elif typeId == 'ssh':
            NetworkRelayDevice_SSH.validateConfig(values, errors)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def closedPrefsConfigUi(self, values, canceled):
        if canceled: return
        self._loadPluginPrefs(values)

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        typeId = device.deviceTypeId

        self.logger.debug(u'Starting device - %s [%s]', device.name, typeId)

        if typeId == 'service':
            obj = NetworkServiceDevice(device)
            self.objects[device.id] = obj

        elif typeId == 'ssh':
            obj = NetworkRelayDevice_SSH(device)
            self.objects[device.id] = obj

        elif typeId == 'telnet':
            obj = NetworkRelayDevice_Telnet(device)
            self.objects[device.id] = obj

        elif typeId == 'macos':
            obj = NetworkRelayDevice_macOS(device)
            self.objects[device.id] = obj

        else:
            self.logger.error(u'unknown device type: %s', typeId)

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
            self.refreshInterval = 60
        else:
            self.refreshInterval = int(refreshVal)
        self.logger.debug(u'{refreshInterval} - %d seconds', self.refreshInterval)

    #---------------------------------------------------------------------------
    def _runLoopStep(self):
        # update all enabled and configured devices
        for id in self.objects:
            obj = self.objects[id]
            obj.updateStatus()

        # sleep for the configured timeout
        self.sleep(self.refreshInterval)

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
        self.logger = logging.getLogger('Plugin.NetworkServiceDevice')

        self.address = device.pluginProps['address']
        self.port = int(device.pluginProps['port'])

        self.device = device
        self.execLock = threading.Lock()

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        validateConfig_String('address', values, errors, emptyOk=False)
        validateConfig_Int('port', values, errors, min=1, max=65536)

    #---------------------------------------------------------------------------
    # sub-classes should override this for their specific device states
    def updateStatus(self):
        device = self.device

        if self._hostIsReachable():
            self.logger.debug(u'%s is AVAILABLE', device.name)
            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')
        else:
            self.logger.debug(u'%s is UNAVAILABLE', device.name)
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

    #---------------------------------------------------------------------------
    # defined here as a convenience to subclasses
    def _exec(self, *cmd):
        self.execLock.acquire()
        self.logger.debug(u'=> exec%s', cmd)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()
        self.logger.debug(u'=> exit(%d)', proc.returncode)

        # TODO check perr
        #self.logger.warn(perr)

        self.execLock.release()
        return (proc.returncode == 0)

################################################################################
# a network service that supports on / off state (relay device)
class NetworkRelayDevice(NetworkServiceDevice):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        NetworkServiceDevice.__init__(self, device)
        self.logger = logging.getLogger('Plugin.NetworkRelayDevice')

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        NetworkServiceDevice.validateConfig(values, errors)
        validateConfig_String('cmd_status', values, errors, emptyOk=False)
        validateConfig_String('cmd_shutdown', values, errors, emptyOk=False)

    #---------------------------------------------------------------------------
    # default behavior; subclasses should provide correct implementation
    def turnOff(self):
        self.logger.warn(u'Not supported - Turn Off %s', self.device.name)

    #---------------------------------------------------------------------------
    # default behavior; subclasses should provide correct implementation
    def turnOn(self):
        self.logger.warn(u'Not supported - Turn On %s', self.device.name)

    #---------------------------------------------------------------------------
    # basic check to see if the server is responding
    def updateStatus(self):
        status = self._hostIsReachable()
        self._setDeviceStatus(status)

    #---------------------------------------------------------------------------
    def _setDeviceStatus(self, deviceIsAvailable):
        device = self.device

        if deviceIsAvailable:
            self.logger.debug(u'%s is AVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'on')
        else:
            self.logger.debug(u'%s is UNAVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'off')

################################################################################
class NetworkRelayDevice_SSH(NetworkRelayDevice):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        NetworkRelayDevice.__init__(self, device)
        self.logger = logging.getLogger('Plugin.NetworkRelayDevice_SSH')

    #---------------------------------------------------------------------------
    def updateStatus(self):
        device = self.device

        statusCmd = device.pluginProps['cmd_status']
        self.logger.debug(u'checking remote status: %s', statusCmd)

        # execute the command and update status
        cmd = shlex.split(statusCmd)
        status = self._rexec(*cmd)
        self._setDeviceStatus(status)

    #---------------------------------------------------------------------------
    def turnOff(self):
        device = self.device

        shutdownCmd = device.pluginProps['cmd_shutdown']
        self.logger.info(u'Shutting down %s', device.name)
        self.logger.debug(u'=> %s', shutdownCmd)

        # execute the command remotely
        cmd = shlex.split(shutdownCmd)
        status = self._rexec(*cmd)

        if status is False:
            self.logger.error(u'Could not turn off remote server: %s', device.name)

    #---------------------------------------------------------------------------
    def _rexec(self, *cmd):
        device = self.device

        # setup the remote command using a safe ssh config
        # XXX -f would be ideal, but we lose the return code of the remote command
        rcmd = ['ssh', '-anTxq']

        # TODO support global timeout, e.g.
        #rcmd.append('-o', 'ConnectTimeout=%d' % connectionTimeout)

        # username is optional for SSH commands...
        username = device.pluginProps.get('username', None)
        if username is not None and len(username) > 0:
            self.logger.debug(u'running as remote user: %s', username)
            rcmd.extend(('-l', username))
        else:
            # TODO capture local username in debug log
            self.logger.debug(u'running as local user')

        # add the host and port
        rcmd.extend(('-p', device.pluginProps['port']))
        rcmd.append(device.pluginProps['address'])

        # add all commands supplied by caller
        rcmd.extend(cmd)

        return self._exec(*rcmd)

################################################################################
class NetworkRelayDevice_Telnet(NetworkRelayDevice):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        NetworkRelayDevice.__init__(self, device)
        self.logger = logging.getLogger('Plugin.NetworkRelayDevice_Telnet')

################################################################################
class NetworkRelayDevice_macOS(NetworkRelayDevice_SSH):

    # XXX could we use remote management instead of SSH?

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # configure known properties for mac servers - FIXME doesn't work
        device.pluginProps['port'] = '22'
        device.pluginProps['cmd_status'] = '/usr/bin/true'
        device.pluginProps['cmd_shutdown'] = '/sbin/shutdown -h now'

        # TODO how to handle password authentication?

        NetworkRelayDevice_SSH.__init__(self, device)
        self.logger = logging.getLogger('Plugin.NetworkRelayDevice_macOS')

