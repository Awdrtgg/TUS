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

import fnctl
import inspect
import json

class Const(object):
    class ConstError(TypeError) : pass
    class ConstCaseError(ConstError):pass

    def __init__(self):
        self.TX_LEN = 100
        self.VALIDATION = 0x0
        self.WRITE = 0x1
        self.INACTIVE = 0x2

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError("Can't change const value!")
        if not name.isupper():
            raise self.ConstCaseError('const "%s" is not all letters are capitalized' % name)
        self.__dict__[name] = value

const = Const()


def transactional_ex(fn):
    def wrapper(*args, **kwargs):
        bound_args = inspect.signature(fn).bind(*args, **kwargs)
        bound_args.apply_defaults()
        target_args = dict(bound_args.arguments)
        cls_obj = target_args['self']
        lock_len, lock_start, lock_whence = 0, 0, 0
        if 'lock_len' in target_args: lock_len = target_args['lock_len']
        if 'lock_start' in target_args: lock_len = target_args['lock_start']
        if 'lock_whence' in target_args: lock_len = target_args['lock_whence']
        
        cls_obj.fp = open(cls_obj.filename, "rb+")
        fnctl.lockf(cls_obj.fp, fnctl.LOCK_EX, lock_len, lock_start, lock_whence)
        
        ret = fn(*args, **kwargs)
        
        fnctl.lockf(cls_obj.fp, fnctl.LOCK_UN, lock_len, lock_start, lock_whence)
        return ret

    return wrapper

def transactional_sh(fn):
    def wrapper(*args, **kwargs):
        bound_args = inspect.signature(fn).bind(*args, **kwargs)
        bound_args.apply_defaults()
        target_args = dict(bound_args.arguments)
        cls_obj = target_args['self']
        lock_len, lock_start, lock_whence = 0, 0, 0
        if 'lock_len' in target_args: lock_len = target_args['lock_len']
        if 'lock_start' in target_args: lock_start = target_args['lock_start']
        if 'lock_whence' in target_args: lock_whence = target_args['lock_whence']
        
        cls_obj.fp = open(cls_obj.filename, "rb+")
        fnctl.lockf(cls_obj.fp, fnctl.LOCK_SH, lock_len, lock_start, lock_whence)
        
        ret = fn(*args, **kwargs)
        
        fnctl.lockf(cls_obj.fp, fnctl.LOCK_UN, lock_len, lock_start, lock_whence)
        return ret
        
    return wrapper


class FileOp(object):
    def __init__(self, filename):
        self.fp = None
        self.filename = filename

    def __del__(self):
        if self.fp:
            self.fp.close()

class NIB(FileOp):
    def __init__(self, filename="tus/nib.json"):
        super(NIB, self).__init__(self.filename)

    @transactional_sh
    def read(self, key):
        data = json.load(self.fp)
        if key in data:
            return data[key]
        return None

    @transactional_sh
    def write(self, key, value):
        data = json.load(self.fp)
        data[key] = value
        self.fp.seek(0, os.SEEK_SET)
        json.dump(data, self.fp)
    
    @transactional_sh
    def update(self, update_dict):
        data = json.load(self.fp)
        for key, value in update_dict.items():
            data[key] = value
        self.fp.seek(0, os.SEEK_SET)
        json.dump(data, self.fp)


class TX(object):
    # TODO 
    # everything...

    def __init__(self, line=None):
        if not line:
            d = [l.strip() for l in line.split(',')]
            self.tx_id = int(d[0])
            self.STATE = int(d[1])
            self.match = d[2]
            self.VOLATILE = int(d[2])
            self.action = d[3]
            self.state = int(d[3])
        else:
            self.tx_id = 0
            self.STATE = 0
            self.match = d[2]
            self.VOLATILE = int(d[2])
            self.action = d[3]
            self.state = int(d[3])
    
    def __str__(self):
        s1 = self.tx_id
        s2 = self.STATE
        s3 = self.match
        s4 = self.action
        return "%25s,%25s,%25s,%25s" % (s1, s2, s3, s4)

class Log(FileOp):
    def __init__(self, filename="tus/log.txt"):
        super(Log, self).__init__(self.filename)

    def _line_to_tx(self, line):
        # TODO: exception!
        t = TX(line)
        return const.TX_LEN * t.tx_id

    def lock_info(self, tx_id):
        # tx_id <= 0 refers to lock the whole file
        if (tx_id <= 0):
            ret = {'lock_len': 0, 'lock_start':0, 'lock_whence':0}
        else:
            ret = {'lock_len': const.TX_LEN, 'lock_start': const.TX_LEN * tx_id, 'lock_whence':0}
        return ret

    @transactional_sh
    def read(self, tx_id, lock_len=0, lock_start=0, lock_whence=0):
        self.fp.seek(const.TX_LEN * tx_id, os.SEEK_SET)
        line = self.fp.readline()
        tx = TX(line)
        return tx

    @transactional_sh
    def new(self, lock_len=0, lock_start=0, lock_whence=0):
        # TODO
        # decide the format of the first line
        self.fp.seek(0, os.SEEK_SET)
        line = self.fp.readline()
        max_id = int(line) + 1 # note the first line format
        tx.tx_id = max_id

        self.fp.seek(0, os.SEEK_SET)
        log_stat = '%49d,%49d\n' % (max_id, max_id) # note the first line format
        self.fp.write(log_stat)
        
        self.fp.seek(const.TX_LEN * max_id, os.SEEK_SET)
        self.fp.write(str(tx))
        return max_id
    
    @transactional_sh
    def update(self, tx, lock_len=0, lock_start=0, lock_whence=0):
        self.fp.seek(const.TX_LEN * tx.tx_id)
        self.fp.write(str(tx))


class TUSInterface(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(TUSInterface, self).__init__(*args, **kwargs)
        self.nib = NIB()
        self.log = Log()

    def transactions(self):
        print('transaction!')
        return self.log.new()
    
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
        