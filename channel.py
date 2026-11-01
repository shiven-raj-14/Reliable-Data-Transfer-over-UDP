import random
import time
import socket
import threading

class ChannelEmulator:
    def __init__(self, loss_rate=0.0, dup_rate=0.0, reorder_rate=0.0, corrupt_rate=0.0, delay_ms=10.0, jitter_ms=1.0, seed=42):
        self.loss_rate = loss_rate
        self.dup_rate = dup_rate
        self.reorder_rate = reorder_rate
        self.corrupt_rate = corrupt_rate
        self.delay_ms = delay_ms
        self.jitter_ms = jitter_ms
        self.rng = random.Random(seed)

    def _corrupt_bytes(self, raw_bytes: bytes) -> bytes:
        if len(raw_bytes) == 0:
            return raw_bytes
        byte_arr = bytearray(raw_bytes)
        idx = self.rng.randint(0, len(byte_arr) - 1)
        byte_arr[idx] ^= 0xFF
        return bytes(byte_arr)

    def transmit(self, sock: socket.socket, raw_bytes: bytes, dest_addr: tuple):
        if self.rng.random() < self.loss_rate:
            return  # Drop packet

        data_to_send = self._corrupt_bytes(raw_bytes) if self.rng.random() < self.corrupt_rate else raw_bytes

        jitter = self.rng.uniform(-self.jitter_ms, self.jitter_ms) if self.jitter_ms > 0 else 0
        delay_sec = max(0.001, (self.delay_ms + jitter) / 1000.0)

        def delayed_send(data):
            time.sleep(delay_sec)
            try:
                sock.sendto(data, dest_addr)
            except Exception:
                pass

        if self.rng.random() < self.reorder_rate:
            threading.Thread(target=delayed_send, args=(data_to_send,), daemon=True).start()
            time.sleep(0.002)
        else:
            threading.Thread(target=delayed_send, args=(data_to_send,), daemon=True).start()

        if self.rng.random() < self.dup_rate:
            threading.Thread(target=delayed_send, args=(data_to_send,), daemon=True).start()