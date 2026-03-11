from api.intents.llm.actions.cancel import cancel
from api.intents.llm.actions.send_prompt import send_prompt


LLM_HANDLERS = {
    "llm.send_prompt": send_prompt,
    "llm.cancel": cancel,
}
