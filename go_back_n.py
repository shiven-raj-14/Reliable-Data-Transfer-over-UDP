import socket, time, threading
from packet import Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN
from rto import AdaptiveRTO

def send_go_back_n(data: bytes, sock: socket.socket, dest: tuple, channel, N=8, chunk_size=1024, rto_calc=None):
    if rto_calc is None:
        rto_calc = AdaptiveRTO()
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    total_chunks = len(chunks)
    base = 0
    next_seq = 0
    total_retransmissions = 0
    lock = threading.Lock()
    timer_start = time.time()

    def listen_acks():
        nonlocal base, timer_start
        while base < total_chunks:
            try:
                raw, _ = sock.recvfrom(2048)
                ack_pkt = Packet.unpack(raw)
                if ack_pkt and (ack_pkt.flags & FLAG_ACK):
                    with lock:
                        if ack_pkt.ack_num >= base:
                            base = ack_pkt.ack_num + 1
                            timer_start = time.time()
            except Exception:
                pass

    threading.Thread(target=listen_acks, daemon=True).start()

    while base < total_chunks:
        with lock:
            while next_seq < base + N and next_seq < total_chunks:
                pkt = Packet(seq_num=next_seq, ack_num=0, flags=FLAG_DATA, payload=chunks[next_seq])
                channel.transmit(sock, pkt.pack(), dest)
                if base == next_seq:
                    timer_start = time.time()
                next_seq += 1

            if base < next_seq and (time.time() - timer_start) > rto_calc.rto:
                for seq in range(base, next_seq):
                    pkt = Packet(seq_num=seq, ack_num=0, flags=FLAG_DATA, payload=chunks[seq])
                    channel.transmit(sock, pkt.pack(), dest)
                    total_retransmissions += 1
                timer_start = time.time()
                rto_calc.update(0, is_retransmission=True)

        time.sleep(0.0002)

    fin_pkt = Packet(seq_num=total_chunks, ack_num=0, flags=FLAG_FIN)
    for _ in range(8):
        channel.transmit(sock, fin_pkt.pack(), dest)
        time.sleep(0.005)

    return total_retransmissions

def receive_go_back_n(sock: socket.socket, output_path: str):
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
                if expected_seq > 0:
                    ack = Packet(seq_num=0, ack_num=expected_seq - 1, flags=FLAG_ACK)
                    sock.sendto(ack.pack(), sender_addr)
        except socket.timeout:
            continue

    with open(output_path, 'wb') as f:
        f.write(received_data)