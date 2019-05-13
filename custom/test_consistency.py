# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.tus import tus_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, arp
from ryu.lib.packet import ether_types
from ryu.lib import hub

import time


class SimpleSwitch13(tus_manager.TusApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.flag_ipv4 = False
        self.lost_packet = {
            1: {1: 0, 2: 0, 3: 0},
            2: {1: 0, 2: 0},
            3: {1: 0, 2: 0},
            4: {1: 0, 2: 0, 3: 0},
            5: {1: 0, 2: 0},
        }
        hub.spawn(self._lost_report)

    
    def _lost_report(self):
        while True:
            self.logger.info('pkt lost report: ' + str(self.lost_packet))
            hub.sleep(10)


    def add_flow(self, priority, inst, cmd, buffer_id=0xffffffff):
        action_dict = {
            'name': 'OFPFlowMod',
            'kwargs': {
                'buffer_id': buffer_id,
                'instructions': inst,
                'command': cmd,
                'priority': priority,
            }
        }
        return action_dict


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)

        if not self.flag_ipv4:
            self.flag_ipv4 = True
            self.set_path_1(ev.msg)
        else:
            msg = ev.msg
            in_port = msg.match['in_port']
            pkt = packet.Packet(msg.data)
            eth = pkt.get_protocols(ethernet.ethernet)[0]
            v4 = pkt.get_protocols(ipv4.ipv4)
            self.logger.info('sw %d, port %d: Unexpected packet in...' % (msg.datapath.id, in_port,))
            self.lost_packet[msg.datapath.id][in_port] += 1


    def set_path_1(self, msg):
        self.logger.info('Setting up path 1...')
        tx_id = self.transactions()

        datapath = self.dpset.get(1)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # h1 -> h2
        match = parser.OFPMatch(in_port=1, eth_src='00:00:00:00:00:01')
        actions = [parser.OFPActionOutput(2)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        cmd = ofproto.OFPFC_ADD
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_ADD)
        self.tx_write(tx_id, self.dpset.get(2), match, action_dict)
        self.tx_write(tx_id, self.dpset.get(3), match, action_dict)
        self.tx_write(tx_id, self.dpset.get(4), match, action_dict)
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_ADD, msg.buffer_id)
        self.tx_write(tx_id, self.dpset.get(1), match, action_dict)
        
        # h2 -> h1
        match = parser.OFPMatch(in_port=2, eth_src='00:00:00:00:00:02')
        actions = [parser.OFPActionOutput(1)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_ADD)
        self.tx_write(tx_id, self.dpset.get(3), match, action_dict)
        self.tx_write(tx_id, self.dpset.get(2), match, action_dict)
        self.tx_write(tx_id, self.dpset.get(1), match, action_dict)
        self.tx_write(tx_id, self.dpset.get(4), match, action_dict)

        self.tx_commit(tx_id, volatile=True)
        
        self.logger.info('Path 1 set up complete. Sleep 10s.')
        hub.spawn(self._set_path_2)


    def _set_path_2(self):
        hub.sleep(10)
        self.set_path_2()


    def set_path_2(self):
        datapath = self.dpset.get(1)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info('Setting up path 2...')
        tx_id = self.transactions()

        # h1 -> h2
        match1 = parser.OFPMatch(in_port=1, eth_src='00:00:00:00:00:01')
        match2 = parser.OFPMatch(in_port=2, eth_src='00:00:00:00:00:02')
        match3 = parser.OFPMatch(in_port=3, eth_src='00:00:00:00:00:01')
        match4 = parser.OFPMatch(in_port=3, eth_src='00:00:00:00:00:02')

        # D & E
        actions = [parser.OFPActionOutput(2)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_ADD)
        self.tx_write(tx_id, self.dpset.get(4), match3, action_dict)
        self.tx_write(tx_id, self.dpset.get(5), match1, action_dict)

        self.barrier(tx_id, self.dpset.get(1))

        # A
        actions = [parser.OFPActionOutput(3)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_MODIFY)
        self.tx_write(tx_id, self.dpset.get(1), match1, action_dict)

        # garbage collection
        actions = []
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_DELETE)
        self.tx_write(tx_id, self.dpset.get(2), match1, action_dict)
        self.tx_write(tx_id, self.dpset.get(3), match1, action_dict)
        self.tx_write(tx_id, self.dpset.get(4), match1, action_dict)


        # h2 -> h1
        # A & E
        actions = [parser.OFPActionOutput(1)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_ADD)
        self.tx_write(tx_id, self.dpset.get(1), match4, action_dict)
        self.tx_write(tx_id, self.dpset.get(5), match2, action_dict)

        self.barrier(tx_id, self.dpset.get(4))

        # D
        actions = [parser.OFPActionOutput(3)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_MODIFY)
        self.tx_write(tx_id, self.dpset.get(4), match2, action_dict)

        # garbage collection
        actions = []
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        action_dict = self.add_flow(1, inst, ofproto.OFPFC_DELETE)
        self.tx_write(tx_id, self.dpset.get(4), match2, action_dict)
        self.tx_write(tx_id, self.dpset.get(3), match2, action_dict)
        self.tx_write(tx_id, self.dpset.get(2), match2, action_dict)

        self.tx_commit(tx_id, volatile=True)

        self.logger.info('Path 2 set up complete.')
