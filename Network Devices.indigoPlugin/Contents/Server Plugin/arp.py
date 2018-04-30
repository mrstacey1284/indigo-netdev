# for managing a local arp cache

import logging
import subprocess
import threading

# TODO add some unit tests for parsing arp command output
# TODO add "expiration" or "last seen" timestamps to entries

################################################################################
class ArpCache():

    lock = None
    cache = dict()

    #---------------------------------------------------------------------------
    def __init__(self):
        self.logger = logging.getLogger('Plugin.arp.ArpCache')
        self.lock = threading.Lock()

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
                'ip_addr': parts[0],
                'eth_addr': parts[3].upper(),
                'iface': parts[5]
            }

            cache.append(entry)
            self.logger.debug('ARP: ' + str(entry))

        self.cache = cache

    #---------------------------------------------------------------------------
    def getEntryByHardwareAddr(self, address):
        addr = address.upper()

        for entry in self.cache:
            if entry['eth_addr'] == addr:
                return entry

        return None

    #---------------------------------------------------------------------------
    def isActiveHardwareAddr(self, address):
        found = self.getEntryByHardwareAddr(address)
        return (found is not None)

