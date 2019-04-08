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

import json


import fnctl

class FileOp(object):
    def __init__(self, filename):
        self.fp = open(filename, "ab+")
    
    def __del__(self):
        self.fp.close()

    def transaction(self):
        pass

class NIB(FileOp):
    filename = "tus/nib.json"

    def __init__(self):
        super(NIB, self).__init__(self.filename)
    
    def read(self, key):
        fnctl.flock(self.fp, fnctl.LOCK_EX)
        nib_dict = json.load(fp)
        fnctl.flock(self.fp, fcntl.LOCK_UN)
        return nib_dict[key]

    def write(self, d):
        fnctl.flock(self.fp, fnctl.LOCK_EX)
        nib_dict = json.load(fp)
        fnctl.flock(self.fp, fcntl.LOCK_UN)

class Log(FileOp):
    filename = "tus/log.txt"

    def __init__(self):
        super(Log, self).__init__(self.filename)

    def read(self, key):
        #fnctl.flock(self.fp, fnctl.LOCK_EX, 0, 100)
        #self.fp.seek(0, 0)
        pass


class TUSInterface(app_manager.RyuApp):
    VALIDATION = 0x0
    WRITE = 0x1
    INACTIVE = 0x2

    def __init__(self, *args, **kwargs):
        super(TUSInterface, self).__init__(*args, **kwargs)

    def transactions(self):
        print('transaction!')
        pass
    
    def tx_read(self, switch, match, op):
        print('tx_read!' + '\n' + str(switch) + '\n' + str(match) + '\n' + str(op))
        pass

    def tx_write(self, switch, match, action):
        print('tx_write!' + '\n' + str(switch) + '\n' + str(match) + '\n' + str(action))
        pass
    
    def tx_commit(self, volatile):
        print('tx_commit!' + '\n' + str(volatile))
        pass

    def barrier(self):
        print('barrier!')
        pass

    def failure_recov(self):
        pass
        