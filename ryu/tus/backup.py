import inspect
#import funcsigs

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
