#! /usr/bin/env python

import time
import subprocess
import socket
import telnetlib

# NOTE most of the pending improvements here are in building the ARP cache
# could add some additional status checks on active devices, e.g. ping

################################################################################
class Plugin(indigo.PluginBase):

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.debug = pluginPrefs.get('debug', False)

        # configure router connection settings
        routerAddr = str(pluginPrefs.get('routerAddr'))
        routerUser = str(pluginPrefs.get('routerUser', None))
        #TODO routerPasswd = pluginPrefs.get('routerPasswd')
        routerArpTable = str(pluginPrefs.get('routerArpTable'))

        conn = (routerUser + '@' if routerUser else '') + routerAddr
        self.arpTableCmd = ['/usr/bin/ssh', conn, routerArpTable]
        self.debugLog('get arp: ' + str(self.arpTableCmd))

        self.retryCount = int(pluginPrefs.get('retryCount', 5))
        self.retryInterval = int(pluginPrefs.get('retryInterval', 60))

        self.debugLog('retry x' + str(self.retryCount)
                      + ' @ ' + str(self.retryInterval) + 'sec')

        connectionTimeout = int(pluginPrefs.get('connectionTimeout', 5))
        socket.setdefaulttimeout(connectionTimeout)
        self.debugLog('connection timeout: ' + str(connectionTimeout))

        self.arp_cache = None

    #---------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    #---------------------------------------------------------------------------
    def validatePrefsConfigUi(self, values):
        valid = True
        errors = indigo.Dict()

        try:
            int(values['retryInterval'])
        except:
            valid = False
            errors['retryInterval'] = u"Retry interval must be an integer"

        try:
            int(values['retryCount'])
        except:
            valid = False
            errors['retryCount'] = u"Retry count must be an integer"

        try:
            int(values['connectionTimeout'])
        except:
            valid = False
            errors['connectionTimeout'] = u"Connection timeout must be an integer"

        return (valid, values, errors)

    #---------------------------------------------------------------------------
    def startup(self):
        self.debugLog('Plugin startup')
        self.rebuildArpCache()

    #---------------------------------------------------------------------------
    def shutdown(self):
        self.debugLog('Plugin shutdown')

    #---------------------------------------------------------------------------
    def didDeviceCommPropertyChange(self, origDev, newDev):
        return origDev.pluginProps['address'] != newDev.pluginProps['address']

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        self.debugLog('Starting device: ' + device.name)
        self.updateDeviceStates(device)

    #---------------------------------------------------------------------------
    def deviceStopComm(self, device):
        self.debugLog('Stopping device: ' + device.name)

        # XXX this has the side effect of firing triggers on device states
        # when the plugin is stopped...  is that the right thing to do?
        #device.updateStateOnServer('active', False)
        #device.updateStateOnServer('status', 'Disabled')

    #---------------------------------------------------------------------------
    def runConcurrentThread(self):
        self.debugLog('Thread Started')

        while True:
            # devices are updated when added, so we'll start with a sleep
            self.sleep(self.retryInterval)

            # grab the current arp table
            self.rebuildArpCache()

            # update all enabled and configured devices
            for device in indigo.devices.itervalues('self'):
                if device and device.configured and device.enabled:
                    self.updateDeviceStates(device)

            # sleep until the next check
            self.debugLog('Thread Sleep: ' + str(self.retryInterval))

        self.debugLog('Thread Stopped')

    #---------------------------------------------------------------------------
    def updateDeviceStates(self, device):
        self.debugLog('Update Device: ' + device.name)

        type = device.deviceTypeId
        props = device.pluginProps

        if type == 'mac_addr':
            self.updateDeviceStates_mac_addr(device)
        elif type == 'hostname':
            self.updateDeviceStates_hostname(device)
        elif type == 'telnet':
            self.updateDeviceStates_telnet(device)
        elif type == 'ssh':
            self.updateDeviceStates_ssh(device)

        # TODO support retry count
        device.replacePluginPropsOnServer(props)

    #---------------------------------------------------------------------------
    def updateDeviceStates_mac_addr(self, device):
        props = device.pluginProps
        addr = props['address']

        if self.isPresentInArpTable(addr):
            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')
            device.updateStateOnServer('lastSeenAt', time.strftime('%c'))
        else:
            device.updateStateOnServer('active', False)
            device.updateStateOnServer('status', 'Inactive')

    #---------------------------------------------------------------------------
    def updateDeviceStates_hostname(self, device):
        props = device.pluginProps
        host = props['address']
        port = int(props['port'])

        if self.hostIsReachable(host, port):
            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')
        else:
            device.updateStateOnServer('active', False)
            device.updateStateOnServer('status', 'Inactive')

    #---------------------------------------------------------------------------
    def updateDeviceStates_telnet(self, device):
        props = device.pluginProps
        host = props['address']
        port = int(props['port'])

        if self.hostIsReachable(host, port):
            device.updateStateOnServer('onOffState', 'on')
        else:
            device.updateStateOnServer('onOffState', 'off')

    #---------------------------------------------------------------------------
    def updateDeviceStates_ssh(self, device):
        props = device.pluginProps
        host = props['address']
        port = int(props['port'])

        if self.hostIsReachable(host, port):
            device.updateStateOnServer('onOffState', 'on')
        else:
            device.updateStateOnServer('onOffState', 'off')

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        # XXX the local arp table doesn't seem as reliable as the router,
        # but it would be much nicer to avoid depending on ssh
        #cmd = ['/usr/sbin/arp', '-a']

        proc = subprocess.Popen(self.arpTableCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        cache = [ ]

        # this table is dependent on the method above
        # FIXME need to trim non-arp lines (e.g. table header)
        for line in pout.splitlines():
            parts = line.split()
            entry = {
                'hostname': None,
                'ip_addr': parts[0],
                'mac_addr': parts[3].upper(),
                'iface': parts[5]
            }

            cache.append(entry)
            self.debugLog('ARP: ' + str(entry))

        self.arp_cache = cache

    #---------------------------------------------------------------------------
    # determine if the specific device is in the ARP cache
    def isPresentInArpTable(self, mac_addr):
        self.debugLog('search: ' + mac_addr)

        # bail on the first match...
        for entry in self.arp_cache:
            if entry['mac_addr'] == mac_addr:
                return True

        # default case - no match
        return False

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def hostIsReachable(self, host, port):
        self.debugLog('checking host - ' + host + ':' + str(port))

        ret = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            sock.close()
            ret = True
        except:
            ret = False

        return ret

    #---------------------------------------------------------------------------
    # try to reach the host via simple telnet connection
    def telnetLogin(self, host, port):
        self.debugLog('connecting to ' + host + ':' + str(port))

        try:
            tn = telnetlib.Telnet(host, port)
            # TODO support username & password
            return tn

        except:
            return None

    #---------------------------------------------------------------------------
    # turn a device on
    def turnOn(self, device):
        pass  # XXX can't turn things back on

    #---------------------------------------------------------------------------
    # turn a device off
    def turnOff(self, device):
        type = device.deviceTypeId

        if type == 'telnet':
            self.turnOff_telnet(device)
        elif type == 'ssh':
            self.turnOff_ssh(device)

    #---------------------------------------------------------------------------
    def turnOff_telnet(self, device):
        pass

    #---------------------------------------------------------------------------
    def turnOff_ssh(self, device):
        pass

    #---------------------------------------------------------------------------
    # Relay / Dimmer Action callback
    def actionControlDimmerRelay(self, action, device):
        ctrl = action.deviceAction
        self.debugLog('ctrl ' + device.name + ':' + str(ctrl))

        #### TURN ON ####
        if ctrl == indigo.kDimmerRelayAction.TurnOn:
            self.turnOn(device)

        #### TURN OFF ####
        elif ctrl == indigo.kDimmerRelayAction.TurnOff:
            self.turnOff(device)

        #### TOGGLE ####
        elif ctrl == indigo.kDimmerRelayAction.Toggle:
            if device.onOffState == 'on':
                self.turnOff(device)
            else:
                self.turnOn(device)

    #---------------------------------------------------------------------------
    # General Action callback
    def actionControlGeneral(self, action, device):
        cmd = action.deviceAction
        self.debugLog('cmd ' + device.name + ':' + str(cmd))

        #### STATUS REQUEST ####
        if cmd == indigo.kDeviceGeneralAction.RequestStatus:
            self.updateDeviceStates(device)

        #### BEEP ####
        elif cmd == indigo.kDeviceGeneralAction.Beep:
            pass

