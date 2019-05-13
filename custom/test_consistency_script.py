import json

fp = open('nib.json', 'r')
data = json.load(fp)
fp.close()

l = [
    data['datapath=1, port=1, rx-pkts'],
    data['datapath=1, port=2, tx-pkts'],
    data['datapath=1, port=3, tx-pkts'],
    data['datapath=4, port=1, rx-pkts'],
    data['datapath=4, port=3, rx-pkts'],
    data['datapath=4, port=2, tx-pkts'],
]

fp = open('test12.csv', 'a+')
fp.write(str(l)[1:-1])
fp.write('\n')
fp.close()