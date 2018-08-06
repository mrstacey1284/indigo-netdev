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
    timeout = 0

    #---------------------------------------------------------------------------
    def __init__(self, timeout=5):
        self.logger = logging.getLogger('Plugin.arp.ArpCache')
        self.timeout = timeout

        self.cmdLock = threading.Lock()
        self.cacheLock = threading.RLock()

    #---------------------------------------------------------------------------
    def _normalizeAddress(self, address):
        addr = address.upper()
        octets = addr.split(':')
        newOctets = []
        for block in octets:
            if len(block) < 2:
                newOctets.append = '0'+block
            else:
                newOctets.append = block
        
        normAddr = ':'.join([str(x) for x in newOctets])
        # TODO make sure all octets are padded
        # TODO return None for invalid address

        return normAddr

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        self.cacheLock.acquire()

        self.updateCurrentDevices()
        self.purgeInactiveDevices()

        self.cacheLock.release()

    #---------------------------------------------------------------------------
    def _getRawArpTable(self):
        # the command takes some time to run so we will bail if
        # another thread is already executing the arp command
        if not self.cmdLock.acquire(False):
            self.logger.warn('/usr/sbin/arp: already in use')
            return None

        cmd = ['/usr/sbin/arp', '-a']
        self.logger.debug('exec: %s', cmd)

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            pout, perr = proc.communicate()
        except:
            pout = None

        self.cmdLock.release()

        return pout

    #---------------------------------------------------------------------------
    def updateCurrentDevices(self):
        rawOutput = self._getRawArpTable()

        self.cacheLock.acquire()

        # translate command output to cache entries
        for line in rawOutput.splitlines():
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
        diff = (now - last) / 60

        self.logger.debug('device %s last activity was %d min ago', address, diff)

        return (diff < self.timeout)

