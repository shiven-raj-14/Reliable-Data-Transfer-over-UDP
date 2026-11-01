import struct

FLAG_DATA = 0x01
FLAG_ACK  = 0x02
FLAG_SYN  = 0x04
FLAG_FIN  = 0x08

class Packet:
    # Header Format: SeqNum (4B), AckNum (4B), Flags (1B), Checksum (2B), PayloadLen (2B)
    HEADER_FORMAT = "!IIBHH"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, seq_num: int, ack_num: int, flags: int, payload: bytes = b"", checksum: int = 0):
        self.seq_num = seq_num
        self.ack_num = ack_num
        self.flags = flags
        self.payload = payload
        self.checksum = checksum if checksum != 0 else self.calculate_checksum()

    def calculate_checksum(self) -> int:
        header_dummy = struct.pack(Packet.HEADER_FORMAT, self.seq_num, self.ack_num, self.flags, 0, len(self.payload))
        data = header_dummy + self.payload
        if len(data) % 2 != 0:
            data += b'\x00'
        
        checksum = 0
        for i in range(0, len(data), 2):
            word = (data[i] << 8) + data[i+1]
            checksum += word
            checksum = (checksum & 0xffff) + (checksum >> 16)
        return ~checksum & 0xffff

    def pack(self) -> bytes:
        header = struct.pack(Packet.HEADER_FORMAT, self.seq_num, self.ack_num, self.flags, self.checksum, len(self.payload))
        return header + self.payload

    @classmethod
    def unpack(cls, raw_bytes: bytes):
        if len(raw_bytes) < cls.HEADER_SIZE:
            return None
        seq_num, ack_num, flags, checksum, payload_len = struct.unpack(cls.HEADER_FORMAT, raw_bytes[:cls.HEADER_SIZE])
        payload = raw_bytes[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_len]
        pkt = cls(seq_num, ack_num, flags, payload, checksum=checksum)
        if pkt.calculate_checksum() != checksum:
            return None  # Corrupted packet dropped
        return pkt