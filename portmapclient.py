#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'lieh'
__mtime__ = '17-9-18'
"""
from twisted.internet import reactor, protocol
from twisted.python import log
import sys
import os
import argparse

class ForwardclientProtocol(protocol.Protocol):

    tunnel_client = None
    buffer = ''

    def connectionMade(self):
        print 'forward client:connect %s:%d'%(self.transport.getPeer().host,self.transport.getPeer().port)
        self.tunnel_client.dataReceived = self.SendData

    def dataReceived(self, data):
        self.buffer += data

    def SendData(self, data):
        self.transport.write(data)

    def connectionLost(self, reason):
        print 'forward client: lose connection,reason:%s'%reason.value
        if self.tunnel_client:
            self.tunnel_client.transport.loseConnection()

class ForwardClientFactory(protocol.ClientFactory):

    def __init__(self):
        self.protocol = ForwardclientProtocol()

    def buildProtocol(self, addr):
        return self.protocol

class TunClient(protocol.Protocol):

    buffer = ''

    def connectionMade(self):
        print 'tunnel client:connect to %s:%d'%(self.transport.getPeer().host, self.transport.getPeer().port)
        self.transport.write('control')
        self.SendHeart()

    def dataReceived(self, data):
        self.buffer += data
        if len(self.buffer) >= 14:
            dport = bin_to_int(self.buffer[10:12])
            dhost = bin_to_ip(self.buffer[6:10])
            forward_server_port = bin_to_int(self.buffer[12:14])
            tunnel_client = TunClientFactory(forward=True)
            portmap_client = ForwardClientFactory()
            portmap_client.protocol.tunnel_client = tunnel_client.protocol
            tunnel_client.protocol.portmap_client = portmap_client.protocol
            reactor.connectTCP(dhost,dport,
                               portmap_client)
            reactor.connectTCP(server_ip,forward_server_port,
                               tunnel_client)
            self.buffer = self.buffer[14::]
            return self.dataReceived('')

    def SendHeart(self):
        self.transport.write(' ')
        reactor.callLater(10,self.SendHeart)

    def connectionLost(self, reason):
        print 'tunnel client:lose connection'

class TunnelForwardClientProtocol(protocol.Protocol):

    portmap_client = None

    def connectionMade(self):
        print 'tunnel forward client:connect to %s:%d'%(self.transport.getPeer().host, self.transport.getPeer().port)
        if self.portmap_client.buffer != '':
            self.SendData(self.portmap_client.buffer)
            self.portmap_client.buffer = ''
        self.portmap_client.dataReceived = self.SendData

    def SendData(self, data):
        #print 'tunnel forward client:send data length %d'%len(data)
        self.transport.write(data)

    def connectionLost(self, reason):
        self.portmap_client.transport.loseConnection()

class TunClientFactory(protocol.ReconnectingClientFactory):

    def __init__(self, forward=False):
        self.forward = forward
        if self.forward:
            self.protocol = TunnelForwardClientProtocol()
        else:
            self.protocol = TunClient()
        self.maxDelay = 600

    def buildProtocol(self, addr):
        return self.protocol

    def clientConnectionLost(self, connector, unused_reason):
        if self.forward is False:
            protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, unused_reason)

    def clientConnectionFailed(self, connector, reason):
        if self.forward is False:
            protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

def bin_to_ip(bstr):
    return '.'.join([str(ord(i)) for i in list(bstr)])

def bin_to_int(bstr):
    l = len(bstr)
    if l == 1:
        return ord(bstr)
    else:
        return ord(bstr[0])*256**(l-1) + bin_to_int(bstr[1::])

def start(server_host, server_port):
    reactor.connectTCP(server_host, server_port, TunClientFactory())
    reactor.run()

def main(deamon=False, server_host='', server_port=None, logfile='/var/log/portmat_client.log'):
    if deamon:
        p = os.fork()
        if p == 0:
            log.startLogging(open(logfile, 'a+'))
            start(server_host, server_port)
    else:
        log.startLogging(sys.stdout)
        start(server_host, server_port)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Passive portmap')
    parser.add_argument('--host', help='server host')
    parser.add_argument('--port', type=int, default=12300, help='server port, defalut 12300')
    parser.add_argument('--logfile', default='/var/log/portmap_client.log', help='log file path, default /var/log/portmap_client.log')
    parser.add_argument('--deamon', action='store_true', help='starting in deamon')
    args = parser.parse_args()
    server_ip = args.host
    if args.host == None:
        parser.print_help()
    else:
        main(deamon=args.deamon, server_host=args.host, server_port=args.port, logfile=args.logfile)