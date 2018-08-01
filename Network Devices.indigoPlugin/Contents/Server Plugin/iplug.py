## Reusable building blocks for Indigo Plugins

import re

import logging
import indigo

# a basic regex for matching simple hostnames and IP addresses
re_hostname = re.compile('^(\w[\-\.]?)+$')

# a regex for matching MAC addresses of the form MM:MM:MM:SS:SS:SS
# Windows-like MAC addresses are also supported (MM-MM-MM-SS-SS-SS)
re_macaddr = re.compile('^([0-9a-fA-F][0-9a-fA-F][:\-]){5}([0-9a-fA-F][0-9a-fA-F])$')

################################################################################
class ThreadedPlugin(indigo.PluginBase):

    # delay between loop steps, set by plugin config
    threadLoopDelay = None

    #---------------------------------------------------------------------------
    # subclasses should invoke the base __init__ if overidden
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.loadPluginPrefs(pluginPrefs)

    #---------------------------------------------------------------------------
    def deviceStartComm(self, device):
        self.logger.debug(u'Starting device - %s [%s]', device.name, device.deviceTypeId)

    #---------------------------------------------------------------------------
    def deviceStopComm(self, device):
        self.logger.debug(u'Stopping device: %s', device.name)

    #---------------------------------------------------------------------------
    # return the value from the dict as an integer, optionally providing a default value
    def getPrefAsInt(self, prefs, name, dfault=None):
        givenValue = prefs.get(name, None)

        value = dfault

        if givenValue is not None:
            value = int(givenValue)

        self.logger.debug(u'{%s} - %s', name, str(value))

        return value

    #---------------------------------------------------------------------------
    # subclasses should invoke the base loadPluginPrefs if overidden
    def loadPluginPrefs(self, prefs):
        # setup logging system
        self.logLevel = self.getPrefAsInt(prefs, 'logLevel', 20)
        self.indigo_log_handler.setLevel(self.logLevel)

        # save loop delay
        self.threadLoopDelay = self.getPrefAsInt(prefs, 'threadLoopDelay', 60)

    #---------------------------------------------------------------------------
    # reload the plugin prefs whenever the config dialog is closed
    def closedPrefsConfigUi(self, prefs, canceled):
        if canceled: return

        self.loadPluginPrefs(prefs)

    #---------------------------------------------------------------------------
    # perform the work in the thread loop for the plugin
    # subclasses should invoke the base runLoopStep if overidden
    def runLoopStep(self): raise NotImplementedError

    #---------------------------------------------------------------------------
    def runConcurrentThread(self):
        self.logger.debug(u'Thread Started')

        try:

            while not self.stopThread:
                self.runLoopStep()

                # sleep for the configured timeout
                self.sleep(self.threadLoopDelay)

        except self.StopThread:
            pass

        self.logger.debug(u'Thread Stopped')

################################################################################
def validateConfig_URL(key, values, errors, emptyOk=False):
    # TODO verify correct URL format
    return validateConfig_String(key, values, errors, emptyOk)

################################################################################
def validateConfig_MAC(key, values, errors, emptyOk=False):
    value = values.get(key, None)

    # it must first be a valid string
    if not validateConfig_String(key, values, errors, emptyOk):
        return False

    if re_macaddr.match(value) is None:
        errors[key] = 'invalid MAC address: %s' % value
        return False

    return True

################################################################################
def validateConfig_Hostname(key, values, errors, emptyOk=False):
    value = values.get(key, None)

    # it must first be a valid string
    if not validateConfig_String(key, values, errors, emptyOk):
        return False

    if re_hostname.match(value) is None:
        errors[key] = 'invalid hostname: %s' % value
        return False

    return True

################################################################################
def validateConfig_String(key, values, errors, emptyOk=False):
    value = values.get(key, None)

    if value is None:
        errors[key] = '%s cannot be empty' % key
        return False

    if not emptyOk and len(value) == 0:
        errors[key] = '%s cannot be blank' % key
        return False

    return True

################################################################################
def validateConfig_Int(key, values, errors, min=None, max=None):
    value = values.get(key, None)
    if value is None:
        errors[key] = '%s is required' % key
        return False

    intVal = None

    try:
        intVal = int(value)
    except:
        errors[key] = '%s must be an integer' % key
        return False

    if min is not None and intVal < min:
        errors[key] = '%s must be greater than or equal to %d' % (key, min)
        return False

    if max is not None and intVal > max:
        errors[key] = '%s must be less than or equal to %d' % (key, max)
        return False

    return True

