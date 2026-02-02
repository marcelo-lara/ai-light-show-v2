import asyncio
import socket
from time import perf_counter
from typing import List

ARTNET_IP = "192.168.10.221"
ARTNET_PORT = 6454
ARTNET_UNIVERSE = 0
DMX_CHANNELS = 512
FPS = 60

class ArtNetService:
    def __init__(self):
        self.dmx_universe: List[int] = [0] * DMX_CHANNELS
        self.last_send = 0.0
        self.last_packet = [0] * DMX_CHANNELS
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False

    async def start(self):
        self.running = True
        asyncio.create_task(self.send_loop())

    async def stop(self):
        self.running = False
        self.sock.close()

    async def update_universe(self, universe: List[int]):
        self.dmx_universe = universe.copy()

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
        packet.extend(bytes(self.dmx_universe))

        # Only log if different from last packet
        if self.dmx_universe != self.last_packet:
            dmx_slice = self.dmx_universe[15:40]
            dmx_str = '.'.join(f"{v:02X}" for v in dmx_slice)
            print(f"[{perf_counter():.3f}] {dmx_str}")

        try:
            self.sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))
        except Exception as e:
            print(f"Art-Net send error: {e}")

        self.last_packet = self.dmx_universe.copy()

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
        self.dmx_universe = [0] * DMX_CHANNELS
        # Send one packet immediately so lights receive the blackout
        if send_once:
            try:
                await self.send_artnet()
            except Exception as e:
                print(f"Art-Net blackout send error: {e}")