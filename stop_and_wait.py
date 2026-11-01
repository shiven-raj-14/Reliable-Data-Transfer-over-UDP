import socket, time
from packet import Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN
from rto import AdaptiveRTO

def send_stop_and_wait(data: bytes, sock: socket.socket, dest: tuple, channel, chunk_size=1024, rto_calc=None):
    if rto_calc is None:
        rto_calc = AdaptiveRTO()
    seq = 0
    total_retransmissions = 0
    
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        pkt = Packet(seq_num=seq, ack_num=0, flags=FLAG_DATA, payload=chunk)
        retransmitted = False
        
        while True:
            start_time = time.time()
            channel.transmit(sock, pkt.pack(), dest)
            sock.settimeout(rto_calc.rto)
            
            try:
                raw, _ = sock.recvfrom(2048)
                ack_pkt = Packet.unpack(raw)
                if ack_pkt and (ack_pkt.flags & FLAG_ACK) and ack_pkt.ack_num == seq:
                    rtt = time.time() - start_time
                    rto_calc.update(rtt, is_retransmission=retransmitted)
                    break
            except socket.timeout:
                retransmitted = True
                total_retransmissions += 1
                rto_calc.update(0, is_retransmission=True)
        seq += 1

    fin_pkt = Packet(seq_num=seq, ack_num=0, flags=FLAG_FIN)
    for _ in range(8):
        channel.transmit(sock, fin_pkt.pack(), dest)
        time.sleep(0.01)

    return total_retransmissions

def receive_stop_and_wait(sock: socket.socket, output_path: str):
    expected_seq = 0
    received_data = bytearray()
    
    while True:
        try:
            raw, sender_addr = sock.recvfrom(2048)
            pkt = Packet.unpack(raw)
            if not pkt:
                continue
            if pkt.flags & FLAG_FIN:
                ack = Packet(seq_num=0, ack_num=pkt.seq_num, flags=FLAG_ACK | FLAG_FIN)
                sock.sendto(ack.pack(), sender_addr)
                break
            if pkt.seq_num == expected_seq:
                received_data.extend(pkt.payload)
                ack = Packet(seq_num=0, ack_num=expected_seq, flags=FLAG_ACK)
                sock.sendto(ack.pack(), sender_addr)
                expected_seq += 1
            else:
                ack = Packet(seq_num=0, ack_num=pkt.seq_num, flags=FLAG_ACK)
                sock.sendto(ack.pack(), sender_addr)
        except socket.timeout:
            continue

    with open(output_path, 'wb') as f:
        f.write(received_data)