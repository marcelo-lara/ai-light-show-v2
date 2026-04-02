from .actions.enqueue import enqueue_analyzer_item
from .actions.enqueue_full_artifact import enqueue_full_artifact_playlist
from .actions.execute import execute_analyzer_item
from .actions.execute_all import execute_all_analyzer_items
from .actions.remove import remove_analyzer_item
from .actions.remove_all import remove_all_analyzer_items


ANALYZER_HANDLERS = {
    "analyzer.enqueue": enqueue_analyzer_item,
    "analyzer.enqueue_full_artifact": enqueue_full_artifact_playlist,
    "analyzer.execute": execute_analyzer_item,
    "analyzer.execute_all": execute_all_analyzer_items,
    "analyzer.remove": remove_analyzer_item,
    "analyzer.remove_all": remove_all_analyzer_items,
}