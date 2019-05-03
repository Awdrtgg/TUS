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
from ryu.controller import ofp_event, dpset
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

import time

from ryu.tus.const import const
from ryu.tus.file_op import NIB, Log
from ryu.tus.transaction import Transaction, intersect_set
from ryu.tus.log_item import LogItem

active_tx = {}

class TusApp(app_manager.RyuApp):
    _CONTEXTS = {
        'dpset': dpset.DPSet,
    }


    def __init__(self, *args, **kwargs):
        super(TusApp, self).__init__(*args, **kwargs)
        self.dpset = kwargs['dpset']
        self.nib = NIB()
        self.log = Log()
        self.tx = {}


    def transactions(self):
        print('\ntransaction!')
        tx_id = self.log.get_max_id() + 1
        self.tx[tx_id] = Transaction(tx_id)
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=const.READ
            )
        )
        print(tx_id, ' Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=const.READ)))
        
        for app_name, app in app_manager.TUS_SERVICE:
            for tx_idd, tx_instance in app.tx:
                if tx_instance.state == const.READ:
                    self.tx[tx_id].conflict.append(tx_idd)

        #print(app_manager.TUS_SERVICE)
        return tx_id


    def tx_read(self, tx_id, dp, match, action):
        print('\ntx_read!' + '\n' + str(dp) + '\n' + str(match) + '\n' + str(action))
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,
                rw='r', dp=dp, match=match, action_or_stat=action
            )
        )
        print('Log: ', LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, rw='r', dp=dp, match=match, action_or_stat=action))
        
        self.tx[tx_id].read(dp, match, action)

    def tx_write(self, tx_id, dp, match, action):
        print('\ntx_write!' + '\n' + str(dp) + '\n' + str(match) + '\n' + str(action))

        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,
                rw='w', dp=dp, match=match, action_or_stat=action
            )
        )
        print('Log: ', LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, rw='w', dp=dp, match=match, action_or_stat=action))
        
        self.tx[tx_id].write(self, dp, match, action)


    def tx_commit(self, tx_id, volatile):
        print('\ntx_commit!' + '\n' + str(volatile))
        self.tx[tx_id].state = const.VALIDATION
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,volatile=volatile
            )
        )
        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,volatile=volatile)))
        
        # do validation 1
        if volatile:
            print('Validation 1 failed')
            self.tx[tx_id].state = const.INACTIVE
            self.log.log(
                LogItem(
                    timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
                )
            )
            print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)))
            return False
        #

        ### do validation 2
        for app_name, app in app_manager.TUS_SERVICE:
            for tx_idd, tx_instance in app.tx:
                if tx_instance.state == const.VALIDATION:
                    i = intersect_set(self.tx[tx_id].write_set, tx_instance.write_set)
                    if len(i) > 0:
                        print('Validation 2 failed')
                        self.tx[tx_id].state = const.INACTIVE
                        self.log.log(
                            LogItem(
                                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
                            )
                        )
                        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)))
                        return False
        ###

        self.tx[tx_id].state = const.WRITE
        self.log.log(
           LogItem(
               timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
            )
        )
        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)))
        
        ### do writing
        self.tx[tx_id].execute()
        ###
        
        self.tx[tx_id].state = const.INACTIVE
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
            )
        )
        print('Log: ', str(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)))
        
        ### do clean
        del self.tx[tx_id]
        ###
        
        return True


    def barrier(self, tx_id, dp):
        print('\nbarrier!')
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, barrier=True
            )
        )
        print(LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, barrier=True))

        self.tx[tx_id].barrier(dp)


    def failure_recov(self):
        pass
        