import inspect
#import funcsigs # python 2
'''
def transaction(fn):
    def wrapper(*args, **kwargs):
        print(args)
        print(kwargs)
        # python 3
        #bound_args = inspect.signature(fn).bind(*args, **kwargs)
        #bound_args.apply_defaults()
        # python 2
        bound_args = funcsigs.signature(fn).bind(*args, **kwargs)

        target_args = dict(bound_args.arguments)
        print(target_args)
        args[0].a += args[1]
        ret = fn(*args, **kwargs)
        args[0].b += args[2]
        return ret
    return wrapper

#def transaction(fn):
#    def wrapper(*args, **kwargs):
#        print(args)
#        print(kwargs)
#        x = fn(*args, **kwargs)
#        args[0].a += args[1]
#       x1 = args[0].critical_section()
#      print(x1)
#        args[0].b += args[2]
#        x2 = args[0].normal_section()
#        print(x2)
#        return x
#    return wrapper

class TestAt(object):
    def __init__(self):
        self.a = 1
        self.b = 2

    @transaction
    def add(self, a, b, c, lock_start=0, lock_len=0):
        #def critical_section():
        #    print("critical section")
        #    return a + b
        #def normal_section():
        #    print("normal section")
        #    return c
        #self.critical_section = critical_section
        #self.normal_section = normal_section
        #return

        print("a=%d, b=%d, c=%d" % (a, b, c))
        print("start=%d, len=%d" % (lock_start, lock_len))
        return c

    @transaction
    def minus(self, a, b, c, lock_start=0, lock_len=0):
        print("a=%d, b=%d, c=%d" % (a, b, c))
        print("start=%d, len=%d" % (lock_start, lock_len))
        return c

A = TestAt()

#c = A.add(1, 2, 3)
#print(c, A.a, A.b)
#c = A.add(1, 2, 3, 4, 5)
#print(c, A.a, A.b)
#c = A.add(1, 2, 3, lock_start=5, lock_len=6)
#print(c, A.a, A.b)

T = {'lock_start': 5, 'lock_len': 6}
c = A.add(1, 2, 3, **T)
print(c, A.a, A.b)

c = A.minus(1, 2, 3, **T)
print(c, A.a, A.b)

class TX(object):
    def __init__(self, d):
        print(d)
        self.tx_id = int(d[0])
        self.STATE = int(d[1])
        self.match = d[2]
        self.VOLATILE = int(d[2])
        self.action = d[3]
        self.state = d[3]

    def __new__(cls, line):
        if not isinstance(line, str):
            return None
        d = [l.strip() for l in line.split(',')]
        if len(d) != 4:
            return None
        return super(TX, cls).__init__(cls, d)

t = TX('1,2,3,4')
print(t)
print(t.tx_id, t.STATE, t.match, t.VOLATILE, t.action, t.state)
'''

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

import time
class _Log():
    # TODO
    # match & action
    def __init__(self):
        self.timestamp = None
        self.tx_id = None
        self.tx_state = None
        self.match = None
        self.action = None
        self.stat = None

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

Log = _Log()
s1 = '2019-04-20 16:12:05,123,START'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,123,VALIDATION,VOLATILE'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,123,VALIDATION,PERSISTENT'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,123,WRITE'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,123,INACTIVE'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,124,BARRIER'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,123,read,match,action'
Log.from_line(s1)
print(Log)

s1 = '2019-04-20 16:12:05,123,write,match,action'
Log.from_line(s1)
print(Log)

