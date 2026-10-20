"""Privacy-safe OpenAI Responses API orchestration."""
import json
import os
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional
import pandas as pd
from tools import TOOL_SCHEMAS, compact_summary, dispatch_tool
from privacy import redact_text

SYSTEM_PROMPT = """You are BizPilot, the SME Finance Copilot for Bengal Boots in Bangladesh. Use a tool for every numerical or analytical claim and never invent a number. Separate known facts, owner assumptions, and calculated estimates. Briefly explain calculations without private reasoning. Ask one concise follow-up when essential facts are missing. Do not promise outcomes or perform real payments, loans, purchases, or inventory actions. State that owner confirmation is required before any simulated action. Advice is educational, not financial advice."""

def api_configuration(env: Optional[Mapping[str, str]] = None) -> dict:
    source = os.environ if env is None else env; key = source.get("OPENAI_API_KEY", "").strip(); model = source.get("OPENAI_MODEL", "").strip()
    return {"enabled": bool(key and model), "api_key": key, "model": model, "message": "Set OPENAI_API_KEY and OPENAI_MODEL in your environment to enable AI chat." if not (key and model) else "AI chat configured."}

def test_ai_connection(client=None) -> dict:
    """Test credentials without sending business or customer data."""
    config = api_configuration()
    if not config["api_key"]:
        return {"ok": False, "message": "OpenAI API key is missing. Add it to `.env`, then restart BizPilot."}
    if not config["model"]:
        return {"ok": False, "message": "OpenAI model is missing. Set `OPENAI_MODEL` in `.env`."}
    try:
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        client.responses.create(model=config["model"], input="Reply with exactly: connection successful", max_output_tokens=32)
        return {"ok": True, "message": f"AI connection succeeded using {config['model']}."}
    except Exception as exc:
        error_code = getattr(exc, "code", None)
        status_code = getattr(exc, "status_code", None)
        if error_code == "billing_not_active":
            message = "The API key was recognized, but API billing is not active for this OpenAI project. Enable billing or use a key from a project with active API billing."
        elif status_code == 401 or error_code == "invalid_api_key":
            message = "OpenAI rejected the API key. Replace it in `.env` with a valid project key, then restart BizPilot."
        elif status_code == 404 or error_code == "model_not_found":
            message = "The configured model is unavailable to this OpenAI project. Update `OPENAI_MODEL` in `.env`."
        else:
            message = "OpenAI connection failed. Check the API key, model access, network connection, and usage limits."
        return {"ok": False, "message": message}

def ask_copilot(question: str, history: list[dict], orders: pd.DataFrame, costs: Mapping[str, float], client=None, logger: Optional[Callable] = None) -> str:
    config = api_configuration()
    if client is None and not config["enabled"]: return "AI chat is not configured yet. Set `OPENAI_API_KEY` and `OPENAI_MODEL`, then restart the app. Dashboards and local analysis remain available without a key."
    if client is None:
        from openai import OpenAI
        client = OpenAI()
    safe_question = redact_text(question)
    inputs = [{"role": x["role"], "content": redact_text(x["content"])} for x in history[-10:]] + [{"role": "user", "content": safe_question}]
    response = client.responses.create(model=config["model"] or "test-model", instructions=SYSTEM_PROMPT, input=inputs, tools=TOOL_SCHEMAS, tool_choice="required"); used = []
    for _ in range(5):
        calls = [x for x in response.output if getattr(x, "type", None) == "function_call"]
        if not calls: break
        inputs.extend(response.output)
        for call in calls:
            arguments = json.loads(call.arguments or "{}"); result = dispatch_tool(call.name, arguments, orders, costs); used.append(call.name)
            if logger: logger({"timestamp": datetime.now(timezone.utc).isoformat(), "user_question": safe_question, "tool_selected": call.name, "sanitized_tool_inputs": arguments, "tool_result_summary": compact_summary(result), "confirmation_required": bool(result.get("confirmation_required", False)), "final_status": "completed"})
            inputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result, default=str)})
        response = client.responses.create(model=config["model"] or "test-model", instructions=SYSTEM_PROMPT, input=inputs, tools=TOOL_SCHEMAS)
    answer = response.output_text
    return answer + (("\n\nTools used: " + ", ".join(dict.fromkeys(used))) if used else "")
