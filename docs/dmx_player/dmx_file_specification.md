## DMX File Specification (.dmx)

The file name must be explicit: {song_name}.{show_name}.dmx


The file uses a Little-Endian binary format composed of a fixed 32-byte header followed by sequential frame records.

### 1 Global Header (32 Bytes)
| Offset | Size | Type   | Description |
| :---   | :--- | :---   | :--- |
| 0      | 4    | char   | Magic Number: `DMXP` |
| 4      | 2    | uint16 | Version: `1` |
| 6      | 2    | uint16 | Universe Count: `1` |
| 8      | 4    | uint32 | Total Frames in file |
| 12     | 4    | uint32 | Expected Frame Rate (e.g., `50` for 20ms intervals) |
| 16     | 16   | -      | Reserved for future metadata (Padding) |

### 2 Frame Record Structure
Each frame record is exactly **516 bytes**.

| Field     | Size | Type   | Description |
| :---      | :--- | :---   | :--- |
| Timestamp | 4    | uint32 | Milliseconds from show start |
| DMX Data  | 512  | uint8  | Raw DMX channel values (0-255) |
