from api.intents.analyzer.actions.enqueue import enqueue_analyzer_item
from api.intents.analyzer.actions.execute import execute_analyzer_item
from api.intents.analyzer.actions.execute_all import execute_all_analyzer_items
from api.intents.analyzer.actions.remove import remove_analyzer_item
from api.intents.analyzer.actions.remove_all import remove_all_analyzer_items


ANALYZER_HANDLERS = {
    "analyzer.enqueue": enqueue_analyzer_item,
    "analyzer.execute": execute_analyzer_item,
    "analyzer.execute_all": execute_all_analyzer_items,
    "analyzer.remove": remove_analyzer_item,
    "analyzer.remove_all": remove_all_analyzer_items,
}