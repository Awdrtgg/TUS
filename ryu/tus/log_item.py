import time
import json

from ryu.tus.const import const

class LogItem():
    # TODO
    # match & action
    def __init__(self, timestamp=None, tx_id=None, tx_state=None, 
                 dp=None, match=None, action=None, stat=None, 
                 volatile=False, rw='r', barrier=False, dpset=None):
        self.timestamp = timestamp
        self.tx_id = tx_id
        self.tx_state = tx_state
        self.dp = dp
        self.match = match
        self.action = action
        self.stat = stat
        self.volatile = volatile
        self.rw = rw
        self.barrier = barrier
        self.dpset = dpset

    def from_line(self, line):
        properties = [l.strip() for l in line.split(const.DIV)]
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
            self.tx_state = const.READ
            if properties[2] == 'read':
                self.rw = 'r'
            elif properties[2] == 'write':
                self.rw = 'w'

            temp_dp = json.loads(properties[3])
            print('property[3]: ', properties[3])
            print('temp_dp: ', temp_dp)
            self.dp = self.dpset.get(int(temp_dp['id']))
            if tuple(temp_dp['address']) != self.dp.address:
                print(tuple(temp_dp['address']), self.dp.address)
                print('Fatal Error: get wrong datapath!')
            
            self.match = self.dp.ofproto_parser.OFPMatch(json.loads(properties[4]))
            # TODO
            self.action = None
            self.stat = None
        
        return self

    def __str__(self):
        res = ''
        if self.tx_id == None:
            return res

        res += time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp)) + const.DIV
        res += str(self.tx_id) + const.DIV
        if self.barrier:
            res += 'BARRIER'
        elif self.tx_state == const.READ:
            if self.match == None:
                res += 'START'
            else:
                if self.rw == 'r':
                    res += 'read'
                elif self.rw == 'w':
                    res += 'write'
                res += const.DIV
                res += str(json.dumps({'id': self.dp.id, 'address': self.dp.address}))
                res += const.DIV
                res += str(json.dumps(self.match.to_jsondict()))
                res += const.DIV
                # TODO: actions
                res += str(self.action)
                
        elif self.tx_state == const.VALIDATION:
            res += 'VALIDATION' + const.DIV
            if self.volatile:
                res += 'VOLATILE'
            else:
                res += 'PERSISTENT'
        elif self.tx_state == const.WRITE:
            res += 'WRITE'
        elif self.tx_state == const.INACTIVE:
            res += 'INACTIVE'

        return res
