from api.intents.transport.actions.jump_to_section import jump_to_section
from api.intents.transport.actions.jump_to_time import jump_to_time
from api.intents.transport.actions.pause import pause
from api.intents.transport.actions.play import play
from api.intents.transport.actions.stop import stop


TRANSPORT_HANDLERS = {
    "transport.play": play,
    "transport.pause": pause,
    "transport.stop": stop,
    "transport.jump_to_time": jump_to_time,
    "transport.jump_to_section": jump_to_section,
}
