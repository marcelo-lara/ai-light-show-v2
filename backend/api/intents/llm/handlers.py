from api.intents.llm.actions.cancel import cancel
from api.intents.llm.actions.clear_conversation import clear_conversation
from api.intents.llm.actions.confirm_action import confirm_action
from api.intents.llm.actions.reject_action import reject_action
from api.intents.llm.actions.send_prompt import send_prompt


LLM_HANDLERS = {
    "llm.send_prompt": send_prompt,
    "llm.cancel": cancel,
    "llm.clear_conversation": clear_conversation,
    "llm.confirm_action": confirm_action,
    "llm.reject_action": reject_action,
}
