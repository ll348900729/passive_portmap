#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__title__ = ''
__author__ = 'lieh'
__mtime__ = '17-9-15'
"""
from twisted.internet import reactor, protocol,error
from twisted.python import log
import sys
import os
import json

class PortmapServerProtocol(protocol.Protocol):

    forward_client = None
    buffer = ''

    def connectionMade(self):
        if tunnel[0] is None:
            return self.transport.loseConnection()
        shost = ip_to_bin(self.transport.getPeer().host)
        sport = int_to_bin(self.transport.getPeer().port)
        forward_host_info = forward.get(str(self.transport.getHost().port),{'host':self.transport.getHost().host,
                                                                       'port':self.transport.getHost().port})
        dhost = ip_to_bin(forward_host_info['host'])
        dport = int_to_bin(forward_host_info['port'])
        print '%s:%d connecting'%(self.transport.getPeer().host,self.transport.getPeer().port)
        self.tunnel_flag = shost + sport + dhost + dport
        forward_server_factory = TunFactory(forward=True, portmap_server=self)
        for i in port_pool:
            try:
                port = reactor.listenTCP(i, forward_server_factory)
                break
            except error.CannotListenError:
                pass
        else:
            print 'No port to listen..'
        forward_server_factory.port = port
        package = self.tunnel_flag + int_to_bin(i)
        tunnel[0].transport.write(package)

    def dataReceived(self, data):
        self.buffer += data

    def SendData(self, data):
        #print 'forward server:send data length %d'%len(data)
        self.transport.write(data)

    def connectionLost(self, reason):
        print 'tunnel server server:lose connection'
        if self.forward_client:
            self.forward_client.transport.loseConnection()

class ForwardServerFactory(protocol.Factory):

    def buildProtocol(self, addr):
        server = PortmapServerProtocol()
        return server

class TunForwardProtocol(protocol.Protocol):

    def __init__(self, portmap_server, factory):
        self.portmap_server = portmap_server
        self.factory = factory
        self.factory.port.stopListening()
        self.factory.stopFactory()

    def connectionMade(self):
        self.portmap_server.dataReceived = self.SendData
        if self.portmap_server.buffer != '':
            self.SendData(self.portmap_server.buffer)
            self.portmap_server.buffer = ''
        self.portmap_server.dataReceived = self.SendData
        self.dataReceived = self.portmap_server.SendData

    def stopListen(self):
        if self.port:
            self.port.stopListening()
        reactor.callLater(180, port.stopListening)

    def SendData(self, data):
        #print 'tunnel forward server:send data length %d'%len(data)
        self.transport.write(data)

    def connectionLost(self, reason):
        self.portmap_server.transport.loseConnection()

class TunPro(protocol.Protocol):

    def connectionMade(self):
        print '%s:%d connecting' % (self.transport.getPeer().host, self.transport.getPeer().port)

    def SendData(self, data):
        #print 'tunnel server:send data length %d'%len(data)
        self.transport.write(data)

    def dataReceived(self, data):
        data = data.replace(' ','')
        if data == 'control':
            tunnel[0] = self

    def connectionLost(self, reason):
        print 'tunnel server:lose connection'

class TunFactory(protocol.Factory):

    port = None

    def __init__(self, forward=False, portmap_server=None):
        self.forward = forward
        self.portmap_server = portmap_server
        self.noconnection = True
        if self.forward:
            reactor.callLater(180, self.stopListen)


    def buildProtocol(self, addr):
        self.noconnection = False
        if self.forward:
            tunpro = TunForwardProtocol(portmap_server=self.portmap_server, factory=self)
        else:
            tunpro = TunPro()
        return tunpro

    def stopListen(self):
        if self.port and self.noconnection:
            self.port.stopListening()

def ip_to_bin(ip):
    return ''.join([chr(int(i)) for i in ip.split('.')])

def bin_to_ip(bstr):
    return '.'.join([int(ord(i)) for i in list(bstr)])

def int_to_bin(n):
    n = int(n)
    if n <= 256:
        return '\x00' + chr(n)
    else:
        return chr(n/256) + chr(n%256)

def bin_to_int(bstr):
    l = len(bstr)
    if l == 1:
        return ord(bstr)
    else:
        return ord(bstr[0])*256**(l-1) + bin_to_int(bstr[1::])

def main():
    reactor.listenTCP(server_port,TunFactory())
    for listenport in forward.keys():
        reactor.listenTCP(int(listenport), ForwardServerFactory())
    reactor.run()

if __name__ == '__main__':
    servers = {}
    tunnel = [None]
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
    forward = cfg["forward"]
    port_pool = xrange(int(cfg['port_start']),int(cfg['port_end']))
    if (deamon is False) or (p == 0):
        main()
