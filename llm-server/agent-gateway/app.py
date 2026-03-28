import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import httpx
import orjson
from fastmcp import Client
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from config import LLM_BASE_URL, MCP_BASE_URL, MCP_TOOL_MAP, TOOLS
from fast_path.router import _run_stream_fast_path
from interpretation.resolution import try_section_timing_interpretation
from llm_client import _chunk_text, _llm_complete
from gateway_mcp.client import call_mcp
from gateway_models import ChatRequest
from prompt.factual_answers import _build_fixtures_at_bar_answer_messages, _build_left_fixtures_answer_messages, _build_loudness_answer_messages, _build_first_effect_answer_messages
from prompt.guidance import _inject_query_guidance
from prompt.instructions import TOOL_OUTPUT_SYSTEM_MESSAGE
from prompt.lookup_answers import _build_chord_answer_messages, _build_cursor_answer_messages, _build_section_answer_messages, _is_section_timing_question
from rendering.results import _render_tool_result

log = logging.getLogger("agent-gateway")
logging.basicConfig(level=logging.INFO)

app = FastAPI()


async def _event_stream(req: ChatRequest):
    request_messages = _inject_query_guidance(req.messages)
    payload = {"model": req.model or "local", "messages": request_messages, "temperature": req.temperature if req.temperature is not None else 0.2, "tools": TOOLS, "tool_choice": req.tool_choice if req.tool_choice is not None else "auto"}
    async with httpx.AsyncClient(timeout=240.0) as client:
        yield f"data: {orjson.dumps({'type': 'status', 'phase': 'thinking', 'label': 'Thinking'}).decode('utf-8')}\n\n"
        fast_path = await _run_stream_fast_path(request_messages)
        if fast_path is not None:
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_tool_calls', 'label': 'Resolving tool calls'}).decode('utf-8')}\n\n"
            for tool_name in fast_path.get("used_tools") or []:
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'executing_tool', 'label': f'Executing {MCP_TOOL_MAP.get(tool_name, tool_name)}', 'tool_name': tool_name}).decode('utf-8')}\n\n"
            if fast_path.get("proposal") is not None:
                yield f"data: {orjson.dumps(fast_path['proposal']).decode('utf-8')}\n\n"
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_confirmation', 'label': 'Awaiting confirmation'}).decode('utf-8')}\n\n"
                yield "data: [DONE]\n\n"
                return
            answer_text = str(fast_path.get("answer_text") or "")
            if answer_text:
                for chunk in _chunk_text(answer_text):
                    if chunk:
                        yield f"data: {orjson.dumps({'type': 'delta', 'delta': chunk}).decode('utf-8')}\n\n"
                yield f"data: {orjson.dumps({'type': 'done', 'finish_reason': 'stop'}).decode('utf-8')}\n\n"
                yield "data: [DONE]\n\n"
                return
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'calling_model', 'label': 'Calling local model'}).decode('utf-8')}\n\n"
            data = await _llm_complete(client, {**payload, 'messages': fast_path.get('answer_messages') or [], 'tools': [], 'tool_choice': 'none'})
            for chunk in _chunk_text(str(data['choices'][0]['message'].get('content') or '')):
                if chunk:
                    yield f"data: {orjson.dumps({'type': 'delta', 'delta': chunk}).decode('utf-8')}\n\n"
            yield f"data: {orjson.dumps({'type': 'done', 'finish_reason': data['choices'][0].get('finish_reason', 'stop')}).decode('utf-8')}\n\n"
            yield "data: [DONE]\n\n"
            return
        interpreted = await try_section_timing_interpretation(request_messages, client, payload["model"], _llm_complete, call_mcp)
        if interpreted is not None:
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_tool_calls', 'label': 'Resolving tool calls'}).decode('utf-8')}\n\n"
            for tool_name in interpreted.get("used_tools") or []:
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'executing_tool', 'label': f'Executing {MCP_TOOL_MAP.get(tool_name, tool_name)}', 'tool_name': tool_name}).decode('utf-8')}\n\n"
            if interpreted.get("error") is not None:
                error = dict(interpreted.get("error") or {})
                yield f"data: {orjson.dumps({'type': 'error', 'code': error.get('code', 'gateway_error'), 'detail': error.get('detail', 'Assistant request failed.'), 'retryable': bool(error.get('retryable', True))}).decode('utf-8')}\n\n"
                yield "data: [DONE]\n\n"
                return
            for chunk in _chunk_text(str(interpreted.get('answer_text') or '')):
                if chunk:
                    yield f"data: {orjson.dumps({'type': 'delta', 'delta': chunk}).decode('utf-8')}\n\n"
            yield f"data: {orjson.dumps({'type': 'done', 'finish_reason': 'stop'}).decode('utf-8')}\n\n"
            yield "data: [DONE]\n\n"
            return
        messages: List[Dict[str, Any]] = list(request_messages)
        while True:
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'calling_model', 'label': 'Calling local model'}).decode('utf-8')}\n\n"
            data = await _llm_complete(client, {**payload, 'messages': messages})
            msg = data['choices'][0]['message']
            tool_calls = msg.get('tool_calls') or []
            if not tool_calls:
                for chunk in _chunk_text(str(msg.get('content') or '')):
                    if chunk:
                        yield f"data: {orjson.dumps({'type': 'delta', 'delta': chunk}).decode('utf-8')}\n\n"
                yield f"data: {orjson.dumps({'type': 'done', 'finish_reason': data['choices'][0].get('finish_reason', 'stop')}).decode('utf-8')}\n\n"
                break
            messages = messages + [msg]
            yield f"data: {orjson.dumps({'type': 'status', 'phase': 'awaiting_tool_calls', 'label': 'Resolving tool calls'}).decode('utf-8')}\n\n"
            tool_messages = []
            section_lookup_result = None
            chord_lookup_result = None
            cursor_lookup_result = None
            write_proposal = None
            for tc in tool_calls:
                tool_name = tc['function']['name']
                args = json.loads(tc['function'].get('arguments', '{}')) if isinstance(tc['function'].get('arguments', '{}'), str) else tc['function'].get('arguments', {})
                if tool_name.startswith('propose_'):
                    from fast_path.proposals import _proposal_for_tool

                    write_proposal = _proposal_for_tool(tool_name, args)
                    break
                yield f"data: {orjson.dumps({'type': 'status', 'phase': 'executing_tool', 'label': f'Executing {MCP_TOOL_MAP.get(tool_name, tool_name)}', 'tool_name': tool_name}).decode('utf-8')}\n\n"
                result = await call_mcp(tool_name, args)
                if tool_name == 'mcp_find_section':
                    section_lookup_result = result
                if tool_name == 'mcp_find_chord':
                    chord_lookup_result = result
                if tool_name == 'mcp_read_cursor':
                    cursor_lookup_result = result
                tool_messages.append({'role': 'tool', 'tool_call_id': tc['id'], 'content': _render_tool_result(tool_name, result)})
            if write_proposal is not None:
                yield f"data: {orjson.dumps(write_proposal).decode('utf-8')}\n\n"
                break
            if section_lookup_result is not None and _is_section_timing_question(messages):
                messages = _build_section_answer_messages(messages, section_lookup_result)
                continue
            if chord_lookup_result is not None:
                messages = _build_chord_answer_messages(messages, chord_lookup_result)
                continue
            if cursor_lookup_result is not None:
                messages = _build_cursor_answer_messages(messages, cursor_lookup_result)
                continue
            messages = messages + tool_messages + [{"role": "system", "content": TOOL_OUTPUT_SYSTEM_MESSAGE}]
    yield "data: [DONE]\n\n"


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.get('/debug/mcp/tools')
async def debug_mcp_tools():
    try:
        async with Client(MCP_BASE_URL) as client:
            tools = await client.list_tools()
        return {'tools': [{'name': tool.name, 'description': tool.description, 'inputSchema': getattr(tool, 'inputSchema', None)} for tool in tools]}
    except Exception as error:
        raise HTTPException(503, f'MCP unavailable: {error}') from error


@app.post('/v1/chat/completions')
async def chat_completions(req: ChatRequest):
    if req.stream:
        return StreamingResponse(_event_stream(req), media_type='text/event-stream')
    request_messages = _inject_query_guidance(req.messages)
    payload = {'model': req.model or 'local', 'messages': request_messages, 'temperature': req.temperature if req.temperature is not None else 0.2, 'tools': TOOLS, 'tool_choice': req.tool_choice if req.tool_choice is not None else 'auto'}
    async with httpx.AsyncClient(timeout=120.0) as client:
        interpreted = await try_section_timing_interpretation(request_messages, client, payload['model'], _llm_complete, call_mcp)
        if interpreted is not None:
            if interpreted.get('error') is not None:
                error = dict(interpreted.get('error') or {})
                raise HTTPException(
                    status_code=422,
                    detail={
                        'code': error.get('code', 'gateway_error'),
                        'detail': error.get('detail', 'Assistant request failed.'),
                        'retryable': bool(error.get('retryable', True)),
                    },
                )
            answer_text = str(interpreted.get('answer_text') or '')
            return {
                'id': 'chatcmpl-section-timing',
                'object': 'chat.completion',
                'choices': [
                    {
                        'index': 0,
                        'message': {'role': 'assistant', 'content': answer_text},
                        'finish_reason': 'stop',
                    }
                ],
            }
        data1 = await _llm_complete(client, payload)
        msg1 = data1['choices'][0]['message']
        tool_calls = msg1.get('tool_calls')
        if not tool_calls:
            return data1
        tool_messages = []
        section_lookup_result = None
        chord_lookup_result = None
        cursor_lookup_result = None
        for tc in tool_calls:
            tool_name = tc['function']['name']
            raw_args = tc['function'].get('arguments', '{}')
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                raise HTTPException(400, f"Tool arguments invalid JSON for {tool_name}: {raw_args}")
            result = await call_mcp(tool_name, args)
            if tool_name == 'mcp_find_section':
                section_lookup_result = result
            if tool_name == 'mcp_find_chord':
                chord_lookup_result = result
            if tool_name == 'mcp_read_cursor':
                cursor_lookup_result = result
            tool_messages.append({'role': 'tool', 'tool_call_id': tc['id'], 'content': _render_tool_result(tool_name, result)})
        if section_lookup_result is not None and _is_section_timing_question(request_messages):
            return await _llm_complete(client, {**payload, 'messages': _build_section_answer_messages(request_messages, section_lookup_result), 'tools': [], 'tool_choice': 'none'})
        if chord_lookup_result is not None:
            return await _llm_complete(client, {**payload, 'messages': _build_chord_answer_messages(request_messages, chord_lookup_result), 'tools': [], 'tool_choice': 'none'})
        if cursor_lookup_result is not None:
            return await _llm_complete(client, {**payload, 'messages': _build_cursor_answer_messages(request_messages, cursor_lookup_result), 'tools': [], 'tool_choice': 'none'})
        return await _llm_complete(client, {**payload, 'messages': request_messages + [msg1] + tool_messages + [{'role': 'system', 'content': TOOL_OUTPUT_SYSTEM_MESSAGE}]})