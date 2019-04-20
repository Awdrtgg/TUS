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
import time

class Const(object):
    class ConstError(TypeError) : pass
    class ConstCaseError(ConstError):pass

    def __init__(self):
        self.NONE = 0x0
        self.READ = 0x1
        self.VALIDATION = 0x2
        self.WRITE = 0x3
        self.INACTIVE = 0x4

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
        
        file_op = 'rb+'
        if 'file_op' in target_args: file_op = target_args['file_op']
        cls_obj.fp = open(cls_obj.filename, file_op)
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
        
        file_op = 'rb+'
        if 'file_op' in target_args: file_op = target_args['file_op']
        cls_obj.fp = open(cls_obj.filename, file_op)
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


class Transaction(object):
    # TODO 
    # everything...

    def __init__(self, tx_id):
        self.tx_id = tx_id
        self.state = const.READ
        self.read_set = {}
        self.write_set = {}
        
    def read(self, key, value):
        self.read_set[key] = value
    
    def write(self, key, value):
        self.write_set[key] = value
    

class LogItem():
    # TODO
    # match & action
    def __init__(self, timestamp=None, tx_id=None, tx_state=None, 
                 match=None, action=None, stat=None, volatile=False, 
                 rw='r', barrier=False):
        self.timestamp = timestamp
        self.tx_id = tx_id
        self.tx_state = tx_state
        self.match = match
        self.action = action
        self.stat = stat
        self.volatile = volatile
        self.rw = rw
        self.barrier = barrier

    def from_line(self, line):
        properties = [l.strip() for l in line.split(',')]
        if len(properties) < 3:
            print(properties) # TODO: maybe send an error?

        self.timestamp = time.mktime(time.strptime(properties[0], "%Y-%m-%d %H:%M:%S"))
        self.tx_id = int(properties[1])

        self.tx_state = const.NONE
        self.barrier = False
        self.volatile = False
        self.rw = None
        if len(properties) <= 4:
            self.tx_state = properties[2]
            if properties[2] == 'START':
                self.tx_state = const.READ
            elif properties[2] == 'VALIDATION':
                self.tx_state = const.VALIDATION
                if properties[3] == 'VOLATILE':
                    self.volatile = True
            elif properties[2] == 'WRITE':
                self.tx_state = const.WRITE
            elif properties[2] == 'INACTIVE':
                self.tx_state = const.INACTIVE
            elif properties[2] == 'BARRIER':
                self.tx_state = const.READ
                self.barrier = True
        else:
            # TODO
            if properties[2] == 'read':
                self.rw = 'r'
            elif properties[2] == 'write':
                self.rw = 'w'
            self.match = None
            self.action = None
            self.stat = None

    def __str__(self):
        res = ''
        if self.tx_id == None:
            return res

        res += time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)) + ','
        res += str(self.tx_id) + ','
        if self.barrier:
            res += 'BARRIER'
        elif self.tx_state == const.READ:
            if self.match == None:
                res += 'START'
            else:
                pass # TODO
        elif self.tx_state == const.VALIDATION:
            res += 'VALIDATION' + ','
            if self.volatile:
                res += 'VOLATILE'
            else:
                res += 'PERSISTENT'
        elif self.tx_state == const.WRITE:
            res += 'WRITE'
        elif self.tx_state == const.INACTIVE:
            res += 'INACTIVE'
        else:
            if self.rw == 'r':
                res += 'read'
            elif self.rw == 'w':
                res += 'write'
            res += ','
            # TODO
        return res



class Log(FileOp):
    def __init__(self, filename="tus/log.txt"):
        super(Log, self).__init__(self.filename)

    def log(self, Log, file_op='ab+'):
        self.fp.write(str(Log) + '\n')

    def get_max_id(self):
        max_id = 0
        for line in self.fp:
            l = line.split(',')
            if len(l) > 0:
                i = int(l[1])
                if max_id < i:
                    max_id = i
        return max_id
        



class TUSInterface(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(TUSInterface, self).__init__(*args, **kwargs)
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
        ### do validation

        ###
        self.tx[tx_id].state = const.WRITE
        self.log.log(
            LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)
        )
        ### do writing

        ###
        self.tx[tx_id].state = const.INACTIVE
        self.log.log(
            LogItem(timestamp=time.time(), tx_id=tx_id, tx_state=self.tx[tx_id].state)
        )
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
        