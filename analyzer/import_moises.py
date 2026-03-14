import json
import os
import sys

def import_moises(song_id):
    moises_chords_path = f"analyzer/meta/{song_id}/moises/chords.json"
    output_path = f"analyzer/meta/{song_id}/beats.json"

    if not os.path.exists(moises_chords_path):
        print(f"ERROR: {moises_chords_path} not found")
        return

    with open(moises_chords_path, 'r') as f:
        moises_chords = json.load(f)

    beats = []
    for entry in moises_chords:
        beat = {
            "time": entry["curr_beat_time"],
            "beat": entry["beat_num"],
            "bar": entry["bar_num"],
            "bass": entry["bass"] if entry["bass"] else None,
            "chord": entry["chord_basic_pop"] if entry["chord_basic_pop"] else None
        }
        beats.append(beat)

    with open(output_path, 'w') as f:
        json.dump(beats, f, indent=2)
    
    print(f"Successfully converted {len(beats)} chords to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_moises.py <song_id>")
    else:
        import_moises(sys.argv[1])
