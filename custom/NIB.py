from ryu.base import app_manager
from ryu.tus import tus_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

from operator import attrgetter

from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

import time

class NIB(tus_manager.TusApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    '''

    def __init__(self, *args, **kwargs):
        super(NIB, self).__init__(*args, **kwargs)
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        msg = ev.msg
        ofp = msg.datapath.ofproto
        body = ev.msg.body

        flows = []
        for stat in body:
            flows.append('table_id=%s match=%s '
                        'duration_sec=%d duration_nsec=%d '
                        'priority=%d '
                        'idle_timeout=%d hard_timeout=%d '
                        'cookie=%d packet_count=%d byte_count=%d '
                        'actions=%s' %
                          (stat.table_id, stat.match,
                          stat.duration_sec, stat.duration_nsec,
                          stat.priority,
                          stat.idle_timeout, stat.hard_timeout,
                          stat.cookie, stat.packet_count, stat.byte_count,
                          stat.actions))
        self.logger.debug('FlowStats: %s', flows)
    '''

    def __init__(self, *args, **kwargs):
        super(NIB, self).__init__(*args, **kwargs)
        print(self.dpset)
        print(self.dpset.get_all())
        print(self.dpset.get(1))
        self.datapaths = {}
        self.recov_thread = hub.spawn(self._recov)
        self.monitor_thread = hub.spawn(self._monitor)

    def _recov(self):
        hub.sleep(5)
        print(self.dpset.get_all())
        print(self.dpset.get(1))
        self.failure_recov()

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]
        
        print(self.dpset.get_all())
        print(self.dpset.get(1))

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_stats(dp)
            hub.sleep(10)

    def _request_stats(self, datapath):
        self.logger.debug('send stats request: %016x', datapath.id)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        table_id = 0xff
        out_port = ofproto.OFPP_NONE

        req = parser.OFPFlowStatsRequest(datapath, 0, match, table_id, out_port)
        datapath.send_msg(req)

        #req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_NONE)
        datapath.send_msg(req)
    '''
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('datapath         '
                         'in-port  eth-dst           '
                         'out-port packets  bytes')
        self.logger.info('---------------- '
                         '-------- ----------------- '
                         '-------- -------- --------')
        for stat in sorted([flow for flow in body if flow.priority == 1],
                           key=lambda flow: (flow.match['in_port'],
                                             flow.match['eth_dst'])):
            self.logger.info('%016x %8x %17s %8x %8d %8d',
                             ev.msg.datapath.id,
                             stat.match['in_port'], stat.match['eth_dst'],
                             stat.instructions[0].actions[0].port,
                             stat.packet_count, stat.byte_count)
    '''
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        msg = ev.msg
        ofp = msg.datapath.ofproto
        body = ev.msg.body

        flows = []
        for stat in body:
            flows.append('table_id=%s match=%s '
                     'duration_sec=%d duration_nsec=%d '
                     'priority=%d '
                     'idle_timeout=%d hard_timeout=%d '
                     'cookie=%d packet_count=%d byte_count=%d '
                     'actions=%s' %
                     (stat.table_id, stat.match,
                      stat.duration_sec, stat.duration_nsec,
                      stat.priority,
                      stat.idle_timeout, stat.hard_timeout,
                      stat.cookie, stat.packet_count, stat.byte_count,
                      stat.actions))
        self.logger.debug('FlowStats: %s', flows)


    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.info('datapath         port     '
                         'rx-pkts  rx-bytes rx-error '
                         'tx-pkts  tx-bytes tx-error')
        self.logger.info('---------------- -------- '
                         '-------- -------- -------- '
                         '-------- -------- --------')
        for stat in sorted(body, key=attrgetter('port_no')):
            #self.logger.info('%016x %8x %8d %8d %8d %8d %8d %8d',
            #                 ev.msg.datapath.id, stat.port_no,
            #                 stat.rx_packets, stat.rx_bytes, stat.rx_errors,
            #                 stat.tx_packets, stat.tx_bytes, stat.tx_errors)
            d = {}
            d["datapath=%x, port=%x, rx-pkts" % (ev.msg.datapath.id, stat.port_no,)] = int(stat.rx_packets)
            d["datapath=%x, port=%x, rx-bytes" % (ev.msg.datapath.id, stat.port_no,)] = int(stat.rx_bytes)
            d["datapath=%x, port=%x, rx-error" % (ev.msg.datapath.id, stat.port_no,)] = int(stat.rx_errors)
            d["datapath=%x, port=%x, tx-pkts" % (ev.msg.datapath.id, stat.port_no,)] = int(stat.tx_packets)
            d["datapath=%x, port=%x, tx-bytes" % (ev.msg.datapath.id, stat.port_no,)] = int(stat.tx_bytes)
            d["datapath=%x, port=%x, tx-error" % (ev.msg.datapath.id, stat.port_no,)] = int(stat.tx_errors)
            self.nib.update(d)