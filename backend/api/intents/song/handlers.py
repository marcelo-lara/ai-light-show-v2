from api.intents.song.actions.list import list_songs
from api.intents.song.actions.load import load_song


SONG_HANDLERS = {
    "song.list": list_songs,
    "song.load": load_song,
}