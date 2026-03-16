from api.intents.chaser.actions.apply import apply_chaser
from api.intents.chaser.actions.list import list_chasers
from api.intents.chaser.actions.start import start_chaser
from api.intents.chaser.actions.stop import stop_chaser


CHASER_HANDLERS = {
    "chaser.apply": apply_chaser,
    "chaser.start": start_chaser,
    "chaser.stop": stop_chaser,
    "chaser.list": list_chasers,
}
