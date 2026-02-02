'''
USE THIS FILE AS REFERENCE ONLY
'''
from time import perf_counter
from typing import Optional, Dict, Any
import socket

# --- DMX Constants ---
DMX_CHANNELS = 512
FPS = 60
ARTNET_PORT = 6454
ARTNET_IP = "192.168.10.221" # real 192.168.10.221
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

def get_channel_value(ch: int) -> int:
    if 0 <= ch < DMX_CHANNELS:
        return dmx_universe[ch-1]
    return 0

def get_channels_values(from_ch: int, to_ch: int) -> Dict[int, int]:
    """
    Get values for a range of channels.
    Args:
        from_ch (int): Start channel (1-based).
        to_ch (int): End channel (1-based).
    Returns:
        Dict[int, int]: Dictionary of channel values.
    """
    return {ch: dmx_universe[ch-1] for ch in range(from_ch, to_ch + 1) if 0 < ch <= DMX_CHANNELS}

# --- Send ArtNet packet ---
last_artnet_send = 0
last_packet = [0] * DMX_CHANNELS

def send_artnet(_dmx_universe=None, current_time=None, debug=False):
    """
    Send ArtNet packet with DMX data.
    
    Args:
        _dmx_universe: Can be bytes, list, or None. If None, uses global dmx_universe.
        debug: Whether to print debug output.
    """
    global last_artnet_send, last_packet, dmx_universe

    # Handle different input types
    if _dmx_universe is not None:
        if isinstance(_dmx_universe, bytes):
            # Convert bytes to list for processing
            dmx_data = list(_dmx_universe)
        elif isinstance(_dmx_universe, (list, tuple)):
            # Use list/tuple directly
            dmx_data = list(_dmx_universe)
        else:
            raise TypeError(f"_dmx_universe must be bytes, list, or None. Got {type(_dmx_universe)}")
    else:
        # Use global dmx_universe
        dmx_data = dmx_universe

    # Limit sending rate to 60 FPS
    now = perf_counter()
    if now - last_artnet_send < (1.0 / FPS):
        return
    last_artnet_send = now

    # Ensure we have exactly 512 bytes of DMX data
    if len(dmx_data) < DMX_CHANNELS:
        # Pad with zeros if data is shorter than 512
        full_data = dmx_data + [0] * (DMX_CHANNELS - len(dmx_data))
    else:
        # Truncate if data is longer than 512
        full_data = dmx_data[:DMX_CHANNELS]

    # Build ArtNet packet
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
    debug =True  # Always debug for testing
    if debug:
        _time = now if current_time is None else current_time
        dmx_slice = full_data[15:40]  # Use full_data instead of dmx_universe
        dmx_str = '.'.join(f"{v:03d}" for v in dmx_slice)
        print(f"[{_time:.3f}] {dmx_str}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))
        sock.close()
    except Exception as e:
        print(f"❌ Art-Net send error: {e}")