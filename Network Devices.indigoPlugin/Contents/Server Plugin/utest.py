#!/usr/bin/env python2.7

import logging
import unittest

import clients
import utils

# keep logging output to a minumim for testing
logging.basicConfig(level=logging.ERROR)

################################################################################
class CommonInternnetServices(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_GoogleDNS(self):
        client = clients.ServiceClient('8.8.8.8', 53)
        available = client.isAvailable()
        self.assertTrue(available)

################################################################################
class BasicLocalCommands(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_DefaultCommand(self):
        client = clients.LocalCommand()
        available = client.isAvailable()
        self.assertTrue(available)

################################################################################
class BasicPingTests(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_LocalPing(self):
        client = clients.PingClient('localhost')
        available = client.isAvailable()
        self.assertTrue(available)

    #---------------------------------------------------------------------------
    def test_PingEther(self):
        client = clients.PingClient('0.0.0.0')
        available = client.isAvailable()
        self.assertFalse(available)

################################################################################
class HttpStatusChecks(unittest.TestCase):

    #---------------------------------------------------------------------------
    def test_Http200(self):
        client = clients.HttpClient('https://httpstat.us/200')
        available = client.isAvailable()
        self.assertTrue(available)

    #---------------------------------------------------------------------------
    def test_Http301(self):
        client = clients.HttpClient('https://httpstat.us/301')
        available = client.isAvailable()

        # the python client should process the redirect to a "success" status
        self.assertTrue(available)

    #---------------------------------------------------------------------------
    def test_Http404(self):
        client = clients.HttpClient('https://httpstat.us/404')
        available = client.isAvailable()
        self.assertFalse(available)

    #---------------------------------------------------------------------------
    def test_Http500(self):
        client = clients.HttpClient('https://httpstat.us/500')
        available = client.isAvailable()
        self.assertFalse(available)

################################################################################
class LocalHostSSH(unittest.TestCase):

    #---------------------------------------------------------------------------
    def setUp(self):
        self.client = clients.SSHClient('locahost')
        self.client.commands['status'] = '/usr/bin/true'

    #---------------------------------------------------------------------------
    def SKIP_test_isAvailable(self):
        available = self.client.isAvailable()
        self.assertTrue(available)

################################################################################
class ValidateIntegers(unittest.TestCase):

    #---------------------------------------------------------------------------
    def setUp(self):
        self.values = dict()
        self.values['zero'] = 0
        self.values['small'] = 1
        self.values['big'] = 100000000000
        self.values['negative'] = -1
        self.values['NaN'] = 'NaN'

    #---------------------------------------------------------------------------
    def test_AllOk(self):
        errors = dict()

        utils.validateConfig_Int('zero', self.values, errors)
        self.assertNotIn('zero', errors)

        utils.validateConfig_Int('negative', self.values, errors)
        self.assertNotIn('negative', errors)

        utils.validateConfig_Int('small', self.values, errors)
        self.assertNotIn('small', errors)

        utils.validateConfig_Int('big', self.values, errors)
        self.assertNotIn('big', errors)

    #---------------------------------------------------------------------------
    def test_ZeroOk(self):
        errors = dict()

        utils.validateConfig_Int('zero', self.values, errors)
        self.assertNotIn('zero', errors)

    #---------------------------------------------------------------------------
    def test_BoundedZeroOk(self):
        errors = dict()

        utils.validateConfig_Int('zero', self.values, errors, min=-1, max=1)
        self.assertNotIn('zero', errors)

    #---------------------------------------------------------------------------
    def test_ZeroOnlyOk(self):
        errors = dict()

        utils.validateConfig_Int('zero', self.values, errors, min=0, max=0)
        self.assertNotIn('zero', errors)

    #---------------------------------------------------------------------------
    def test_ZeroNotOk(self):
        errors = dict()

        utils.validateConfig_Int('zero', self.values, errors, min=1, max=1)
        self.assertIn('zero', errors)

    #---------------------------------------------------------------------------
    def test_NaN(self):
        errors = dict()

        utils.validateConfig_Int('NaN', self.values, errors)
        self.assertIn('NaN', errors)

    #---------------------------------------------------------------------------
    def test_SmallNumberOk(self):
        errors = dict()

        utils.validateConfig_Int('small', self.values, errors, min=0, max=1)
        self.assertNotIn('small', errors)

    #---------------------------------------------------------------------------
    def test_SmallNumberNotOk(self):
        errors = dict()

        utils.validateConfig_Int('small', self.values, errors, min=2)
        self.assertIn('small', errors)

    #---------------------------------------------------------------------------
    def test_BigNumberOk(self):
        errors = dict()

        utils.validateConfig_Int('big', self.values, errors, min=1)
        self.assertNotIn('big', errors)

    #---------------------------------------------------------------------------
    def test_BigNumberNotOk(self):
        errors = dict()

        utils.validateConfig_Int('big', self.values, errors, min=0, max=0)
        self.assertIn('big', errors)

    #---------------------------------------------------------------------------
    def test_NegativeOk(self):
        errors = dict()

        utils.validateConfig_Int('negative', self.values, errors, max=0)
        self.assertNotIn('negative', errors)

    #---------------------------------------------------------------------------
    def test_NegativeNotOk(self):
        errors = dict()

        utils.validateConfig_Int('negative', self.values, errors, min=0)
        self.assertIn('negative', errors)

################################################################################
class ValidateEmptyStrings(unittest.TestCase):

    #---------------------------------------------------------------------------
    def setUp(self):
        self.values = dict()
        self.values['empty'] = ''
        self.values['none'] = None

    #---------------------------------------------------------------------------
    def test_EmptyStringOk(self):
        errors = dict()

        utils.validateConfig_String('empty', self.values, errors, emptyOk=True)
        self.assertNotIn('empty', errors)

    #---------------------------------------------------------------------------
    def test_EmptyStringNotOk(self):
        errors = dict()

        utils.validateConfig_String('empty', self.values, errors, emptyOk=False)
        self.assertIn('empty', errors)

    #---------------------------------------------------------------------------
    def test_NoneStringOk(self):
        errors = dict()

        utils.validateConfig_String('none', self.values, errors, emptyOk=True)
        self.assertNotIn('none', errors)

    #---------------------------------------------------------------------------
    def test_NoneStringNotOk(self):
        errors = dict()

        utils.validateConfig_String('none', self.values, errors, emptyOk=False)
        self.assertIn('none', errors)

################################################################################
class ValidateRegularStrings(unittest.TestCase):

    #---------------------------------------------------------------------------
    def setUp(self):
        self.values = dict()
        self.values['basic'] = 'this is a simple string'
        self.values['complex'] = 'TODO make a complex string'
        self.values['numeric'] = '0123456789'
        self.values['mixed'] = 'string with numbers: 42 and symbols: %%^ for fun'
        self.values['unicode'] = u'TODO make a unicode string'

    #---------------------------------------------------------------------------
    def test_MissingString(self):
        errors = dict()

        utils.validateConfig_String('_missing_', self.values, errors, emptyOk=False)
        self.assertIn('_missing_', errors)

    #---------------------------------------------------------------------------
    def _stdStringTest(self, key):
        errors = dict()

        utils.validateConfig_String(key, self.values, errors, emptyOk=False)
        self.assertNotIn(key, errors)

    #---------------------------------------------------------------------------
    def test_BasicString(self): self._stdStringTest('basic')
    def test_NumericString(self): self._stdStringTest('numeric')
    def test_ComplexString(self): self._stdStringTest('complex')
    def test_MixedString(self): self._stdStringTest('mixed')
    def test_UnicodeString(self): self._stdStringTest('unicode')

################################################################################
## MAIN ENTRY

if __name__ == '__main__':
    unittest.main(verbosity=2)

