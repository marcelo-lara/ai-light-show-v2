from api.intents.fixture.handlers import FIXTURE_HANDLERS
from api.intents.llm.handlers import LLM_HANDLERS
from api.intents.transport.handlers import TRANSPORT_HANDLERS


INTENT_HANDLERS = {
    "transport": TRANSPORT_HANDLERS,
    "fixture": FIXTURE_HANDLERS,
    "llm": LLM_HANDLERS,
}
