import serial, time, sys
from collections import namedtuple
import json
from operator import attrgetter



class Packet(namedtuple("Packet", ["hdr1", "hdr2", "mode", "command", "data", "raw"])):
    
    def __str__(self):
        return "Packet:\n\tHeader 1: %x\n\tHeader 2: %x\n\tMode: %d\n\tCommand: %d\n\tData: %s" % (self.hdr1, self.hdr2, self.mode, self.command, self.data)
        
def parse_packets(packets, modal):
    ret = []
    for packet in packets:
        if packet == 'BUFFER FULL' or packet == '': continue
        data = packet.split()
        print data
        print modal
        if modal == "a":
            data = ["00", "00"] + data
        hdr1 = int(data[0], 16)
        hdr2 = int(data[1], 16)
        mode = int(data[2], 16) - 0x40        
        cmd = int(data[3], 16)
        pdata = "".join(map(lambda x: chr(int(x, 16)), data[4:]))
        raw = "".join(data)
        p = Packet(hdr1, hdr2, mode, cmd, repr(pdata), repr(raw))
        print p
        ret.append(p)
    return ret

def parse(raw_obd, mode):
    msgs = {}
    init = ["ATZ", "ATSP0", "ATE1", "ATH1", "ATST00","ATH", "AT"]
    with open(raw_obd, 'Urb') as inputFile:
       for row in inputFile:
           row = eval(row)
           cmdpkt = False
           #cmd packets 
           for cmd in init:
               if cmd in row:
                    msgs.setdefault("init", []).append(row[1:-1])
                    cmdpkt = True 
                    break

           if cmdpkt == True:
               continue

           row = row.split('\r')[1:-1]
           #main packets
           if "SEARCHING" in row[0]:
               row = row[1:]
           print "Row", row
           parsed_pkts = parse_packets(row, mode)
           msgs.setdefault("packets", []).extend(parsed_pkts)


    with open(raw_obd+'_parsed','w') as outputFile:
        json.dump(msgs, outputFile)

def main():
    parse(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
    
