"""Custom topology example
Two directly connected switches plus a host for each switch:
   host --- switch --- switch --- host
Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, Node, CPULimitedHost, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.util import dumpNodeConnections
from mininet.log import info, error, debug, output, warn

import time

class MyTopo( Topo ):
    def __init__( self, **opts ):
        Topo.__init__(self, **opts)

        # Add hosts and switches
        h1 = self.addHost( 'h1' )
        h2 = self.addHost( 'h2' )
        ovsA = self.addSwitch( 's1' )
        ovsB = self.addSwitch( 's2' )
        ovsC = self.addSwitch( 's3' )
        ovsD = self.addSwitch( 's4' )
        ovsE = self.addSwitch( 's5' )

        # Add links
        self.addLink(h1, ovsA)
        self.addLink(ovsA, ovsB)
        self.addLink(ovsB, ovsC)
        self.addLink(ovsC, ovsD)
        self.addLink(ovsD, h2)
        self.addLink(ovsA, ovsE)
        self.addLink(ovsE, ovsD)


topos = { 'mytopo': ( lambda: MyTopo() ) }

if __name__ == '__main__':
    OVSKernelSwitch.setup()
    net = Mininet(
        topo=MyTopo(),
        switch=OVSKernelSwitch,
        build=False,
        link=TCLink,
        host=CPULimitedHost,
        autoSetMacs=True,
        autoStaticArp=True,
    )
    info(net)
    c = RemoteController('c0', ip='127.0.0.1', port=6633)
    info(c)
    net.addController(c)
    info('ready to build')
    net.build()
    info('ready to start')
    net.start()

    time.sleep(5)

    #net.iperf(
    #    hosts=None, 
    #    l4Type='UDP', 
    #    udpBw='100M', 
    #    fmt=None,
    #    seconds=20, 
    #    port=5001
    #)
    net.iperf_multi(
        hosts_list=[None, None],
        l4Type_list=['UDP', 'UDP'],
        udpBw_list=['1M', '1M'],
        fmt=[None, None],
        seconds=[20, 20],
        port=[5001, 5002]
    )

    CLI(net)
    net.stop()