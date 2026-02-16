import asyncio
from typing import Any


async def run_startup_blue_wipe(state_manager: Any, artnet_service: Any) -> None:
    """Run the initial left-to-right blue wipe animation over parcans.

    Duration is exactly 1 second:
    - First half: turn ON from left to right
    - Second half: turn OFF from left to right
    """
    parcans_with_blue = sorted(
        [f for f in state_manager.fixtures if f.id.startswith("parcan") and "blue" in f.channels],
        key=lambda f: f.location.get("x", 0),
    )
    total_duration = 1.0
    if not parcans_with_blue:
        return

    n = len(parcans_with_blue)
    # Single fixture: keep lit for whole duration, then turn off.
    if n == 1:
        parcan = parcans_with_blue[0]
        channel_num = parcan.channels["blue"]
        await artnet_service.set_channel(channel_num, 255)
        await asyncio.sleep(total_duration)
        await artnet_service.set_channel(channel_num, 0)
        return

    phase = total_duration / 2.0
    spacing = phase / (n - 1)

    # Turn ON left-to-right over first half.
    for i, parcan in enumerate(parcans_with_blue):
        channel_num = parcan.channels["blue"]
        await artnet_service.set_channel(channel_num, 255)
        if i < n - 1:
            await asyncio.sleep(spacing)

    # Turn OFF left-to-right over second half.
    for i, parcan in enumerate(parcans_with_blue):
        channel_num = parcan.channels["blue"]
        await artnet_service.set_channel(channel_num, 0)
        if i < n - 1:
            await asyncio.sleep(spacing)
