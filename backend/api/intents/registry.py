from api.intents.chaser.handlers import CHASER_HANDLERS
from api.intents.cue.handlers import CUE_HANDLERS
from api.intents.fixture.handlers import FIXTURE_HANDLERS
from api.intents.llm.handlers import LLM_HANDLERS
from api.intents.transport.handlers import TRANSPORT_HANDLERS
from api.intents.poi.handlers import POI_HANDLERS


INTENT_HANDLERS = {
    "chaser": CHASER_HANDLERS,
    "cue": CUE_HANDLERS,
    "transport": TRANSPORT_HANDLERS,
    "fixture": FIXTURE_HANDLERS,
    "llm": LLM_HANDLERS,
    "poi": POI_HANDLERS,
}
