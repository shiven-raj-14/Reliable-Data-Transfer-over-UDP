import socket, time, os, threading
import matplotlib.pyplot as plt
from channel import ChannelEmulator
from integrity import FileIntegrity
from stop_and_wait import send_stop_and_wait, receive_stop_and_wait
from go_back_n import send_go_back_n, receive_go_back_n
from selective_repeat import send_selective_repeat, receive_selective_repeat

TEST_FILE = "test_input.bin"
OUTPUT_FILE = "test_output.bin"
PAYLOAD_SIZE = 20 * 1024

def setup_test_file():
    data = os.urandom(PAYLOAD_SIZE)
    with open(TEST_FILE, 'wb') as f:
        f.write(data)
    return data

def plot_1_goodput_vs_loss(data):
    print("\n--- Running Plot 1: Goodput vs Loss Rate ---")
    loss_rates = [0.0, 0.05, 0.10, 0.15, 0.20]
    results = {'Selective Repeat': [], 'Go-Back-N': [], 'Stop-and-Wait': []}

    for loss in loss_rates:
        for proto, send_fn, recv_fn in [
            ('Selective Repeat', send_selective_repeat, receive_selective_repeat),
            ('Go-Back-N', send_go_back_n, receive_go_back_n),
            ('Stop-and-Wait', send_stop_and_wait, receive_stop_and_wait)
        ]:
            print(f"  [Running] Protocol: {proto:<16} | Packet Loss: {int(loss*100)}%")
            rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            rx_sock.bind(('127.0.0.1', 9999))
            rx_sock.settimeout(1.0)

            tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tx_sock.settimeout(1.0)
            channel = ChannelEmulator(loss_rate=loss, delay_ms=10.0, seed=42)

            recv_thread = threading.Thread(target=recv_fn, args=(rx_sock, OUTPUT_FILE))
            recv_thread.start()

            start_t = time.time()
            if proto == 'Stop-and-Wait':
                send_fn(data, tx_sock, ('127.0.0.1', 9999), channel)
            else:
                send_fn(data, tx_sock, ('127.0.0.1', 9999), channel, N=8)
            recv_thread.join(timeout=5.0)
            duration = max(0.001, time.time() - start_t)

            goodput = len(data) / duration
            results[proto].append(goodput)

            rx_sock.close()
            tx_sock.close()
            time.sleep(0.05)

    plt.figure(figsize=(8, 5))
    for proto, goodputs in results.items():
        plt.plot([l * 100 for l in loss_rates], goodputs, marker='o', label=proto)
    plt.title("Goodput vs Packet Loss Rate")
    plt.xlabel("Packet Loss Rate (%)")
    plt.ylabel("Goodput (Bytes/sec)")
    plt.grid(True)
    plt.legend()
    plt.savefig("goodput_vs_loss.png")
    print("Saved: goodput_vs_loss.png")

def plot_2_goodput_vs_window(data):
    print("\n--- Running Plot 2: Goodput vs Window Size ---")
    window_sizes = [2, 4, 8, 16]
    results = {'Selective Repeat': [], 'Go-Back-N': []}

    for w in window_sizes:
        for proto, send_fn, recv_fn in [
            ('Selective Repeat', send_selective_repeat, receive_selective_repeat),
            ('Go-Back-N', send_go_back_n, receive_go_back_n)
        ]:
            print(f"  [Running] Protocol: {proto:<16} | Window Size N: {w}")
            rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            rx_sock.bind(('127.0.0.1', 9999))
            rx_sock.settimeout(1.0)

            tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tx_sock.settimeout(1.0)
            channel = ChannelEmulator(loss_rate=0.05, delay_ms=10.0, seed=42)

            recv_thread = threading.Thread(target=recv_fn, args=(rx_sock, OUTPUT_FILE, w)) if proto == 'Selective Repeat' else threading.Thread(target=recv_fn, args=(rx_sock, OUTPUT_FILE))
            recv_thread.start()

            start_t = time.time()
            send_fn(data, tx_sock, ('127.0.0.1', 9999), channel, N=w)
            recv_thread.join(timeout=5.0)
            duration = max(0.001, time.time() - start_t)

            goodput = len(data) / duration
            results[proto].append(goodput)

            rx_sock.close()
            tx_sock.close()
            time.sleep(0.05)

    plt.figure(figsize=(8, 5))
    for proto, goodputs in results.items():
        plt.plot(window_sizes, goodputs, marker='s', label=proto)
    plt.title("Goodput vs Window Size (at 5% Loss Rate)")
    plt.xlabel("Window Size (N)")
    plt.ylabel("Goodput (Bytes/sec)")
    plt.grid(True)
    plt.legend()
    plt.savefig("goodput_vs_window.png")
    print("Saved: goodput_vs_window.png")

def plot_3_retransmissions_vs_reorder(data):
    print("\n--- Running Plot 3: Retransmissions vs Reordering Probability ---")
    reorder_rates = [0.0, 0.05, 0.10, 0.15, 0.20]
    results = {'Go-Back-N': [], 'Selective Repeat': []}

    for r in reorder_rates:
        for proto, send_fn, recv_fn in [
            ('Go-Back-N', send_go_back_n, receive_go_back_n),
            ('Selective Repeat', send_selective_repeat, receive_selective_repeat)
        ]:
            print(f"  [Running] Protocol: {proto:<16} | Reorder Rate: {int(r*100)}%")
            rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            rx_sock.bind(('127.0.0.1', 9999))
            rx_sock.settimeout(1.0)

            tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tx_sock.settimeout(1.0)
            channel = ChannelEmulator(reorder_rate=r, delay_ms=10.0, seed=42)

            recv_thread = threading.Thread(target=recv_fn, args=(rx_sock, OUTPUT_FILE))
            recv_thread.start()

            retrans = send_fn(data, tx_sock, ('127.0.0.1', 9999), channel, N=8)
            recv_thread.join(timeout=5.0)
            results[proto].append(retrans)

            rx_sock.close()
            tx_sock.close()
            time.sleep(0.05)

    plt.figure(figsize=(8, 5))
    for proto, counts in results.items():
        plt.plot([r * 100 for r in reorder_rates], counts, marker='^', label=proto)
    plt.title("Retransmission Count vs Reordering Probability")
    plt.xlabel("Reordering Probability (%)")
    plt.ylabel("Total Retransmissions")
    plt.grid(True)
    plt.legend()
    plt.savefig("retransmissions_vs_reordering.png")
    print("Saved: retransmissions_vs_reordering.png")

if __name__ == "__main__":
    data = setup_test_file()
    plot_1_goodput_vs_loss(data)
    plot_2_goodput_vs_window(data)
    plot_3_retransmissions_vs_reorder(data)
    print("\nAll experiment benchmarks completed successfully!")