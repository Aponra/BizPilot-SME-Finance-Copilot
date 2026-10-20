"""Privacy-safe OpenAI Responses API orchestration."""
import json
import os
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional
import pandas as pd
from tools import TOOL_SCHEMAS, compact_summary, dispatch_tool, route_question
from privacy import redact_text

SYSTEM_PROMPT = """You are BizPilot, the SME Finance Copilot for Bengal Boots in Bangladesh. Use a tool for every numerical or analytical claim and never invent a number. Separate known facts, owner assumptions, and calculated estimates. Briefly explain calculations without private reasoning. Ask one concise follow-up when essential facts are missing. Do not promise outcomes or perform real payments, loans, purchases, or inventory actions. State that owner confirmation is required before any simulated action. Advice is educational, not financial advice."""

def _is_rate_limit_error(exc: Exception) -> bool:
    """Identify quota/rate-limit failures without displaying provider details."""
    return getattr(exc, "status_code", None) == 429 or type(exc).__name__ == "RateLimitError"

def _local_fallback_answer(question: str, orders: pd.DataFrame, costs: Mapping[str, float], logger: Optional[Callable] = None) -> str:
    """Provide safe deterministic help when the language-model request is unavailable."""
    tool_name = route_question(question)
    if tool_name not in {"analyze_business_finances", "analyze_courier_performance"}:
        destinations = {
            "compare_pricing_scenarios": "Pricing and Marketing Simulator",
            "analyze_marketing_campaign": "Pricing and Marketing Simulator",
            "forecast_cash_flow": "Cash-Flow Forecast",
            "compare_financing_options": "Financing Options",
        }
        destination = destinations[tool_name]
        return (
            "OpenAI API quota or rate limits are currently preventing a chat response. "
            f"Please use **{destination}** in the left menu; its calculations run locally and remain available. "
            "No customer data was sent."
        )

    result = dispatch_tool(tool_name, {}, orders, costs)
    if logger:
        logger({"timestamp": datetime.now(timezone.utc).isoformat(), "user_question": redact_text(question), "tool_selected": tool_name, "sanitized_tool_inputs": {}, "tool_result_summary": compact_summary(result), "confirmation_required": False, "final_status": "completed_locally_after_api_limit"})
    if tool_name == "analyze_courier_performance":
        answer = (
            f"Delivered COD sales are **৳{result['delivered_cod']:,.0f}**. Delivery success is "
            f"**{result['delivery_success_rate_pct']:.1f}%** and cancellation rate is "
            f"**{result['cancellation_rate_pct']:.1f}%**. Recorded courier charges total "
            f"**৳{result['courier_charges']:,.0f}**."
        )
    else:
        answer = (
            f"Recognized revenue is **৳{result['total_recognized_revenue']:,.0f}**. Estimated total costs are "
            f"**৳{result['estimated_total_costs']:,.0f}**, giving estimated net profit of "
            f"**৳{result['estimated_net_profit']:,.0f}** and an estimated margin of "
            f"**{result['estimated_profit_margin_pct']:.1f}%**. The selected data contains "
            f"**{result['delivered_orders']} delivered**, **{result['cancelled_orders']} cancelled**, and "
            f"**{result['partial_deliveries']} partially delivered** orders."
        )
    return (
        "OpenAI API quota or rate limits are currently preventing the language-model response, "
        "so BizPilot ran the deterministic finance tool locally instead.\n\n"
        + answer
        + f"\n\n**Tool used:** `{tool_name}`\n\n"
        "Costs are estimates based on the visible owner assumptions. This is educational decision support."
    )

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
        elif _is_rate_limit_error(exc):
            message = "The API key was recognized, but this OpenAI project has reached an API quota or rate limit. Check project billing and usage limits. BizPilot's local dashboards and finance tools still work."
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
    try:
        response = client.responses.create(model=config["model"] or "test-model", instructions=SYSTEM_PROMPT, input=inputs, tools=TOOL_SCHEMAS, tool_choice="required")
    except Exception as exc:
        if _is_rate_limit_error(exc):
            return _local_fallback_answer(question, orders, costs, logger)
        raise
    used = []
    for _ in range(5):
        calls = [x for x in response.output if getattr(x, "type", None) == "function_call"]
        if not calls: break
        inputs.extend(response.output)
        for call in calls:
            arguments = json.loads(call.arguments or "{}"); result = dispatch_tool(call.name, arguments, orders, costs); used.append(call.name)
            if logger: logger({"timestamp": datetime.now(timezone.utc).isoformat(), "user_question": safe_question, "tool_selected": call.name, "sanitized_tool_inputs": arguments, "tool_result_summary": compact_summary(result), "confirmation_required": bool(result.get("confirmation_required", False)), "final_status": "completed"})
            inputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result, default=str)})
        try:
            response = client.responses.create(model=config["model"] or "test-model", instructions=SYSTEM_PROMPT, input=inputs, tools=TOOL_SCHEMAS)
        except Exception as exc:
            if _is_rate_limit_error(exc):
                return _local_fallback_answer(question, orders, costs, logger)
            raise
    answer = response.output_text
    return answer + (("\n\nTools used: " + ", ".join(dict.fromkeys(used))) if used else "")
