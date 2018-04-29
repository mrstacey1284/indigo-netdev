## Indigo plugin for monitoring network devices

import logging
import socket
import urllib2
import subprocess

import clients

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

    wrappers = dict()
    arp_cache = None

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self._loadPluginPrefs(pluginPrefs)

    #---------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    #---------------------------------------------------------------------------
    def refreshAllDevices(self):
        # update all enabled and configured devices
        for id in self.wrappers:
            wrapper = self.wrappers[id]
            wrapper.updateStatus()

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        # TODO limit concurrent calls to arp - abort if already running

        cmd = ['/usr/sbin/arp', '-a']

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        cache = [ ]

        # translate command output to cache entries
        for line in pout.splitlines():
            parts = line.split()
            entry = {
                'hostname': None,
                'ip_addr': parts[0],
                'eth_addr': parts[3].upper(),
                'iface': parts[5]
            }

            cache.append(entry)
            self.logger.debug('ARP: ' + str(entry))

        self.arp_cache = cache

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
            DeviceWrapper_Service.validateConfig(values, errors)
        elif typeId == 'ping':
            DeviceWrapper_Ping.validateConfig(values, errors)
        elif typeId == 'http':
            DeviceWrapper_HTTP.validateConfig(values, errors)
        elif typeId == 'local':
            DeviceWrapper_Local.validateConfig(values, errors)
        elif typeId == 'ssh':
            DeviceWrapper_SSH.validateConfig(values, errors)
        elif typeId == 'macos':
            DeviceWrapper_macOS.validateConfig(values, errors)

        return ((len(errors) == 0), values, errors)

    #---------------------------------------------------------------------------
    def closedPrefsConfigUi(self, values, canceled):
        if canceled: return
        self._loadPluginPrefs(values)

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        typeId = device.deviceTypeId

        self.logger.debug(u'Starting device - %s [%s]', device.name, typeId)

        wrapper = None

        if typeId == 'service':
            wrapper = DeviceWrapper_Service(device)
        elif typeId == 'ping':
            wrapper = DeviceWrapper_Ping(device)
        elif typeId == 'http':
            wrapper = DeviceWrapper_HTTP(device)
        elif typeId == 'local':
            wrapper = DeviceWrapper_Local(device)
        elif typeId == 'ssh':
            wrapper = DeviceWrapper_SSH(device)
        elif typeId == 'macos':
            wrapper = DeviceWrapper_macOS(device)
        else:
            self.logger.error(u'unknown device type: %s', typeId)

        self.wrappers[device.id] = wrapper

        # XXX we might want to make sure the device status is updated here...
        # the problem with that is it makes for a long plugin startup if all
        # devices update status - especially things like ping and http.
        # !! when status is updated here, start the thread loop with a sleep !!
        #if device.configured: wrapper.updateStatus()

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
            self.refreshInterval = 60
        else:
            self.refreshInterval = int(refreshVal)
        self.logger.debug(u'{refreshInterval} - %d seconds', self.refreshInterval)

    #---------------------------------------------------------------------------
    def _runLoopStep(self):
        #TODO self.rebuildArpCache()
        self.refreshAllDevices()

        # sleep for the configured timeout
        self.sleep(self.refreshInterval)

    #---------------------------------------------------------------------------
    # Relay / Dimmer Action callback
    def actionControlDimmerRelay(self, action, device):
        act = action.deviceAction
        self.logger.debug(u'actionControlDimmerRelay[%s] - %s', act, device.name)

        wrapper = self.wrappers[device.id]

        #### TURN ON ####
        if act == indigo.kDimmerRelayAction.TurnOn:
            wrapper.turnOn()

        #### TURN OFF ####
        elif act == indigo.kDimmerRelayAction.TurnOff:
            wrapper.turnOff()

        #### TOGGLE ####
        elif act == indigo.kDimmerRelayAction.Toggle:
            if device.onState:
                wrapper.turnOff()
            else:
                wrapper.turnOn()

    #---------------------------------------------------------------------------
    # General Action callback
    def actionControlGeneral(self, action, device):
        act = action.deviceAction
        self.logger.debug(u'actionControlGeneral[%s] - %s', act, device.name)

        wrapper = self.wrappers[device.id]

        #### STATUS REQUEST ####
        if act == indigo.kDeviceGeneralAction.RequestStatus:
            wrapper.updateStatus()

        #### BEEP ####
        elif act == indigo.kDeviceGeneralAction.Beep:
            pass

################################################################################
# wrapper base class for device types
class DeviceWrapper():

    #---------------------------------------------------------------------------
    def __init__(self, device):
        raise NotImplementedError()

    #---------------------------------------------------------------------------
    # sub-classes should override this for their specific device states
    def updateStatus(self):
        device = self.device

        if self.client.isAvailable():
            self.logger.debug(u'%s is AVAILABLE', device.name)
            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')

        else:
            self.logger.debug(u'%s is UNAVAILABLE', device.name)
            device.updateStateOnServer('active', False)
            device.updateStateOnServer('status', 'Inactive')

################################################################################
# base wrapper class for relay-type devices
class RelayDeviceWrapper(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        raise NotImplementedError()

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
        device = self.device

        if self.client.isAvailable():
            self.logger.debug(u'%s is AVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'on')
        else:
            self.logger.debug(u'%s is UNAVAILABLE', device.name)
            device.updateStateOnServer('onOffState', 'off')

################################################################################
# plugin device wrapper for Network Service devices
class DeviceWrapper_Service(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.DeviceWrapper_Service')

        address = device.pluginProps['address']
        port = int(device.pluginProps['port'])
        client = clients.ServiceClient(address, port)

        self.device = device
        self.client = client

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        validateConfig_String('address', values, errors, emptyOk=False)
        validateConfig_Int('port', values, errors, min=1, max=65536)

################################################################################
# plugin device wrapper for Ping Status devices
class DeviceWrapper_Ping(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.DeviceWrapper_Ping')

        address = device.pluginProps['address']

        self.device = device
        self.client = clients.PingClient(address)

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        validateConfig_String('address', values, errors, emptyOk=False)

################################################################################
# plugin device wrapper for HTTP Status devices
class DeviceWrapper_HTTP(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.DeviceWrapper_HTTP')

        url = device.pluginProps['url']

        self.device = device
        self.client = clients.HttpClient(url)

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        validateConfig_String('url', values, errors, emptyOk=False)

        # update 'address' for proper display
        url = values['url']
        req = urllib2.Request(url)

        values['address'] = req.get_host()

################################################################################
# plugin device wrapper for Local Device types
class DeviceWrapper_Local(DeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.DeviceWrapper_Local')

        address = device.pluginProps['address']

        self.device = device
        self.client = clients.NullClient()

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        validateConfig_String('address', values, errors, emptyOk=False)

################################################################################
# plugin device wrapper for SSH Device types
class DeviceWrapper_SSH(RelayDeviceWrapper):

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.DeviceWrapper_SSH')

        address = device.pluginProps['address']
        port = int(device.pluginProps['port'])
        uname = device.pluginProps['username']
        client = clients.SSHClient(address, port=port, username=uname)

        client.commands['status'] = device.pluginProps['cmd_status']
        client.commands['shutdown'] = device.pluginProps['cmd_shutdown']

        self.client = client
        self.device = device

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        DeviceWrapper_Service.validateConfig(values, errors)
        validateConfig_String('cmd_status', values, errors, emptyOk=False)
        validateConfig_String('cmd_shutdown', values, errors, emptyOk=False)

    #---------------------------------------------------------------------------
    def turnOff(self):
        device = self.device
        self.logger.info(u'Shutting down %s', device.name)

        if not self.client.turnOff():
            self.logger.error(u'Could not turn off remote server: %s', device.name)

################################################################################
# plugin device wrapper for macOS Device types
class DeviceWrapper_macOS(RelayDeviceWrapper):

    # XXX could we use remote management instead of SSH?

    #---------------------------------------------------------------------------
    def __init__(self, device):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.DeviceWrapper_macOS')

        address = device.pluginProps['address']
        uname = device.pluginProps.get('username', None)
        passwd = device.pluginProps.get('password', None)
        client = clients.SSHClient(address, username=uname, password=passwd)

        # macOS commands are known and cannot be changed by the user
        client.commands['status'] = '/usr/bin/true'
        client.commands['shutdown'] = '/sbin/shutdown -h now'

        self.client = client
        self.device = device

    #---------------------------------------------------------------------------
    @staticmethod
    def validateConfig(values, errors):
        validateConfig_String('address', values, errors, emptyOk=False)

