#! /usr/bin/env python

import re, subprocess

################################################################################
class Plugin(indigo.PluginBase):

    #---------------------------------------------------------------------------
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.debug = pluginPrefs.get('debug', False)
        self.devices = [ ]
        self.arp_table = None

    #---------------------------------------------------------------------------
    def __del__(self):
        indigo.PluginBase.__del__(self)

    #---------------------------------------------------------------------------
    def startup(self):
        self.debugLog('Plugin starting')

    #---------------------------------------------------------------------------
    def shutdown(self):
        self.debugLog('Plugin stopping')

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        self.debugLog('Starting device: ' + device.name)

        if device.id not in self.devices:
            self.devices.append(device.id)

    #---------------------------------------------------------------------------
    def deviceStopComm(self, device):
        self.debugLog('Stopping device: ' + device.name)

        if device.id in self.devices:
            self.devices.remove(device.id)

    #---------------------------------------------------------------------------
    def runConcurrentThread(self):
        self.debugLog('Thread Started')

        try:

            while True:
                # grab the current arp table
                self.arp_table = self.findDevices()
                self.debugLog('ARP table: ' + str(self.arp_table))

                for id in self.devices:
                    self.update(indigo.devices[id])

                # TODO make the interval configurable
                self.sleep(60)

        except: pass

        self.debugLog('Thread Stopped')

    #---------------------------------------------------------------------------
    def update(self, device):
        if device.address in self.arp_table:
            self.debugLog('Device Found: ' + device.name)
            device.updateStateOnServer('present', True)
            device.updateStateOnServer('status', 'present')
        else:
            self.debugLog('Device NOT Found: ' + device.name)
            device.updateStateOnServer('present', False)
            device.updateStateOnServer('status', 'away')

    #---------------------------------------------------------------------------
    def findDevices(self):
        # XXX make these plugin config params
        router_user = 'root'
        router_addr = '10.0.0.1'
        router_passwd = None

        cmd = ['/usr/bin/ssh', router_user + '@' + router_addr, 'cat /proc/net/arp']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        arp_data = proc.communicate()[0]

        # XXX could use better error handling here...
        return [line.split()[3].upper() for line in arp_data.splitlines()]

