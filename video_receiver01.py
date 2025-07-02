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
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('0.0.0.0', port))

        self.last_seq_num = -1
        self.received_packets = {}

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

            self.received_packets[data.seq_num] ={
                'send_ts':data.send_ts,
                'sent_bytes':data.sent_bytes,
                'delivered_time':data.delivered_time,
                'delivered':data.delivered,
                'payload':data.payload
            }

            ack = datagram_pb2.Ack()
            # ack.seq_num = data.seq_num
            # ack.send_ts = data.send_ts
            # ack.sent_bytes = data.sent_bytes
            # ack.delivered_time = data.delivered_time
            # ack.delivered = data.delivered
            # ack.ack_bytes = len(serialized_data)

            if data.seq_num == self.last_seq_num+1:
                self.last_seq_num = data.seq_num
                sys.stderr.write("Receive-----Normal,seq_num=%d\n" % data.seq_num)
            else:
                sys.stderr.write("Receive-----Repeated,seq_num=%d\n" % data.seq_num)

            
            ack.seq_num = self.last_seq_num
            ack.send_ts = self.received_packets[ack.seq_num]['send_ts']
            ack.sent_bytes = self.received_packets[ack.seq_num]['sent_bytes']
            ack.delivered_time = self.received_packets[ack.seq_num]['delivered_time']
            ack.delivered = self.received_packets[ack.seq_num]['delivered']
            ack.ack_bytes = len(serialized_data)
            
            self.sock.sendto(ack.SerializeToString(), addr)

            # ack = self.construct_ack_from_data(serialized_data)
            # if ack is not None:
            #     self.sock.sendto(ack, addr)
