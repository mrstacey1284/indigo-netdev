# for managing a local arp cache

import time
import logging
import subprocess
import threading

# TODO add some unit tests for parsing arp command output

################################################################################
class ArpCache():

    cmdLock = None
    cacheLock = None

    cache = dict()

    #---------------------------------------------------------------------------
    def __init__(self, timeout=300):
        self.logger = logging.getLogger('Plugin.arp.ArpCache')
        self.timeout = timeout

        self.cmdLock = threading.Lock()
        self.cacheLock = threading.RLock()

    #---------------------------------------------------------------------------
    def _normalizeAddress(self, address):
        addr = address.upper()

        # TODO make sure all octets are padded
        # TODO return None for invalid address

        return addr

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        self.cacheLock.acquire()

        self.updateCurrentDevices()
        self.purgeInactiveDevices()

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def updateCurrentDevices(self):
        # this command takes some time to run so we will bail if
        # another thread is already executing the arp command
        if not self.cmdLock.acquire(False):
            self.logger.warn('/usr/sbin/arp: already in use')
            return

        cmd = ['/usr/sbin/arp', '-a']

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        self.cmdLock.release()

        self.cacheLock.acquire()

        # translate command output to cache entries
        for line in pout.splitlines():
            parts = line.split()

            addr = self._normalizeAddress(parts[3])
            if addr is None: continue

            self.cache[addr] = time.time()
            self.logger.debug('device found: %s', addr)

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def purgeInactiveDevices(self):
        toBePurged = list()

        self.cacheLock.acquire()

        # first, find all the expired keys
        for addr in self.cache.keys():
            if not self.isActive(addr):
                self.logger.debug('device expired: %s; marked for removal', addr)
                toBePurged.append(addr)

        # now, delete the expired addresses
        for addr in toBePurged: del self.cache[addr]

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def isActive(self, address):
        addr = self._normalizeAddress(address)

        last = self.cache.get(addr)
        if last is None: return False

        now = time.time()
        diff = now - last

        self.logger.debug('device %s last activity was %d sec ago', address, diff)

        return (diff < self.timeout)

