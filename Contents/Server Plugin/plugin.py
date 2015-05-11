#! /usr/bin/env python

import time
import subprocess

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
        device.updateStateOnServer('active', False)
        device.updateStateOnServer('status', 'Disabled')

    #---------------------------------------------------------------------------
    def runConcurrentThread(self):
        self.debugLog('Thread Started')

        while True:
            # devices are updated when added, so we'll start with a sleep
            self.sleep(self.retryInterval)

            # grab the current arp table
            self.rebuildArpCache()

            # update all active and configured devices
            for device in indigo.devices.itervalues('self'):
                if device and device.configured and device.enabled:
                    self.updateDeviceStates(device)

            # sleep until the next check
            self.debugLog('Thread Sleep: ' + str(self.retryInterval))

        self.debugLog('Thread Stopped')

    #---------------------------------------------------------------------------
    def updateDeviceStates(self, device):
        self.debugLog('Update Device: ' + device.name)
        props = device.pluginProps

        # the device is in the current arp cache
        if any(entry['eth_addr'] == device.address for entry in self.arp_cache):
            self.debugLog('  - Device is ACTIVE')

            device.updateStateOnServer('active', True)
            device.updateStateOnServer('status', 'Active')
            device.updateStateOnServer('lastSeenAt', time.strftime('%c'))

            props['retry'] = self.retryCount

        # the device isn't there, but we have retries remaining...
        elif props.get('retry', 0) > 0:
            self.debugLog('  - Retry Device: ' + str(props['retry']))

            props['retry'] -= 1

        # the device isn't there and we are out of retries
        else:
            self.debugLog('  - Device is NOT Active')

            device.updateStateOnServer('active', False)
            device.updateStateOnServer('status', 'Inactive')

            props['retry'] = 0

        device.replacePluginPropsOnServer(props)

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        # XXX the local arp table doesn't seem as reliable as the router,
        # but it would be much nicer to avoid depending on ssh
        #cmd = ['/usr/sbin/arp', '-a']

        proc = subprocess.Popen(self.arpTableCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        cache = [ ]

        # this table is dependent on the mthod above
        # FIXME need to trim non-arp lines (e.g. table header)
        for line in pout.splitlines():
            parts = line.split()
            entry = {
                'hostname': None,
                'ip_addr': parts[0],
                'eth_addr': parts[3].upper(),
                'iface': parts[5]
            }

            cache.append(entry)
            self.debugLog('ARP: ' + str(entry))

        self.arp_cache = cache

