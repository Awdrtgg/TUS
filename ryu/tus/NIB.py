from ryu.base import app_manager
from ryu.tus import tus_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

class NIB(tus_manager.TusApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

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