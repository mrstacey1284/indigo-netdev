## handle client activities for Network Devices

import logging
import shlex
import socket
import urllib2
import threading
import subprocess

################################################################################
class ClientBase():

    #---------------------------------------------------------------------------
    def __init__(self):
        self.logger = logging.getLogger('Plugin.client.ClientBase')
        self.execLock = threading.Lock()

    #---------------------------------------------------------------------------
    # defined here as a convenience to subclasses
    def _exec(self, *cmd):
        self.execLock.acquire()
        self.logger.debug(u'=> exec%s', cmd)

        retval = -1

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()

        retval = proc.returncode
        self.logger.debug(u'=> exit(%d)', retval)

        # TODO check perr
        #self.logger.warn(perr)

        self.execLock.release()
        return (retval == 0)

################################################################################
class NullClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self):
        ClientBase.__init__(self)

    #---------------------------------------------------------------------------
    def isAvailable(self):
        return False

################################################################################
class LocalCommand(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, statusCommand='/usr/bin/true'):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.LocalCommand')

        self.statusCommand = statusCommand

    #---------------------------------------------------------------------------
    def isAvailable(self):
        statusCmd = self.statusCommand
        self.logger.debug(u'checking status: %s', statusCmd)

        if statusCmd is None:
            return False
        else:
            cmd = shlex.split(statusCmd)
            return self._exec(*cmd)

################################################################################
class ServiceClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, address, port):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.ServiceClient')

        self.address = address
        self.port = port

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def isAvailable(self):
        self.logger.debug('checking host - %s:%d', self.address, self.port)

        ret = True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect( (self.address, self.port) )
            sock.close()
        except:
            ret = False

        return ret

################################################################################
class PingClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, address):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.PingClient')
        self.address = address

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def isAvailable(self):
        self.logger.debug('pinging address - %s', self.address)

        # we will only wait for 1 ping response
        cmd = ['/sbin/ping', '-c1', self.address]

        return self._exec(*cmd)

################################################################################
class HttpClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, url):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.client.HttpClient')
        self.url = url

    #---------------------------------------------------------------------------
    # determine if the returned status code is success or error
    def isAvailable(self):
        self.logger.debug('connecting to URL - %s', self.url)
        available = None

        try:
            resp = urllib2.urlopen(self.url)
            status = resp.getcode()

            self.logger.debug('HTTP status - %d', status)
            available = (200 <= status <= 299)

            # XXX how are redirects handled?

        except Exception as e:
            self.logger.warn(str(e))
            available = False

        # XXX maybe we want to return None (Error) for 5xx codes?

        return available

################################################################################
class SSHClient(ServiceClient):

    # FIXME not a big fan of the "commands" dictionary...
    # commands contain user-defined instructions for specific actions:
    # - status : determine if the system is available
    # - shutdown : shut the system down; halt; power off

    #---------------------------------------------------------------------------
    def __init__(self, address, port=22, username=None, password=None):
        ServiceClient.__init__(self, address, port)
        self.logger = logging.getLogger('Plugin.client.SSHClient')

        self.commands = dict()
        self.username = username
        self.password = password

    #---------------------------------------------------------------------------
    def isAvailable(self):
        statusCmd = self.commands.get('status', None)
        self.logger.debug(u'checking remote status: %s', statusCmd)

        if statusCmd is None:
            return ServiceClient.isAvailable(self)
        else:
            cmd = shlex.split(statusCmd)
            return self._rexec(*cmd)

    #---------------------------------------------------------------------------
    def turnOff(self):
        shutdownCmd = self.commands.get('shutdown', None)
        self.logger.debug(u'=> %s', shutdownCmd)
        if shutdownCmd is None: return False

        # execute the command remotely
        cmd = shlex.split(shutdownCmd)
        status = self._rexec(*cmd)

        return status

    #---------------------------------------------------------------------------
    def _rexec(self, *cmd):
        # setup the remote command using a safe ssh config
        # XXX -f would be ideal, but we lose the return code of the remote command
        rcmd = ['/usr/bin/ssh', '-anTxq']

        # TODO support global timeout, e.g.
        #rcmd.append('-o', 'ConnectTimeout=%d' % connectionTimeout)

        # username is optional for SSH commands...
        username = self.username
        if username is not None and len(username) > 0:
            self.logger.debug(u'running as remote user: %s', username)
            rcmd.extend(('-l', username))
        else:
            # TODO capture local username in debug log
            self.logger.debug(u'running as local user')

        # add the host and port
        rcmd.extend(('-p', str(self.port), self.address))

        # add all commands supplied by caller
        rcmd.extend(cmd)

        return self._exec(*rcmd)

