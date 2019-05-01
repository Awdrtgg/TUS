from ryu.tus.const import const

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
    