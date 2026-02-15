import asyncio
import socket
from pathlib import Path
from time import perf_counter
from typing import Iterable, Optional, Union

ARTNET_IP = "192.168.10.221"
ARTNET_PORT = 6454
ARTNET_UNIVERSE = 0
DMX_CHANNELS = 512
FPS = 60

UniverseLike = Union[bytes, bytearray, memoryview, Iterable[int]]

class ArtNetService:
    def __init__(self, debug: bool = False, debug_file: Optional[str] = None):
        self.dmx_universe: bytearray = bytearray(DMX_CHANNELS)
        self.last_send = 0.0
        self.last_packet: bytes = bytes(DMX_CHANNELS)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.debug = bool(debug)
        self.debug_file_path = Path(debug_file) if debug_file else None
        if self.debug_file_path is not None:
            self.debug_file_path.parent.mkdir(parents=True, exist_ok=True)

    async def start(self):
        self.running = True
        asyncio.create_task(self.send_loop())

    async def stop(self):
        self.running = False
        self.sock.close()

    async def update_universe(self, universe: UniverseLike):
        if isinstance(universe, memoryview):
            if len(universe) != DMX_CHANNELS:
                raise ValueError(f"universe must be {DMX_CHANNELS} bytes")
            self.dmx_universe[:] = universe
            return
        if isinstance(universe, bytes):
            if len(universe) != DMX_CHANNELS:
                raise ValueError(f"universe must be {DMX_CHANNELS} bytes")
            self.dmx_universe[:] = universe
            return
        if isinstance(universe, bytearray):
            if len(universe) != DMX_CHANNELS:
                raise ValueError(f"universe must be {DMX_CHANNELS} bytes")
            self.dmx_universe[:] = universe
            return

        # Fallback: iterable of ints
        vals = bytearray(DMX_CHANNELS)
        i = 0
        for v in universe:
            if i >= DMX_CHANNELS:
                break
            vals[i] = max(0, min(255, int(v)))
            i += 1
        self.dmx_universe[:] = vals

    async def send_loop(self):
        while self.running:
            now = perf_counter()
            if now - self.last_send >= 1.0 / FPS:
                await self.send_artnet()
                self.last_send = now
            await asyncio.sleep(0.01)  # small sleep to not hog CPU

    async def send_artnet(self):
        # Build packet
        packet = bytearray()
        packet.extend(b'Art-Net\x00')  # ID
        packet.extend((0x00, 0x50))  # OpCode: ArtDMX
        packet.extend((0x00, 0x0e))  # Protocol version
        packet.extend((0x00, 0x00))  # Sequence + Physical
        packet.extend((ARTNET_UNIVERSE & 0xFF, (ARTNET_UNIVERSE >> 8) & 0xFF))  # Universe
        packet.extend((0x02, 0x00))  # Data length = 512
        packet.extend(self.dmx_universe)

        current_packet = bytes(self.dmx_universe)
        if self.debug:
            await self._debug_dump(current_packet)

        try:
            self.sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))
        except Exception as e:
            print(f"Art-Net send error: {e}")

        self.last_packet = current_packet

    async def _debug_dump(self, universe_bytes: bytes):
        timestamp = perf_counter()
        dmx_hex = '.'.join(f"{value:02X}" for value in universe_bytes)
        line = f"[{timestamp:.3f}] artnet dmx {dmx_hex}\n"

        if self.debug_file_path is None:
            print(line, end="")
            return

        try:
            with self.debug_file_path.open("a", encoding="utf-8") as debug_file:
                debug_file.write(line)
        except Exception as e:
            print(f"Art-Net debug write error: {e}")

    async def set_channel(self, channel: int, value: int):
        if 1 <= channel <= DMX_CHANNELS and 0 <= value <= 255:
            self.dmx_universe[channel - 1] = value

    async def arm_fixture(self, fixture):
        # Send arm values
        for channel_name, value in fixture.arm.items():
            if channel_name in fixture.channels:
                channel_num = fixture.channels[channel_name]
                await self.set_channel(channel_num, value)

    async def blackout(self, send_once: bool = True) -> None:
        """Immediately set the entire DMX universe to zero and optionally send one Art-Net packet.

        This is intended to be called during shutdown to ensure fixtures go dark before sockets close.
        """
        # Zero the universe
        self.dmx_universe = bytearray(DMX_CHANNELS)
        # Send one packet immediately so lights receive the blackout
        if send_once:
            try:
                await self.send_artnet()
            except Exception as e:
                print(f"Art-Net blackout send error: {e}")