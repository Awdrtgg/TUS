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
        
        for app_name, app in app_manager.TUS_SERVICE.items():
            if app == self:
                continue
            for tx_idd, tx_instance in app.tx.items():
                if tx_instance.state == const.READ:
                    self.tx[tx_id].conflict.append(tx_idd)

        return tx_id


    def tx_read(self, tx_id, match):
        value = self.nib.read(match)
        print('\ntx_read!' + '\n' + str(match) + '\n' + str(value))
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,
                rw='r', match=match, action_or_stat=value
            )
        )
        
        self.tx[tx_id].read(match, value)


    def tx_write(self, tx_id, dp, match, action):
        print('\ntx_write!' + '\n' + str(dp) + '\n' + str(match) + '\n' + str(action))
        self.tx[tx_id].write(dp, match, action)
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state,
                rw='w', dp=dp, match=match, action_or_stat=action
            )
        )
        

    def tx_commit(self, tx_id, volatile=False):
        print('\ntx_commit!' + '\n' + str(volatile))
        self.tx[tx_id].state = const.VALIDATION
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, volatile=volatile
            )
        )
        
        ### do validation 1
        if volatile:
            vld = self.nib.verify(self.tx[tx_id].read_set)
            if vld:
                print('Validation 1 failed')
                self.tx[tx_id].state = const.INACTIVE
                self.log.log(
                    LogItem(
                        timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
                    )
                )
                return False
        ###
        print('Validation 1 success')

        ### do validation 2
        for app_name, app in app_manager.TUS_SERVICE.items():
            if app == self:
                continue
            for tx_idd, tx_instance in app.tx.items():
                if tx_instance.state == const.VALIDATION:
                    i = intersect_set(self.tx[tx_id].write_set, tx_instance.write_set)
                    if len(i) > 0:
                        print('Validation 2 failed, txID1=%d, txState1=%d, txWS1=%s, txID2=%d, txState2=%d, txWS2=%s' 
                              % (tx_id, self.tx[tx_id].state, str(self.tx[tx_id].write_set), 
                                 tx_idd, tx_instance.state, str(tx_instance.write_set)
                                )
                              )
                        self.tx[tx_id].state = const.INACTIVE
                        self.log.log(
                            LogItem(
                                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
                            )
                        )
                        return False
        ###
        print('Validation 2 success')

        self.tx[tx_id].state = const.WRITE
        self.log.log(
           LogItem(
               timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
            )
        )
        
        ### do writing
        self.tx[tx_id].execute()
        ###
        
        self.tx[tx_id].state = const.INACTIVE
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state
            )
        )
        
        ### do clean
        del self.tx[tx_id]
        ###
        
        return True


    def barrier(self, tx_id, dp):
        print('\nbarrier!')
        self.tx[tx_id].barrier(dp)
        self.log.log(
            LogItem(
                timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state, barrier=True
            )
        )


    def failure_recov(self):
        tx = {}
        validation_set = []

        fp = open('log.txt')
        for line in fp:
            print(line, end='')
            trans = LogItem(dpset=self.dpset).from_line(line)
            print(str(trans))
            print(trans.timestamp, trans.tx_id, trans.tx_state, trans.rw, trans.match, trans.action_or_stat)
            print()

            if trans.tx_id not in tx:
                if trans.tx_state != const.READ:
                    print('There is something wrong!')
                tx[trans.tx_id] = Transaction(trans.tx_id)
            else:
                if trans.tx_state == const.READ:
                    if trans.rw == 'r':
                        tx[trans.tx_id].read(trans.match, trans.action_or_stat)
                    elif trans.rw == 'w':
                        tx[trans.tx_id].write(trans.dp, trans.match, trans.action_or_stat)
                    elif trans.barrier:
                        tx[trans.tx_id].barrier(trans.dp)
                    else:
                        print('There is something wrong!')
                else:
                    if trans.tx_state == const.VALIDATION:
                        tx[trans.tx_id].volatile = trans.volatile     
                    tx[trans.tx_id].state = trans.tx_state
        fp.close()

        print('trans set: ', tx)
        OCC_set = []
        for _, t in tx.items():
            if t.state == const.READ or t.state == const.INACTIVE:
                print('tx_id=%d, state is READ/INACTIVE, ignore' % (t.tx_id,))
                continue
            elif t.state == const.WRITE:
                #t.execute()
                t.state = const.INACTIVE
                print('tx_id=%d, state is WRITE, execute and set INACTIVE' % (t.tx_id,))
                #self.log.log(
                #    LogItem(
                #        timestamp=time.time(), tx_id=t.tx_id, tx_state=t.state
                #    )
                #)
            elif t.state == const.VALIDATION:
                print('tx_id=%d, state is VALIDATION, add to OCC set' % (t.tx_id,))
                OCC_set.append(t)
            else:
                print('Something wrong!')
        
        print('OCC set: ', OCC_set)
        for t1 in OCC_set:
            for t2 in OCC_set:
                if t1.state == const.INACTIVE or t1 == t2:
                    continue
                i = intersect_set(t1.write_set, t2.write_set)
                if len(i) > 0:
                    print('Validation 2 failed, txID1=%d, txState1=%d, txWS1=%s, txID2=%d, txState2=%d, txWS2=%s' 
                            % (t1.tx_id, t1.state, str(t1.write_set), 
                               t2.tx_id, t2.state, str(t2.write_set)
                              )
                    )
                    t1.state = const.INACTIVE
                    print('tx_id=%d, set INACTIVE' % (t1.tx_id,))
                    #self.log.log(
                    #    LogItem(
                    #        timestamp=time.time(), tx_id=t1.tx_id, tx_state=t1.state
                    #    )
                    #)
                    continue

                vld = True
                if t1.volatile:
                    vld = self.nib.verify(t1.read_set)
                
                if vld:
                    #t1.execute()
                    print('tx_id=%d, execute!' % (t1.tx_id,))
                else:
                    print('tx_id=%d, is VOLATILE and read_set was out-dated. Do not execute.')

                t1.state = const.INACTIVE
                print('tx_id=%d, set INACTIVE' % (t1.tx_id,))
                #self.log.log(
                #    LogItem(
                #        timestamp=time.time(), tx_id=t1.tx_id, tx_state=t1.state
                #    )
                #)