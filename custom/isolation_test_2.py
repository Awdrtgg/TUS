from ryu.base import app_manager
#from ryu import tus_core
from ryu.tus import tus_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0

class ISOtest1(tus_manager.TusApp):
#class ISOtest2(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ISOtest2, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        ofp_parser = dp.ofproto_parser

        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]
        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions)
        #dp.send_msg(out)
        #print(actions)
        #fo = open("test.out", 'a+')
        #fo.write("This is test 2. Action sent: " + str(actions) + "\n")
        #fo.close()

        print(type(msg), msg)
        print(type(dp), dp)
        print(type(ofp), ofp)
        print(type(ofp_parser), ofp_parser)
        print(type(actions[0]), actions[0])
        print(type(out), out)

        self.tx_commit(1, 0)