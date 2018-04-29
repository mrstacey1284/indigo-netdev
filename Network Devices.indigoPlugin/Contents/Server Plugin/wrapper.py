# provides wrapper objects for specific device types

import logging
import urllib2

import clients
import utils

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
class Service(DeviceWrapper):

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
        utils.validateConfig_Hostname('address', values, errors, emptyOk=False)
        utils.validateConfig_Int('port', values, errors, min=1, max=65536)

################################################################################
# plugin device wrapper for Ping Status devices
class Ping(DeviceWrapper):

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
        utils.validateConfig_Hostname('address', values, errors, emptyOk=False)

################################################################################
# plugin device wrapper for HTTP Status devices
class HTTP(DeviceWrapper):

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
        utils.validateConfig_URL('url', values, errors, emptyOk=False)

        # update 'address' for proper display
        url = values['url']
        req = urllib2.Request(url)

        values['address'] = req.get_host()

################################################################################
# plugin device wrapper for Local Device types
class Local(DeviceWrapper):

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
        utils.validateConfig_MAC('address', values, errors, emptyOk=False)

################################################################################
# plugin device wrapper for SSH Device types
class SSH(RelayDeviceWrapper):

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
        utils.validateConfig_Hostname('address', values, errors, emptyOk=False)
        utils.validateConfig_Int('port', values, errors, min=1, max=65536)

        utils.validateConfig_String('username', values, errors, emptyOk=False)
        #utils.validateConfig_String('password', values, errors, emptyOk=True)

        utils.validateConfig_String('cmd_status', values, errors, emptyOk=False)
        utils.validateConfig_String('cmd_shutdown', values, errors, emptyOk=False)

    #---------------------------------------------------------------------------
    def turnOff(self):
        device = self.device
        self.logger.info(u'Shutting down %s', device.name)

        if not self.client.turnOff():
            self.logger.error(u'Could not turn off remote server: %s', device.name)

################################################################################
# plugin device wrapper for macOS Device types
class macOS(RelayDeviceWrapper):

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
        utils.validateConfig_Hostname('address', values, errors, emptyOk=False)
        utils.validateConfig_String('username', values, errors, emptyOk=False)
        #utils.validateConfig_String('password', values, errors, emptyOk=True)
