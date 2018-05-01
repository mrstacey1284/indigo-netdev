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
        self.lock = threading.Lock()
        self.timeout = timeout

    #---------------------------------------------------------------------------
    def rebuildArpCache(self):
        # XXX it would be nice to lock these in a mutex...
        self.updateCurrentDevices()
        self.expireOldDevices()

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
            addr = parts[3].upper()

            # TODO look for valid addresses only

            self.cache[addr] = time.clock()
            self.logger.debug('device found: %s', addr)

        self.lock.release()

    #---------------------------------------------------------------------------
    def expireOldDevices(self):
        expired = list()

        now = time.clock()
        self.lock.acquire()

        # first, find all the expired keys
        for addr, last_seen in self.cache.items():
            if now - last_seen >= self.timeout:
                expired.append(addr)

        # now, delete the expired addresses
        for addr in expired:
            self.logger.debug('device expired: %s', addr)
            del self.cache[addr]

        self.lock.release()

    #---------------------------------------------------------------------------
    def getClock(self, address):
        addr = address.upper()
        return self.cache.get(addr)

    #---------------------------------------------------------------------------
    def isActiveHardwareAddr(self, address):
        clock = self.getClock(address)

        # TODO handle expired clock
        return (clock is not None)

