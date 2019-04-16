import inspect
import funcsigs # python 2

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
'''
c = A.add(1, 2, 3)
print(c, A.a, A.b)
c = A.add(1, 2, 3, 4, 5)
print(c, A.a, A.b)
c = A.add(1, 2, 3, lock_start=5, lock_len=6)
print(c, A.a, A.b)
'''
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