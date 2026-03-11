from api.intents.fixture.actions.preview_effect import preview_effect
from api.intents.fixture.actions.set_arm import set_arm
from api.intents.fixture.actions.set_values import set_values
from api.intents.fixture.actions.stop_preview import stop_preview


FIXTURE_HANDLERS = {
    "fixture.set_arm": set_arm,
    "fixture.set_values": set_values,
    "fixture.preview_effect": preview_effect,
    "fixture.stop_preview": stop_preview,
}
