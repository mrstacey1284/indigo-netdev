#!/usr/bin/env python2.7

import logging
import unittest

import utils

# keep logging output to a minumim for testing
logging.basicConfig(level=logging.ERROR)

################################################################################
class ValidateIntegers(unittest.TestCase):

    #---------------------------------------------------------------------------
    def assertError(self, value, min=None, max=None):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_Int('address', values, errors, min=min, max=max)
        self.assertIn('address', errors)

    #---------------------------------------------------------------------------
    def assertNoError(self, value, min=None, max=None):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_Int('address', values, errors, min=min, max=max)
        self.assertNotIn('address', errors)

    #---------------------------------------------------------------------------
    def test_ZeroOnlyOk(self):
        self.assertNoError(0, min=0, max=0)

    #---------------------------------------------------------------------------
    def test_NaN(self):
        self.assertError('NaN')

    #---------------------------------------------------------------------------
    def test_AnyNumbersOkay(self):
        self.assertNoError(0)
        self.assertNoError(1)
        self.assertNoError(1234567890)
        self.assertNoError(9876543210)

    #---------------------------------------------------------------------------
    def test_NumbersInRange(self):
        self.assertNoError(0, min=-1, max=1)
        self.assertNoError(5, min=1, max=10)

    #---------------------------------------------------------------------------
    def test_NumbersOutOfRange(self):
        self.assertError(0, min=1, max=10)

    #---------------------------------------------------------------------------
    def test_PartialRangeOk(self):
        self.assertNoError(0, max=1)
        self.assertNoError(1234567890, min=1)

    #---------------------------------------------------------------------------
    def test_PartialRangeNotOk(self):
        self.assertError(0, min=1)
        self.assertError(1, max=0)
        self.assertError(1234567890, max=0)

    #---------------------------------------------------------------------------
    def test_NegativesOk(self):
        self.assertNoError(-1)
        self.assertNoError(-1, max=0)

    #---------------------------------------------------------------------------
    def test_NegativesNotOk(self):
        self.assertError(-1, min=0)

################################################################################
class ValidateStrings(unittest.TestCase):

    #---------------------------------------------------------------------------
    def assertError(self, value, emptyOk=False):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_String('address', values, errors, emptyOk=emptyOk)
        self.assertIn('address', errors)

    #---------------------------------------------------------------------------
    def assertNoError(self, value, emptyOk=False):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_String('address', values, errors, emptyOk=emptyOk)
        self.assertNotIn('address', errors)

    #---------------------------------------------------------------------------
    def test_EmptyString(self):
        self.assertError('')
        self.assertNoError('', emptyOk=True)

    #---------------------------------------------------------------------------
    def test_NoneString(self):
        self.assertError(None)
        self.assertError(None, emptyOk=True)

    #---------------------------------------------------------------------------
    def test_MissingString(self):
        values = dict()
        errors = dict()

        utils.validateConfig_String('undef', values, errors)
        self.assertIn('undef', errors)

    #---------------------------------------------------------------------------
    def test_BasicString(self):
        self.assertNoError('this is a basic string')

    #---------------------------------------------------------------------------
    def test_NumericString(self):
        self.assertNoError('42')
        self.assertNoError('898234765')
        self.assertNoError('897,654,321')
        self.assertNoError('3.141592654')

    #---------------------------------------------------------------------------
    def test_MixedString(self):
        self.assertNoError('p4$$w0RD')
        self.assertNoError('a string with SYMBOLS (*!&@~) and NUMBERS (98,764) too!')

    #---------------------------------------------------------------------------
    def test_UnicodeString(self):
        self.assertNoError(u'something in unicode pls')

################################################################################
class ValidateHostnames(unittest.TestCase):

    #---------------------------------------------------------------------------
    def assertError(self, value):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_Hostname('address', values, errors)
        self.assertIn('address', errors)

    #---------------------------------------------------------------------------
    def assertNoError(self, value):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_Hostname('address', values, errors)
        self.assertNotIn('address', errors)

    #---------------------------------------------------------------------------
    def test_MissingHostname(self):
        values = dict()
        errors = dict()

        utils.validateConfig_Hostname('undef', values, errors)
        self.assertIn('undef', errors)

    #---------------------------------------------------------------------------
    def test_EmptyHostname(self):
        self.assertError('')
        self.assertError(None)

    #---------------------------------------------------------------------------
    def test_InvalidHostname(self):
        self.assertError('bad+wolf')

    #---------------------------------------------------------------------------
    def test_BasicHostname(self):
        self.assertNoError('www.google.com')
        self.assertNoError('8.8.8.8')

    #---------------------------------------------------------------------------
    def test_Localhost(self):
        self.assertNoError('localhost')
        self.assertNoError('127.0.0.1')

    #---------------------------------------------------------------------------
    def test_URL(self):
        self.assertError('http://www.google.com/')
        self.assertError('http://www.google.com')

    #---------------------------------------------------------------------------
    def test_MacAddress(self):
        self.assertError('8c:85:90:4f:7f:73')

################################################################################
class ValidateMacAddress(unittest.TestCase):

    #---------------------------------------------------------------------------
    def assertError(self, value):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_MAC('address', values, errors)
        self.assertIn('address', errors)

    #---------------------------------------------------------------------------
    def assertNoError(self, value):
        values = { 'address' : value }

        errors = dict()

        utils.validateConfig_MAC('address', values, errors)
        self.assertNotIn('address', errors)

    #---------------------------------------------------------------------------
    def test_EmptyAddress(self):
        self.assertError('')
        self.assertError(None)

    #---------------------------------------------------------------------------
    def test_BasicAddress(self):
        self.assertNoError('8c:85:90:4f:7f:73')
        self.assertNoError('8C:85:90:4F:7F:73')

    #---------------------------------------------------------------------------
    def test_MalformedAddress(self):
        self.assertError('8c:85:0:4f:7f:73')
        self.assertError('8c.85.90.4f.7f.73')
        self.assertError('8C85904F7F73')

    #---------------------------------------------------------------------------
    def test_InvalidAddress(self):
        self.assertError('localhost')
        self.assertError('-')
        self.assertError(':::::')

    #---------------------------------------------------------------------------
    def test_WindowsAddress(self):
        self.assertNoError('8c-85-90-4f-7f-73')
