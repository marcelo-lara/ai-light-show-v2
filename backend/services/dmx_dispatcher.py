
from time import perf_counter
import socket

# --- DMX Constants ---
DMX_CHANNELS = 512
FPS = 60
ARTNET_PORT = 6454
ARTNET_IP = "192.168.1.221" # real 192.168.1.221
ARTNET_UNIVERSE = 0

# --- DMX State ---
dmx_universe = [0] * DMX_CHANNELS
def get_universe():
    return dmx_universe.copy()


# --- DMX Controller Functions ---
DMX_BLACKOUT =  [0] * DMX_CHANNELS

def blackout():
    global dmx_universe
    dmx_universe = DMX_BLACKOUT.copy()
    send_artnet()
    print("🔴 Blackout sent to DMX universe")

def set_channel(ch: int, val: int) -> bool:
    if 0 <= ch < DMX_CHANNELS and 0 <= val <= 255:
        dmx_universe[ch-1] = val
        return True
    send_artnet()
    return False

# --- Send ArtNet packet ---
last_artnet_send = 0
def send_artnet(_dmx_universe=None, debug=False):
    global last_artnet_send, last_packet, dmx_universe

    if _dmx_universe is not None:
        dmx_universe = _dmx_universe

    # Limit sending rate to 60 FPS
    now = perf_counter()
    if now - last_artnet_send < (1.0 / FPS):
        return
    last_artnet_send = now

    # Full 512-byte DMX data
    full_data = dmx_universe[:DMX_CHANNELS] + [0] * (DMX_CHANNELS - len(dmx_universe))
    packet = bytearray()
    packet.extend(b'Art-Net\x00')                          # ID
    packet.extend((0x00, 0x50))                            # OpCode: ArtDMX
    packet.extend((0x00, 0x0e))                            # Protocol version
    packet.extend((0x00, 0x00))                            # Sequence + Physical
    packet.extend((ARTNET_UNIVERSE & 0xFF, (ARTNET_UNIVERSE >> 8) & 0xFF))  # Universe
    packet.extend((0x02, 0x00))                            # Data length = 512
    packet.extend(bytes(full_data))
    
    last_packet = full_data.copy()

    # Debug output
    if debug:
      dmx_slice = dmx_universe[15:40]
      dmx_str = '.'.join(f"{v:03d}" for v in dmx_slice)
      print(f"[{now:.3f}] {dmx_str}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))
        sock.close()
    except Exception as e:
        print(f"❌ Art-Net send error: {e}")