#def transaction(fn):
#    def wrapper(*args, **kwargs):
#        print(args)
#        print(kwargs)
#        args[0].a += args[1]
#        ret = fn(*args, **kwargs)
#        args[0].b += args[2]
#        return ret
#    return wrapper

def transaction(fn):
    def wrapper(*args, **kwargs):
        print(args)
        print(kwargs)
        x = fn(*args, **kwargs)
        args[0].a += args[1]
        x1 = args[0].critical_section()
        print(x1)
        args[0].b += args[2]
        x2 = args[0].normal_section()
        print(x2)
        return x
    return wrapper

class TestAt(object):
    def __init__(self):
        self.a = 1
        self.b = 2

    @transaction
    def add(self, a, b, c):
        def critical_section():
            print("critical section")
            return a + b
        def normal_section():
            print("normal section")
            return c
        self.critical_section = critical_section
        self.normal_section = normal_section
        return

        #print("a=%d, b=%d, c=%d" % (a, b, c))
        #return c

A = TestAt()
c = A.add(1, 2, 3)
print(c, A.a, A.b)
c = A.add(1, 2, 3)
print(c, A.a, A.b)
c = A.add(1, 2, 3)
print(c, A.a, A.b)