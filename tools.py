"""OpenAI tool schemas and deterministic tool dispatch."""
import json
import math
from typing import Any, Mapping
import pandas as pd
from finance import analyze_finances, compare_financing, compare_pricing, courier_performance, date_range_metrics, forecast_cash

TOOL_SCHEMAS = [
    {"type": "function", "name": "analyze_business_finances", "description": "Calculate revenue, costs, profit, margin, and courier outcomes using the current sanitized dataset.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"type": "function", "name": "analyze_courier_performance", "description": "Analyze delivery success, cancellations, partial delivery, COD, charges, and trends.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"type": "function", "name": "compare_pricing_scenarios", "description": "Compare prices using transparent demand and cancellation assumptions.", "parameters": {"type": "object", "properties": {"prices": {"type": "array", "items": {"type": "number"}}, "baseline_price": {"type": "number"}, "baseline_demand": {"type": "number"}, "sensitivity": {"type": "number"}, "competitor_price": {"type": ["number", "null"]}, "cancellation_rate": {"type": "number"}}, "required": ["prices", "baseline_price", "baseline_demand", "sensitivity", "competitor_price", "cancellation_rate"], "additionalProperties": False}},
    {"type": "function", "name": "analyze_marketing_campaign", "description": "Calculate campaign CAC, ROAS, estimated profit, and break-even orders; null marks missing information.", "parameters": {"type": "object", "properties": {"campaign_type": {"type": "string"}, "spend": {"type": ["number", "null"]}, "orders_attributed": {"type": ["number", "null"]}, "revenue_attributed": {"type": ["number", "null"]}, "contribution_per_order": {"type": ["number", "null"]}}, "required": ["campaign_type", "spend", "orders_attributed", "revenue_attributed", "contribution_per_order"], "additionalProperties": False}},
    {"type": "function", "name": "forecast_cash_flow", "description": "Forecast at least three months of cash and flag shortages.", "parameters": {"type": "object", "properties": {"monthly_sales": {"type": "number"}, "monthly_variable_costs": {"type": "number"}, "financing_payment": {"type": "number"}, "growth_rate": {"type": "number"}, "months": {"type": "integer"}}, "required": ["monthly_sales", "monthly_variable_costs", "financing_payment", "growth_rate", "months"], "additionalProperties": False}},
    {"type": "function", "name": "compare_financing_options", "description": "Compare simulated loan, supplier credit, revenue financing, and no-financing choices.", "parameters": {"type": "object", "properties": {"amount": {"type": "number"}, "months": {"type": "integer"}, "expected_monthly_revenue": {"type": "number"}}, "required": ["amount", "months", "expected_monthly_revenue"], "additionalProperties": False}},
]

def analyze_marketing_campaign(campaign_type: str, spend, orders_attributed, revenue_attributed, contribution_per_order) -> dict:
    values = {"spend": spend, "orders_attributed": orders_attributed, "revenue_attributed": revenue_attributed, "contribution_per_order": contribution_per_order}; missing = [k for k, v in values.items() if v is None]
    if missing: return {"status": "needs_information", "missing_information": missing, "question": "Please provide " + ", ".join(missing) + "."}
    if any(float(v) < 0 for v in values.values()): raise ValueError("Campaign values cannot be negative")
    profit = float(orders_attributed) * float(contribution_per_order) - float(spend)
    return {"campaign_type": campaign_type, "customer_acquisition_cost": round(float(spend) / float(orders_attributed), 2) if orders_attributed else None, "return_on_ad_spend": round(float(revenue_attributed) / float(spend), 2) if spend else None, "estimated_campaign_profit": round(profit, 2), "break_even_orders": math.ceil(float(spend) / float(contribution_per_order)) if contribution_per_order else None, "assumptions": "Attribution and contribution are owner-provided estimates."}

def dispatch_tool(name: str, arguments: Mapping[str, Any], orders: pd.DataFrame, costs: Mapping[str, float]) -> dict:
    args = dict(arguments)
    if name == "analyze_business_finances": return {**analyze_finances(orders, costs), "selected_date_range_metrics": date_range_metrics(orders)}
    if name == "analyze_courier_performance": return {**courier_performance(orders), "selected_date_range_metrics": date_range_metrics(orders)}
    if name == "compare_pricing_scenarios": return compare_pricing(unit_cost=float(costs["product_purchase_cost"]), packaging=float(costs["packaging_cost_per_order"]), courier=float(orders["courier_charge"].mean()), ad_allocation=float(costs["monthly_facebook_ads"]) / max(len(orders), 1), discount=float(costs["discount_amount"]), **args)
    if name == "analyze_marketing_campaign": return analyze_marketing_campaign(**args)
    if name == "forecast_cash_flow": return forecast_cash(current_cash=float(costs["current_cash"]), monthly_ads=float(costs["monthly_facebook_ads"]), monthly_inventory=float(costs["planned_inventory_purchases"]), other_expenses=float(costs["other_monthly_expenses"]), **args)
    if name == "compare_financing_options": return compare_financing(**args)
    raise ValueError(f"Unknown tool: {name}")

def compact_summary(result: dict) -> str:
    value = json.dumps(result, ensure_ascii=False, default=str); return value[:500] + ("…" if len(value) > 500 else "")

def route_question(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ("courier", "delivery success", "cancel")): return "analyze_courier_performance"
    if any(x in q for x in ("price", "discount", "free delivery")): return "compare_pricing_scenarios"
    if any(x in q for x in ("facebook", "influencer", "campaign", "roas")): return "analyze_marketing_campaign"
    if any(x in q for x in ("cash", "shortage", "afford")): return "forecast_cash_flow"
    if any(x in q for x in ("loan", "financ", "credit", "borrow")): return "compare_financing_options"
    return "analyze_business_finances"
