from api.intents.poi.actions.create import create_poi
from api.intents.poi.actions.update import update_poi
from api.intents.poi.actions.delete import delete_poi
from api.intents.poi.actions.update_fixture_target import update_fixture_target

POI_HANDLERS = {
    "poi.create": create_poi,
    "poi.update": update_poi,
    "poi.delete": delete_poi,
    "poi.update_fixture_target": update_fixture_target,
}
