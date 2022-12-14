import serial, time, sys
from collections import namedtuple
import json, argparse
from operator import attrgetter
import struct

DEBUG = 1
BF = {"01" : (0xff)/2,
      "09" : 10,
      "22" : 10
      }

def connect(dev="/dev/rfcomm0"):
    s = serial.Serial(port=dev, baudrate=115200, timeout=0)
    return s

def read_elm(dev):
    ret = ""
    while True:
        c = dev.read()
        ret += c
        if ret[-3:] == "\r\r>":
            if DEBUG: print >>sys.stderr, repr(ret)
            return ret.split('\r')[1:-2]

def write_elm(dev, msg):
    dat = msg + "\r"
    if DEBUG: print >>sys.stderr, repr(dat)
    dev.write(dat)

def send_recv(dev, msg):
    write_elm(dev, msg)
    return read_elm(dev)

def bits_2_pid(number):
    pids = []
    binstr = bin(number)[2:][::-1]
    blen = len(binstr)
    for idx, c in enumerate(binstr):
        print idx, c
        if c == "1":
            pids.append("%02x" % (idx))
    return pids

def get_avail():
    dev.write("0100\r")
    status_msg = read_elm(dev).split('\r')[2:-2]
    for val in status_msg:
        big = "".join(val.split()[3:])
        little = big[::-1]
        intb = int(big, 16)
        intln = int(little, 16)
        print bits_2_pid(intb)
        print bits_2_pid(intln)


def bt_main():
    dev = connect()
    msgs = {}

    # INIT
    init = ["ATZ", "ATSP0", "ATE1", "ATH1", "ATST00", "ATKW0"]
    for cmd in init:
        initreply = send_recv(dev, cmd)
        msgs.setdefault("init", []).append(initreply)

    # MAIN PACKETS
    for bmode, brange in BF.iteritems():
        for i in xrange(brange):
            cmd = bmode + "%02x" % i
            data = send_recv(dev, cmd)
            if "NO DATA" not in "".join(data):
                if "SEARCHING" in data[0]:
                    data = data[1:]
                parsed_pkts = parse_packets(data, cmd)
                msgs.setdefault("packets", []).extend(parsed_pkts)
    
    print_packets(msgs["packets"])
    with open(str(int(time.time())) + ".json", "w") as f:
        json.dump(msgs, f)

def print_packets(packets, fp=None):
    if not fp:
        f = None
    else:
        f = open(fp, "w")
    for idx, p in enumerate(packets):
        if not f:
            print p
        else:
            print >>f, p
    if f:
        f.close()
    return 

class Packet(namedtuple("Packet", ["hdr1", "hdr2", "mode", "command",
                                   "data", "raw", "cmd"])):
    
    def __str__(self):
        return "Packet:\n\tHeader 1: %x\n\tHeader 2: %x\n\tMode: %d\n\tCommand: %d\n\tData: %s\n\tRaw Data: %s\n\tCommand: %s" \
            % (self.hdr1, self.hdr2, self.mode, self.command, 
               self.parse_data(), self.raw, self.cmd)

    def parse_data(self):
        ret = ""
        data = eval(self.data)
        dlen = len(data)
        ilen = dlen/4
        iustr = "I" * ilen
        isstr = "i" * ilen
        hlen = dlen / 2
        hustr = "H" * hlen
        hsstr = "h" * hlen
        bustr = "B" * dlen
        bsstr = "b" * dlen
        endianess = ["<", ">"]
        vtypes = [(iustr, ilen, 4), (isstr, ilen, 4), (hustr, hlen, 2), 
                  (hsstr, hlen, 2), (bustr, dlen, 1), (bsstr, dlen, 1)]
        for (x, (y, ylen, yper)) in ((x, y) for x in endianess for y in vtypes):
            ret += "\n\t\tDlen: %d Format: %s: Data: %s" \
                % (dlen, x+y, struct.unpack(x+y, data[:ylen*yper]))
        return ret

def parse_packets(packets, cmdstr):
    ret = []
    for packet in packets:
        if packet == 'BUFFER FULL': continue
        data = packet.split()
        print data
        try:
            hdr1 = int(data[0], 16)
            hdr2 = int(data[1], 16)
            mode = int(data[2], 16) - 0x40        
            cmd = int(data[3], 16)
            pdata = "".join(map(lambda x: chr(int(x, 16)), data[4:]))
            raw = "".join(data)
            p = Packet(hdr1, hdr2, mode, cmd, repr(pdata), repr(raw), cmdstr)
            print p
            ret.append(p)
        except Exception as e:
            print "error with packet %s" % packet
    return ret

def from_file(file_dict):
    packets = []
    for p in file_dict["packets"]:
        if len(p) == 6:
            p.append("notrecorded")
        packets.append(Packet(*p))
    return packets

def file_main(files):
    if len(files) != 2:
        return
    for x, fname in enumerate(files):
        with open(fname) as f:
            val = from_file(json.load(f))
            '''
            val = sorted(val, key=attrgetter("data"))            
            val = sorted(val, key=attrgetter("command"))
            val = sorted(val, key=attrgetter("mode"))
            val = sorted(val, key=attrgetter("hdr2"))
            val = sorted(val, key=attrgetter("hdr1"))
            '''
            if x == 0:
                p1 = val
            elif x == 1:
                p2 = val
    diff(p1, p2)
    '''
    print_packets(p1, "p1")
    print_packets(p2, "p2")
    '''

def packets_to_cmds(packets):
    cmd_dict = {}
    for p in packets:
        cmd_dict.setdefault(p.command, set()).add(p)
    return cmd_dict

def get_modes(packets):
    modes = {}
    for p in packets:
        modes.setdefault(p.mode, set()).add(p)
    return modes

def diff(p1, p2):
    p1_modes = get_modes(p1)
    p2_modes = get_modes(p2)
    # Compare like modes to like modes
    # as data is not really compatible
    for mode in [0x01, 0x09, 0x22]:
        p1_mdata = p1_modes[mode] if mode in p1_modes else set([])
        p1_cdata = packets_to_cmds(p1_mdata)
        p2_mdata = p2_modes[mode] if mode in p2_modes else set([])
        p2_cdata = packets_to_cmds(p2_mdata)
        if mode == 0x01:
            diff_general = packet_diff_general(p1_cdata, p2_cdata)
            #print diff_general
        elif mode == 0x09:
            pass
        elif mode == 0x22:
            pass

def packet_diff_general(p1, p2):
    diffs = {}
    for cmd, p1_packets in p1.iteritems():
        if cmd in p2:
            p2_packets = p2[cmd]
            diff = p1_packets - p2_packets
            if diff:
                diffs[cmd] = (diff, len(diff))
                print "\n\nAt command %d ->" % cmd,
                print "First packets: %s" % p1_packets
                print "Second packets: %s" % p2_packets
                print "Difference: %s" % diff

def main():
    parser = argparse.ArgumentParser(description='Handle OBD data')
    parser.add_argument('-m', dest="mode", action="store",
                        help="mode", required=True, default=False)
    parser.add_argument('bar', nargs='*')
    args = parser.parse_args()
    
    if args.mode == "c":
        bt_main()
    elif args.mode == "l":
        file_main(args.bar)
    else:
        return

if __name__ == "__main__":
    main()

