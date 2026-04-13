from api.intents.song.actions.list import list_songs
from api.intents.song.actions.hints_create import create_human_hint
from api.intents.song.actions.hints_delete import delete_human_hint
from api.intents.song.actions.hints_update import update_human_hint
from api.intents.song.actions.load import load_song


SONG_HANDLERS = {
    "song.list": list_songs,
    "song.load": load_song,
    "song.hints.create": create_human_hint,
    "song.hints.update": update_human_hint,
    "song.hints.delete": delete_human_hint,
}