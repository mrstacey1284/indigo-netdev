#!/usr/bin/env python2.7

import logging
import unittest
import clients

# keep logging output to a minumim for testing
logging.basicConfig(level=logging.ERROR)

################################################################################
class GoogleDNSService(unittest.TestCase):

    def setUp(self):
        self.client = clients.ServiceClient('8.8.8.8', 53)

    def test_isAvailable(self):
        available = self.client.isAvailable()
        self.assertTrue(available)

################################################################################
class BasicLocalCommand(unittest.TestCase):

    def setUp(self):
        self.client = clients.LocalCommand()

    def test_isAvailable(self):
        available = self.client.isAvailable()
        self.assertTrue(available)

################################################################################
class LocalHostSSH(unittest.TestCase):

    def setUp(self):
        self.client = clients.SSHClient('locahost')
        self.client.commands['status'] = '/usr/bin/true'

    def test_isAvailable(self):
        available = self.client.isAvailable()
        self.assertTrue(available)

################################################################################
## MAIN ENTRY

if __name__ == '__main__':
    unittest.main(verbosity=2)

