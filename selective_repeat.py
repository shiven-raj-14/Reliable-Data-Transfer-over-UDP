import socket, time, threading
from packet import Packet, FLAG_DATA, FLAG_ACK, FLAG_FIN
from rto import AdaptiveRTO

def send_selective_repeat(data: bytes, sock: socket.socket, dest: tuple, channel, N=8, chunk_size=1024, rto_calc=None):
    if rto_calc is None:
        rto_calc = AdaptiveRTO()
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    total_chunks = len(chunks)
    acked = [False] * total_chunks
    send_times = {}
    base = 0
    total_retransmissions = 0
    lock = threading.Lock()

    def listen_acks():
        nonlocal base
        while base < total_chunks:
            try:
                raw, _ = sock.recvfrom(2048)
                ack_pkt = Packet.unpack(raw)
                if ack_pkt and (ack_pkt.flags & FLAG_ACK):
                    seq = ack_pkt.ack_num
                    with lock:
                        if seq < total_chunks:
                            acked[seq] = True
                            while base < total_chunks and acked[base]:
                                base += 1
            except Exception:
                pass

    threading.Thread(target=listen_acks, daemon=True).start()

    while base < total_chunks:
        with lock:
            now = time.time()
            for seq in range(base, min(base + N, total_chunks)):
                if not acked[seq]:
                    if seq not in send_times or (now - send_times[seq]) > rto_calc.rto:
                        if seq in send_times:
                            total_retransmissions += 1
                            rto_calc.update(0, is_retransmission=True)
                        send_times[seq] = now
                        pkt = Packet(seq_num=seq, ack_num=0, flags=FLAG_DATA, payload=chunks[seq])
                        channel.transmit(sock, pkt.pack(), dest)
        time.sleep(0.0002)

    fin_pkt = Packet(seq_num=total_chunks, ack_num=0, flags=FLAG_FIN)
    for _ in range(8):
        channel.transmit(sock, fin_pkt.pack(), dest)
        time.sleep(0.005)

    return total_retransmissions

def receive_selective_repeat(sock: socket.socket, output_path: str, N=8):
    base = 0
    buffer = {}
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

            seq = pkt.seq_num
            ack = Packet(seq_num=0, ack_num=seq, flags=FLAG_ACK)
            sock.sendto(ack.pack(), sender_addr)

            if base <= seq < base + N:
                buffer[seq] = pkt.payload
                while base in buffer:
                    received_data.extend(buffer.pop(base))
                    base += 1
        except socket.timeout:
            continue

    with open(output_path, 'wb') as f:
        f.write(received_data)