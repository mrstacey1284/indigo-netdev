# for managing a local arp cache

import time
import logging
import subprocess
import threading

# TODO add some unit tests for parsing arp command output
# TODO support a user-defined timeout for entries

################################################################################
class ArpCache():

    lock = None
    cache = dict()

    #---------------------------------------------------------------------------
    def __init__(self, timeout=300):
        self.logger = logging.getLogger('Plugin.arp.ArpCache')
        self.timeout = timeout
        self.lock = threading.RLock()

    #---------------------------------------------------------------------------
    def _normalizeAddress(self, address):
        addr = address.upper()

        # TODO make sure all octets are padded
        # TODO return None for invalid address

        return addr

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        self.lock.acquire()

        self.updateCurrentDevices()
        self.purgeInactiveDevices()

        self.lock.release()

    #---------------------------------------------------------------------------
    def updateCurrentDevices(self):
        # TODO limit concurrent calls to arp - abort if already running

        cmd = ['/usr/sbin/arp', '-a']

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        self.lock.acquire()

        # translate command output to cache entries
        for line in pout.splitlines():
            parts = line.split()

            addr = self._normalizeAddress(parts[3])
            if addr is None: continue

            self.cache[addr] = time.time()
            self.logger.debug('device found: %s', addr)

        self.lock.release()

    #---------------------------------------------------------------------------
    def purgeInactiveDevices(self):
        toBePurged = list()

        self.lock.acquire()

        # first, find all the expired keys
        for addr in self.cache.keys():
            if not self.isActive(addr):
                self.logger.debug('device expired: %s; marked for removal', addr)
                toBePurged.append(addr)

        # now, delete the expired addresses
        for addr in toBePurged: del self.cache[addr]

        self.lock.release()

    #---------------------------------------------------------------------------
    def isActive(self, address):
        addr = self._normalizeAddress(address)

        last = self.cache.get(addr)
        if last is None: return False

        now = time.time()
        diff = now - last

        self.logger.debug('device %s last activity was %d sec ago', address, diff)

        return (diff < self.timeout)

