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
import argparse

class PortmapServerProtocol(protocol.Protocol):

    forward_client = None
    buffer = ''

    def connectionMade(self):
        if tunnel[0] is None:
            return self.transport.loseConnection()
        shost = ip_to_bin(self.transport.getPeer().host)
        sport = int_to_bin(self.transport.getPeer().port)
        forward_host_info = forward.get(str(self.transport.getHost().port))
        if forward_host_info is None:
            return self.connectionLost()
        forward_host_info = forward_host_info.split(':')
        if len(forward_host_info) == 2:
            dhost = ip_to_bin(forward_host_info[0])
            dport = int_to_bin(forward_host_info[1])
        else:
            return self.connectionLost()
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
        self.transport.write(data)

    def connectionLost(self, reason):
        self.portmap_server.transport.loseConnection()

class TunPro(protocol.Protocol):

    def connectionMade(self):
        print '%s:%d connecting' % (self.transport.getPeer().host, self.transport.getPeer().port)

    def SendData(self, data):
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

def int_to_bin(n):
    n = int(n)
    if n <= 256:
        return '\x00' + chr(n)
    else:
        return chr(n/256) + chr(n%256)

def start(server_ip, server_port, forward):
    reactor.listenTCP(server_port, TunFactory(), interface=server_ip)
    for listenport in forward.keys():
        reactor.listenTCP(int(listenport), ForwardServerFactory(), interface=server_ip)
    reactor.run()

def main(deamon=False, server_ip='0.0.0.0', server_port=12300, forward_config='',port_pools='', logfile='/var/log/portmap_server.log'):
    global port_pool,forward
    port_pools = port_pools.split('-')
    port_pool = xrange(int(port_pools[0]), int(port_pools[1])+1)
    forward = json.load(open(forward_config,'r'))
    if deamon:
        p = os.fork()
        if p == 0:
            log.startLogging(open(logfile, 'a+'))
            start(server_ip, server_port, forward)
    else:
        log.startLogging(sys.stdout)
        start(server_ip, server_port, forward)

if __name__ == '__main__':
    servers = {}
    tunnel = [None]
    forward = {}
    port_pool = xrange(15000, 20000)
    parser = argparse.ArgumentParser(description='Passive portmap server')
    parser.add_argument('--listen-ip', default='0.0.0.0', help='listen ip, defalut 0.0.0.0')
    parser.add_argument('--listen-port', type=int, default=12300, help='listen port, defalut 12300')
    parser.add_argument('--logfile', default='/var/log/portmap_server.log', help='log file path, default /var/log/portmap_server.log')
    parser.add_argument('--forward-config', help='forward config')
    parser.add_argument('--deamon', action='store_true', help='starting in deamon')
    parser.add_argument('--port_pool', default='15000-20000', help='port pool, default 15000-20000')
    args = parser.parse_args()
    if args.forward_config == None:
        parser.print_help()
    else:
        main(deamon=args.deamon, server_ip=args.listen_ip, server_port=args.listen_port, logfile=args.logfile, port_pools=args.port_pool, forward_config=args.forward_config)

