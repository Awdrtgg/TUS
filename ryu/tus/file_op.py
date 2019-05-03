import inspect
#import funcsigs
import fcntl
import json

from ryu.tus.const import const

def transactional_ex(fn):
    def wrapper(*args, **kwargs):
        bound_args = inspect.signature(fn).bind(*args, **kwargs)
        bound_args.apply_defaults()
        #bound_args = funcsigs.signature(fn).bind(*args, **kwargs)
        target_args = dict(bound_args.arguments)
        print(target_args)
        cls_obj = target_args['self']
        lock_len, lock_start, lock_whence = 0, 0, 0
        if 'lock_len' in target_args: lock_len = target_args['lock_len']
        if 'lock_start' in target_args: lock_len = target_args['lock_start']
        if 'lock_whence' in target_args: lock_len = target_args['lock_whence']
        
        file_op = 'r+'
        if 'file_op' in target_args: file_op = target_args['file_op']
        cls_obj.fp = open(cls_obj.filename, file_op)
        fcntl.lockf(cls_obj.fp, fcntl.LOCK_SH, lock_len, lock_start, lock_whence)
        
        ret = fn(*args, **kwargs)
        
        fcntl.lockf(cls_obj.fp, fcntl.LOCK_UN, lock_len, lock_start, lock_whence)
        return ret

    return wrapper

def transactional_sh(fn):
    def wrapper(*args, **kwargs):
        bound_args = inspect.signature(fn).bind(*args, **kwargs)
        bound_args.apply_defaults()
        #bound_args = funcsigs.signature(fn).bind(*args, **kwargs)
        target_args = dict(bound_args.arguments)
        print(target_args)
        cls_obj = target_args['self']
        lock_len, lock_start, lock_whence = 0, 0, 0
        if 'lock_len' in target_args: lock_len = target_args['lock_len']
        if 'lock_start' in target_args: lock_start = target_args['lock_start']
        if 'lock_whence' in target_args: lock_whence = target_args['lock_whence']
        
        file_op = 'r+'
        if 'file_op' in target_args: file_op = target_args['file_op']
        cls_obj.fp = open(cls_obj.filename, file_op)
        fcntl.lockf(cls_obj.fp, fcntl.LOCK_SH, lock_len, lock_start, lock_whence)
        
        ret = fn(*args, **kwargs)
        
        fcntl.lockf(cls_obj.fp, fcntl.LOCK_UN, lock_len, lock_start, lock_whence)
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
    def __init__(self, filename="nib.json"):
        super(NIB, self).__init__(filename)

    @transactional_sh
    def read(self, key):
        # TODO 
        # support complex key match
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


class Log(FileOp):
    def __init__(self, filename="log.txt"):
        super(Log, self).__init__(filename)

    @transactional_sh
    def log(self, Log, file_op='a+'):
        self.fp.write(str(Log) + '\n')

    @transactional_sh
    def get_max_id(self):
        max_id = 0
        for line in self.fp:
            l = line.split(const.DIV)
            if len(l) > 0:
                i = int(l[1])
                if max_id < i:
                    max_id = i
        return max_id
        
