from ryu.tus.const import const

class Transaction(object):
    # TODO 
    # everything...

    def __init__(self, tx_id):
        self.tx_id = tx_id
        self.state = const.READ
        self.read_set = [[]]
        self.write_set = [[]]
        self.barrier_count = 0

        self.conflict = []
        
    def read(self, dp, match, action):
        self.read_set[self.barrier_count].append(
            {
                'dp': dp,
                'match': match,
                'action': action,
            }
        )
    
    def write(self, key, value):
        self.write_set[self.barrier_count].append(
            {
                'dp': dp,
                'match': match,
                'action': action,
            }
        )
    
    def barrier(self):
        self.read_set.append([])
        self.write_set.append([])
        self.barrier_count += 1

    def execute(self):
        for phase in range(self.barrier_count):
            for ac_write in self.write_set[phase]:
                # TODO 
                pass
                #ac_write['dp'].send_msg()