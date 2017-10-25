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
import json

class ForwardclientProtocol(protocol.Protocol):

    tunnel_client = None
    buffer = ''

    def connectionMade(self):
        print 'forward client:connect %s:%d'%(self.transport.getPeer().host,self.transport.getPeer().port)
        self.tunnel_client.dataReceived = self.SendData

    def dataReceived(self, data):
        self.buffer += data

    def SendData(self, data):
        #print 'forward client:recv data size %d'%len(data)
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

def ip_to_bin(ip):
    return ''.join([chr(int(i)) for i in ip.split('.')])

def bin_to_ip(bstr):
    return '.'.join([str(ord(i)) for i in list(bstr)])

def int_to_bin(n):
    n = int(n)
    if n/256 == 0:
        return chr(n)
    else:
        return int_to_bin(n/256) + chr(n%256)

def bin_to_int(bstr):
    l = len(bstr)
    if l == 1:
        return ord(bstr)
    else:
        return ord(bstr[0])*256**(l-1) + bin_to_int(bstr[1::])

def main():
    reactor.connectTCP(server_ip, server_port, TunClientFactory())
    reactor.run()

if __name__ == '__main__':
    server_ip = '172.93.42.182'
    tunnel = {}
    deamon = True if '-d' in sys.argv else False
    config = sys.argv[sys.argv.index('-c')+1]
    if deamon:
        p = os.fork()
        log.startLogging(open('/home/lieh/forward.log','a+'))
    else:
        p = os.getpid()
        log.startLogging(sys.stdout)
    if os.path.exists(config):
        cfg = json.load(open(config,'r'))
    else:
        print 'can\'t found config file'
        sys.exit(1)
    server_ip = cfg['server_ip']
    server_port = int(cfg['server_port'])
    if (deamon is False) or (p == 0):
        main()
