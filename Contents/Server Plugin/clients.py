## handle client activities for Network Devices

import logging
import shlex
import socket
import threading
import subprocess

################################################################################
class ClientBase():

    #---------------------------------------------------------------------------
    def __init__(self):
        # to emit Indigo events, logger must be a child of 'Plugin'
        self.logger = logging.getLogger('Plugin.ClientBase')
        self.execLock = threading.Lock()

    #---------------------------------------------------------------------------
    # defined here as a convenience to subclasses
    def _exec(self, *cmd):
        self.execLock.acquire()
        self.logger.debug(u'=> exec%s', cmd)

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pout, perr = proc.communicate()
        self.logger.debug(u'=> exit(%d)', proc.returncode)

        # TODO check perr
        #self.logger.warn(perr)

        self.execLock.release()
        return (proc.returncode == 0)


################################################################################
class ServiceClient(ClientBase):

    #---------------------------------------------------------------------------
    def __init__(self, address, port):
        ClientBase.__init__(self)
        self.logger = logging.getLogger('Plugin.ServiceClient')

        self.address = address
        self.port = port

    #---------------------------------------------------------------------------
    # determine if the specific host is reachable
    def isAvailable(self):
        self.logger.debug('checking host - %s:%d', self.address, self.port)

        ret = True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.address, self.port))
            sock.close()
        except:
            ret = False

        return ret

################################################################################
class SSHClient(ServiceClient):

    # FIXME not a big fan of the "commands" dictionary...

    #---------------------------------------------------------------------------
    def __init__(self, address, port=22, username=None):
        ServiceClient.__init__(self, address, port)
        self.logger = logging.getLogger('Plugin.SSHClient')

        self.commands = dict()
        self.username = username

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

        # execute the command remotely
        cmd = shlex.split(shutdownCmd)
        status = self._rexec(*cmd)

        return status

    #---------------------------------------------------------------------------
    def _rexec(self, *cmd):
        # setup the remote command using a safe ssh config
        # XXX -f would be ideal, but we lose the return code of the remote command
        rcmd = ['ssh', '-anTxq']

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

