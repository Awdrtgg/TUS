
class Const(object):
    class ConstError(TypeError) : pass
    class ConstCaseError(ConstError):pass

    def __init__(self):
        self.NONE = 0x0
        self.READ = 0x1
        self.VALIDATION = 0x2
        self.WRITE = 0x3
        self.INACTIVE = 0x4
        self.DIV = '||'

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError("Can't change const value!")
        if not name.isupper():
            raise self.ConstCaseError('const "%s" is not all letters are capitalized' % name)
        self.__dict__[name] = value

const = Const()