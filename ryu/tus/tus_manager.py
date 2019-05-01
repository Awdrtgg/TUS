import inspect
import itertools
import logging
import sys
import os
import gc

from ryu import cfg
from ryu import utils
from ryu.app import wsgi
from ryu.controller.handler import register_instance, get_dependent_services
from ryu.controller.controller import Datapath
from ryu.controller import event
from ryu.controller.event import EventRequestBase, EventReplyBase
from ryu.lib import hub
from ryu.ofproto import ofproto_protocol

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

import time

from ryu.tus.const import const
from ryu.tus.file_op import NIB, Log
from ryu.tus.transaction import Transaction
from ryu.tus.log_item import LogItem

class TusApp(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(TusApp, self).__init__(*args, **kwargs)
        self.nib = NIB()
        self.log = Log()
        self.tx = {}

    def transactions(self):
        print('transaction!')
        tx_id = self.log.get_max_id() + 1
        self.tx[tx_id] = Transaction(tx_id)
        self.log.log(
            LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=const.READ)
        )
        print(tx_id, ' Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=const.READ)))
        return tx_id

    def tx_read(self, tx_id, switch, match, op):
        print('tx_read!' + '\n' + str(switch) + '\n' + str(match) + '\n' + str(op))

    def tx_write(self, tx_id, switch, match, action):
        print('tx_write!' + '\n' + str(switch) + '\n' + str(match) + '\n' + str(action))
    
    def tx_commit(self, tx_id, volatile):
        print('tx_commit!' + '\n' + str(volatile))
        self.tx[tx_id].state = const.VALIDATION
        self.log.log(
            LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,volatile=volatile)
        )
        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,volatile=volatile)))
        ### do validation
        print(app_manager.TUS_SERVICE)
        ###
        self.tx[tx_id].state = const.WRITE
        self.log.log(
           LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)
        )
        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)))
        ### do writing

        ###
        self.tx[tx_id].state = const.INACTIVE
        self.log.log(
            LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)
        )
        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)))
        ### do clean

        ###
        del self.tx[tx_id]
        return True

    def barrier(self, tx_id):
        print('barrier!')
        self.log.log(
            LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, barrier=True)
        )

    def failure_recov(self):
        pass
        