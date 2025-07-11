#!/usr/bin/env python
"""
DMX Canvas module for AI Light Show.

This module provides a canvas for storing and manipulating DMX state over time.
It represents a timeline of 512-byte DMX frames that can be painted with channel values
at specific timestamps.
"""
import numpy as np
from typing import Dict, Callable, Optional
import math


class DmxCanvas:
    """
    A canvas for storing and manipulating DMX state over time.
    
    The DmxCanvas represents a timeline of DMX universe states (512 channels),
    quantized at a specific frame rate. It allows painting values at specific timestamps
    and retrieving the complete DMX frame at any point in time.
    
    Attributes:
        fps (int): Frames per second for the timeline.
        duration (float): Total duration of the timeline in seconds.
        frame_duration (float): Duration of a single frame in seconds.
        num_frames (int): Total number of frames in the timeline.
        universe_size (int): Size of the DMX universe (512 channels).
        _timeline (Dict[float, bytes]): Internal storage mapping timestamps to DMX frames.
        _canvas (np.ndarray): NumPy array for efficient frame manipulation.
    """
    
    def __init__(self, fps: int = 44, duration: float = 300.0):
        """
        Initialize a new DMX canvas.
        
        Args:
            fps (int): Frames per second for the timeline. Defaults to 44.
            duration (float): Total duration of the timeline in seconds. Defaults to 300.0.
        """
        self.fps = fps
        self.duration = duration
        self.frame_duration = 1.0 / fps
        self.num_frames = math.ceil(duration * fps)
        self.universe_size = 512
        
        # Internal storage as NumPy array for performance
        self._canvas = np.zeros((self.num_frames, self.universe_size), dtype=np.uint8)
        
        # Timeline dictionary for final storage and export
        self._timeline = {}
    
    def _time_to_frame_index(self, timestamp: float) -> int:
        """
        Convert a timestamp to the nearest frame index.
        
        Args:
            timestamp (float): Time in seconds.
            
        Returns:
            int: The nearest frame index.
        """
        frame_index = round(timestamp * self.fps)
        return max(0, min(frame_index, self.num_frames - 1))
    
    def _frame_index_to_time(self, frame_index: int) -> float:
        """
        Convert a frame index to its timestamp.
        
        Args:
            frame_index (int): Index of the frame.
            
        Returns:
            float: Time in seconds, rounded to 4 decimal places.
        """
        return round(frame_index * self.frame_duration, 4)
    
    def paint_frame(self, timestamp: float, channel_values: Dict[int, int]) -> None:
        """
        Paint DMX channel values at a specific timestamp.
        
        Args:
            timestamp (float): Time in seconds where the values should be applied.
            channel_values (Dict[int, int]): Dictionary mapping channel numbers to values (0-255).
        """
        frame_index = self._time_to_frame_index(timestamp)
        
        # Apply the channel values to the frame
        for channel, value in channel_values.items():
            if 0 <= channel < self.universe_size:
                self._canvas[frame_index, channel] = min(255, max(0, value))
    
    def paint_channel(self, channel: int, start_time: float, duration: float,
                     value_fn: Callable[[float], int]) -> None:
        """
        Paint a single channel's values over a time range.
        
        Args:
            channel (int): DMX channel number (0-511)
            start_time (float): Start time in seconds
            duration (float): Duration in seconds
            value_fn (Callable[[float], int]): Function that takes time offset (0-1)
                and returns channel value (0-255)
        """
        if not 0 <= channel < self.universe_size:
            return
            
        start_frame = self._time_to_frame_index(start_time)
        end_frame = self._time_to_frame_index(start_time + duration)
        
        for frame_index in range(start_frame, end_frame + 1):
            frame_time = self._frame_index_to_time(frame_index)
            time_offset = (frame_time - start_time) / duration
            if 0 <= time_offset <= 1:
                self._canvas[frame_index, channel] = min(255, max(0, 
                    value_fn(time_offset)))

    def paint_range(self, start: float, end: float, 
                   channel_values_fn: Callable[[float], Dict[int, int]]) -> None:
        """
        Apply a function to paint channel values across a time range.
        
        Args:
            start (float): Start time in seconds.
            end (float): End time in seconds.
            channel_values_fn (Callable[[float], Dict[int, int]]): Function that takes a timestamp 
                and returns a dictionary of channel values.
        """
        start_frame = self._time_to_frame_index(start)
        end_frame = self._time_to_frame_index(end)
        
        for frame_index in range(start_frame, end_frame + 1):
            timestamp = self._frame_index_to_time(frame_index)
            channel_values = channel_values_fn(timestamp)
            
            # Apply the channel values to the frame
            for channel, value in channel_values.items():
                if 0 <= channel < self.universe_size:
                    self._canvas[frame_index, channel] = min(255, max(0, value))
    
    def get_frame(self, timestamp: float) -> bytes:
        """
        Get the DMX frame at the specified timestamp.
        
        Args:
            timestamp (float): Time in seconds.
            
        Returns:
            bytes: A 512-byte array representing the DMX universe state.
        """
        frame_index = self._time_to_frame_index(timestamp)
        return bytes(self._canvas[frame_index])
    
    def export(self) -> Dict[float, bytes]:
        """
        Export the complete DMX canvas.
        
        Returns:
            Dict[float, bytes]: Dictionary mapping timestamps to DMX frames.
        """
        # Convert the NumPy array to a timeline dictionary
        timeline = {}
        for frame_index in range(self.num_frames):
            timestamp = self._frame_index_to_time(frame_index)
            timeline[timestamp] = bytes(self._canvas[frame_index])
        
        return timeline


if __name__ == "__main__":
    # Example usage
    canvas = DmxCanvas(fps=30, duration=10.0)
    
    # Paint a single frame
    canvas.paint_frame(1.0, {10: 255, 11: 128, 12: 64})
    
    # Paint a range with a function
    def fade_in(t: float) -> Dict[int, int]:
        # Calculate value based on time (linear fade from 0 to 255)
        progress = (t - 2.0) / 3.0  # From t=2 to t=5, progress goes from 0 to 1
        value = int(255 * progress)
        return {20: value, 21: value, 22: value}
    
    canvas.paint_range(2.0, 5.0, fade_in)
    
    # Get a frame
    frame_at_3s = canvas.get_frame(3.0)
    print(f"Frame at 3.0s: {frame_at_3s[:30]}...")  # Show first 30 bytes
