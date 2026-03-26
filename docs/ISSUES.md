## LLM-01: Confirmation keeps looping requesting confirmation.
user > clear the entire cue
history >
Thinking
Calling local model
Resolving tool calls
Applying action...
Awaiting confirmation

user > confirm
Applying propose_cue_clear_range
Thinking
Calling local model
Resolving tool calls
Confirm cue clear
Remove cue items from 0.000s to 0.000s.

user > Confirm
Awaiting confirmation

## LLM-02: Clear the entire cue
intended result: all items on the cue sheet are removed.
actual result: a range from 0 to 0 is removed

