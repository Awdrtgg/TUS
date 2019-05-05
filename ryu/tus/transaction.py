from ryu.tus.const import const


def intersect_set(set1, set2):
    # TODO
    # complete __equal__ for OFPMatch
    set1_flat = [y for x in set1 for y in x]
    set2_flat = [y for x in set2 for y in x]
    res = []
    for s1 in set1_flat:
        for s2 in set2_flat:
            if s1['dp'].id == s2['dp'].id:
            #if s1 == s2:
                res.append(s1)
    return res


class Transaction(object):
    # TODO 
    # everything...

    def __init__(self, tx_id):
        self.tx_id = tx_id
        self.state = const.READ
        self.read_set = {}
        self.write_set = [[]]
        self.barrier_set = []

        self.conflict = []
        
    def read(self, key, value):
        self.read_set[key] = value
    
    def write(self, dp, match, action):
        self.write_set[self.barrier_count].append(
            {
                'dp': dp,
                'match': match,
                'action': action,
            }
        )
    
    def barrier(self, dp):
        self.read_set.append([])
        self.write_set.append([])
        self.barrier_set.append(dp)

    def execute(self):
        for phase in range(len(self.barrier_set)):
            for ac_write in self.write_set[phase]:
                # TODO 
                # OFP v1.2
                dp =  ac_write['dp']
                ofp_parser = dp.ofproto_parser
                if ac_write['action']['name'] == 'OFPFlowMod':
                    req = ofp_parser.OFPFlowMod(
                        dp, 
                        match=ac_write['match'], 
                        **ac_write['action']['kwargs'], 
                    )
                    ac_write['dp'].send_msg(req)
                elif ac_write['action']['name'] == 'OFPPortMod':
                    req = ofp_parser.OFPPortMod(
                        dp, 
                        **ac_write['action']['kwargs'],
                    )
                elif ac_write['action']['name'] == 'OFPPacketOut':
                    req = ofp_parser.OFPPacketOut(
                        dp, 
                        **ac_write['action']['kwargs']
                    )
            
            dp = self.barrier_set[phase]
            ofp_parser = dp.ofproto_parser
            req = ofp_parser.OFPBarrierRequest(dp)
            dp.send_msg(req)
