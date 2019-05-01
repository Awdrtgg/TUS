import time

from ryu.tus.const import const

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
