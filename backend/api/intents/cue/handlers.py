from api.intents.cue.actions.add import add_cue
from api.intents.cue.actions.delete import delete_cue
from api.intents.cue.actions.update import update_cue


CUE_HANDLERS = {
    "cue.add": add_cue,
    "cue.update": update_cue,
    "cue.delete": delete_cue,
}
