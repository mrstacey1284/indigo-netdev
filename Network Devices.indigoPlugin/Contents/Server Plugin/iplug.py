## Reusable building blocks for Indigo Plugins

import logging
import indigo

# TODO move config validation into this module

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
    def runLoopStep(self): pass

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

