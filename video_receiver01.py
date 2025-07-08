import sys
import json
import socket
import select
import datagram_pb2

READ_FLAGS = select.POLLIN | select.POLLPRI
WRITE_FLAGS = select.POLLOUT
ERR_FLAGS = select.POLLERR | select.POLLHUP | select.POLLNVAL
READ_ERR_FLAGS = READ_FLAGS | ERR_FLAGS
ALL_FLAGS = READ_FLAGS | WRITE_FLAGS | ERR_FLAGS

class Receiver(object):
    def __init__(self, port):
        # UDP socket and poller
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 65536)
        self.sock.bind(('0.0.0.0', port))

        self.last_seq_num = -1
        self.received_packets = {}
        self.window_size = 100

        self.ack_count = 0
        self.sent_ack = -1

        self.poller = select.poll()
        self.poller.register(self.sock, ALL_FLAGS)

    def cleanup(self):
        self.sock.close()

    def construct_ack_from_data(self, serialized_data):
        """Construct a serialized ACK that acks a serialized datagram."""

        data = datagram_pb2.Data()
        data.ParseFromString(serialized_data)

        ack = datagram_pb2.Ack()
        ack.seq_num = data.seq_num
        ack.send_ts = data.send_ts
        ack.sent_bytes = data.sent_bytes
        ack.delivered_time = data.delivered_time
        ack.delivered = data.delivered
        ack.ack_bytes = len(serialized_data)

        return ack.SerializeToString()

    def handshake(self):
        print('[receiver] Start listening on port %d'%self.port)
        pass

    def run(self):
        self.sock.setblocking(1)  # blocking UDP socket

        while True:
            serialized_data, addr = self.sock.recvfrom(1600)
            data = datagram_pb2.Data()
            data.ParseFromString(serialized_data)

            # self.received_packets[data.seq_num] ={
            #     'send_ts':data.send_ts,
            #     'sent_bytes':data.sent_bytes,
            #     'delivered_time':data.delivered_time,
            #     'delivered':data.delivered,
            #     'payload':data.payload
            # }
            # ack.seq_num = data.seq_num
            # ack.send_ts = data.send_ts
            # ack.sent_bytes = data.sent_bytes
            # ack.delivered_time = data.delivered_time
            # ack.delivered = data.delivered
            # ack.ack_bytes = len(serialized_data)

            # if data.seq_num == self.last_seq_num+1:
            #     self.last_seq_num = data.seq_num
            #     sys.stderr.write("Receive-----Normal,seq_num=%d\n" % data.seq_num)
            # else:
            #     sys.stderr.write("Receive-----Repeated,seq_num=%d\n" % data.seq_num)

            if data.seq_num <= self.last_seq_num:
                sys.stderr.write("Receiver--old packet\n")
            # elif data.seq_num <= self.last_seq_num + self.window_size:
            else:
                self.received_packets[data.seq_num] ={
                'send_ts':data.send_ts,
                'sent_bytes':data.sent_bytes,
                'delivered_time':data.delivered_time,
                'delivered':data.delivered,
                'payload':data.payload
                }
                sys.stderr.write("Receiver--Buffer data_seq=%d\n" %data.seq_num)
            # else:
            #     sys.stderr.write("Receiver--Out of window%d\n" %data.seq_num)
            #     continue
            
            advanced = False
            while(self.last_seq_num +1) in self.received_packets:
                self.last_seq_num += 1
                self.received_packets.pop(self.last_seq_num)
                advanced = True

            ack = datagram_pb2.Ack()
            ack.seq_num = self.last_seq_num
            
            pkt_info = self.received_packets.get(self.last_seq_num,{
                'send_ts':data.send_ts,
                'sent_bytes':data.sent_bytes,
                'delivered_time':data.delivered_time,
                'delivered':data.delivered
            })
            
            ack.send_ts = pkt_info['send_ts']
            ack.sent_bytes = pkt_info['sent_bytes']
            ack.delivered_time = pkt_info['delivered_time']
            ack.delivered = pkt_info['delivered']
            ack.ack_bytes = len(serialized_data)

            if advanced:
                self.ack_count = 0
                self.sent_ack = ack.seq_num
                self.sock.sendto(ack.SerializeToString(), addr)
                sys.stderr.write("Receiver--ACK_sent seq=%d\n" %ack.seq_num)
            else:
                # if ack.seq_num == self.sent_ack and self.ack_count < 3:
                # if ack.seq_num == self.sent_ack:
                self.sock.sendto(ack.SerializeToString(), addr)
                self.ack_count += 1
                sys.stderr.write("Receiver--Repeated ACK for seq =%d\n" %ack.seq_num)
            
            # self.sock.sendto(ack.SerializeToString(), addr)
            # sys.stderr.write("Receiver--ACK seq=%d\n" %ack.seq_num)

            # ack = self.construct_ack_from_data(serialized_data)
            # if ack is not None:
            #     self.sock.sendto(ack, addr)
