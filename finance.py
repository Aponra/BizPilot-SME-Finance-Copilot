"""Core deterministic financial calculations for Bengal Boots (amounts in BDT)."""
from __future__ import annotations

import math
import random
from datetime import date, timedelta
from typing import Iterable, Mapping, Optional, Sequence

import pandas as pd

DELIVERED, CANCELLED, PARTIAL = "Delivered", "Cancelled", "Partial delivery"
PRODUCTS = [
    {"product": "Dhaka Street Sneaker", "price": 2500, "cost": 1420, "weight": 29},
    {"product": "Bengal Leather Boot", "price": 3600, "cost": 2180, "weight": 20},
    {"product": "Classic Office Loafer", "price": 2800, "cost": 1690, "weight": 24},
    {"product": "Everyday Sandal", "price": 1800, "cost": 890, "weight": 20},
    {"product": "Trail Runner", "price": 3200, "cost": 1910, "weight": 7},
]
DEFAULT_COSTS = {"product_purchase_cost": 1100.0, "packaging_cost_per_order": 0.0, "monthly_facebook_ads": 0.0, "influencer_expense": 0.0, "discount_amount": 0.0, "return_related_cost": 0.0, "current_cash": 0.0, "planned_inventory_purchases": 0.0, "other_monthly_expenses": 0.0}


def validate_non_negative(values: Mapping[str, float]) -> None:
    for name, value in values.items():
        try: numeric = float(value)
        except (TypeError, ValueError) as exc: raise ValueError(f"{name} must be a number") from exc
        if not math.isfinite(numeric) or numeric < 0: raise ValueError(f"{name} must be a non-negative finite number")


def generate_sample_orders(order_count: int = 240, seed: int = 42) -> pd.DataFrame:
    """Generate deterministic, anonymous Steadfast-style footwear orders."""
    if order_count < 1: raise ValueError("order_count must be at least 1")
    rng = random.Random(seed); names = [p["product"] for p in PRODUCTS]; weights = [p["weight"] for p in PRODUCTS]
    lookup = {p["product"]: p for p in PRODUCTS}; statuses = [DELIVERED, CANCELLED, PARTIAL, "Pending", "In review", "Exceptional"]
    rows = []
    for index in range(order_count):
        name = rng.choices(names, weights=weights, k=1)[0]; item = lookup[name]
        status = rng.choices(statuses, weights=[72, 13, 6, 5, 2, 2], k=1)[0]
        rows.append({"order_id": f"BB-{index + 1:05d}", "order_date": date(2026, 5, 1) + timedelta(days=rng.randint(0, 169)), "product": name, "cod_amount": float(max(0, item["price"] + rng.choice([0, 0, 0, -100, -200]))), "courier_charge": float(rng.choice([80, 90, 100, 120, 140])), "status": status, "settlement_status": "Settled" if status == DELIVERED else "Unsettled"})
    return pd.DataFrame(rows).sort_values("order_date").reset_index(drop=True)


def analyze_finances(orders: pd.DataFrame, costs: Mapping[str, float]) -> dict:
    validate_non_negative(costs); statuses = orders["status"].astype(str)
    dm, pm, cm = statuses.eq(DELIVERED), statuses.eq(PARTIAL), statuses.eq(CANCELLED)
    delivered, partial, cancelled = int(dm.sum()), int(pm.sum()), int(cm.sum()); attempted = delivered + partial + cancelled
    delivered_revenue = float(orders.loc[dm, "cod_amount"].sum()); partial_revenue = float(orders.loc[pm, "cod_amount"].sum())
    revenue = delivered_revenue + partial_revenue; successful = delivered + partial
    # Cancelled/returned inventory remains saleable, so it is not recognized as COGS.
    # Partial-delivery product quantity is unknown in courier data and is excluded.
    product_cost = float(costs["product_purchase_cost"]) * delivered
    courier_cost = float(orders["courier_charge"].sum()); packaging = float(costs["packaging_cost_per_order"]) * len(orders)
    discounts = float(costs["discount_amount"]) * successful; returns = float(costs["return_related_cost"]) * (cancelled + partial)
    marketing = float(costs["monthly_facebook_ads"]) + float(costs["influencer_expense"]); other = float(costs["other_monthly_expenses"])
    gross = revenue - product_cost - courier_cost - packaging - discounts - returns; total = product_cost + courier_cost + packaging + discounts + returns + marketing + other; net = revenue - total
    product_performance = []
    for name, group in orders.groupby("product"):
        delivered_group = group[group["status"].eq(DELIVERED)]; count = len(delivered_group); product_revenue = float(delivered_group["cod_amount"].sum())
        direct_cost = count * (float(costs["product_purchase_cost"]) + float(costs["packaging_cost_per_order"])) + float(delivered_group["courier_charge"].sum())
        product_performance.append({"product": name, "delivered_orders": count, "delivered_revenue": round(product_revenue, 2), "estimated_contribution_before_marketing": round(product_revenue - direct_cost, 2)})
    product_performance.sort(key=lambda item: item["estimated_contribution_before_marketing"], reverse=True)
    return {"delivered_revenue": round(delivered_revenue, 2), "partial_delivery_revenue_estimate": round(partial_revenue, 2), "total_recognized_revenue": round(revenue, 2), "product_cost": round(product_cost, 2), "courier_cost": round(courier_cost, 2), "packaging_cost": round(packaging, 2), "discount_cost": round(discounts, 2), "return_related_cost": round(returns, 2), "advertising_and_influencer_cost": round(marketing, 2), "other_operating_cost": round(other, 2), "estimated_total_costs": round(total, 2), "estimated_gross_profit": round(gross, 2), "estimated_net_profit": round(net, 2), "estimated_profit_margin_pct": round(net / revenue * 100, 2) if revenue else 0.0, "delivered_orders": delivered, "cancelled_orders": cancelled, "partial_deliveries": partial, "delivery_success_rate_pct": round(delivered / attempted * 100, 2) if attempted else 0, "cancellation_rate_pct": round(cancelled / attempted * 100, 2) if attempted else 0, "average_order_value": round(delivered_revenue / delivered, 2) if delivered else 0, "average_courier_cost": round(courier_cost / len(orders), 2) if len(orders) else 0, "cancelled_cod_value": round(float(orders.loc[cm, "cod_amount"].sum()), 2), "product_performance": product_performance, "assumptions": ["Product cost is recognized only for delivered orders.", "Cancelled/returned footwear remains saleable and is not expensed as product cost.", "Partial-delivery COD is counted as collected; its product cost is excluded because fulfilled quantity is missing.", "All recorded courier charges are included.", "Other expenses are included only when entered by the owner.", "Product contribution excludes shared marketing and operating overheads."]}


def courier_performance(orders: pd.DataFrame) -> dict:
    statuses = orders["status"].astype(str); counts = {name: int(statuses.eq(name).sum()) for name in sorted(statuses.unique())}; attempted = sum(counts.get(s, 0) for s in (DELIVERED, CANCELLED, PARTIAL))
    monthly = orders.assign(month=pd.to_datetime(orders["order_date"]).dt.to_period("M").astype(str)).groupby("month").agg(orders=("order_id", "count"), cod_amount=("cod_amount", "sum"), courier_charges=("courier_charge", "sum")).reset_index()
    return {"status_counts": counts, "delivery_success_rate_pct": round(counts.get(DELIVERED, 0) / attempted * 100, 2) if attempted else 0, "cancellation_rate_pct": round(counts.get(CANCELLED, 0) / attempted * 100, 2) if attempted else 0, "total_cod": round(float(orders["cod_amount"].sum()), 2), "delivered_cod": round(float(orders.loc[statuses.eq(DELIVERED), "cod_amount"].sum()), 2), "courier_charges": round(float(orders["courier_charge"].sum()), 2), "monthly_trends": monthly.to_dict("records")}


def date_range_metrics(orders: pd.DataFrame) -> dict:
    """Calculate courier KPIs and daily/monthly trends for an already filtered range."""
    statuses = orders["status"].astype(str); delivered = statuses.eq(DELIVERED); cancelled = statuses.eq(CANCELLED); partial = statuses.eq(PARTIAL)
    attempted = int((delivered | cancelled | partial).sum()); delivered_count = int(delivered.sum()); cancelled_count = int(cancelled.sum())
    delivered_cod = float(orders.loc[delivered, "cod_amount"].sum()); delivered_courier = float(orders.loc[delivered, "courier_charge"].sum())
    base = orders.assign(delivered_sales=orders["cod_amount"].where(delivered, 0), delivered_order=delivered.astype(int))
    daily = base.assign(period=pd.to_datetime(base["order_date"]).dt.strftime("%Y-%m-%d")).groupby("period").agg(sales=("delivered_sales", "sum"), orders=("order_id", "count"), delivered_orders=("delivered_order", "sum")).reset_index()
    monthly = base.assign(period=pd.to_datetime(base["order_date"]).dt.to_period("M").astype(str)).groupby("period").agg(sales=("delivered_sales", "sum"), orders=("order_id", "count"), delivered_orders=("delivered_order", "sum")).reset_index()
    return {"total_orders": len(orders), "delivered_orders": delivered_count, "cancelled_orders": cancelled_count, "partial_deliveries": int(partial.sum()), "delivered_cod_sales": round(delivered_cod, 2), "cancelled_order_value": round(float(orders.loc[cancelled, "cod_amount"].sum()), 2), "partial_delivery_collections": round(float(orders.loc[partial, "cod_amount"].sum()), 2), "total_courier_charges": round(float(orders["courier_charge"].sum()), 2), "net_delivered_cod_after_courier": round(delivered_cod - delivered_courier, 2), "average_delivered_order_value": round(delivered_cod / delivered_count, 2) if delivered_count else 0, "delivery_success_rate_pct": round(delivered_count / attempted * 100, 2) if attempted else 0, "cancellation_rate_pct": round(cancelled_count / attempted * 100, 2) if attempted else 0, "zero_cod_anomalies": int(orders["cod_amount"].eq(0).sum()), "daily_trends": daily.to_dict("records"), "monthly_trends": monthly.to_dict("records")}


def compare_pricing(prices: Sequence[float], unit_cost: float, packaging: float, courier: float, ad_allocation: float, discount: float, cancellation_rate: float, baseline_price: float, baseline_demand: float, sensitivity: float = 1.0, explicit_demand: Optional[Sequence[float]] = None, competitor_price: Optional[float] = None, confidence: str = "Low — owner assumptions, not a demand forecast") -> dict:
    validate_non_negative({"unit_cost": unit_cost, "packaging": packaging, "courier": courier, "ad_allocation": ad_allocation, "discount": discount, "baseline_price": baseline_price, "baseline_demand": baseline_demand, "sensitivity": sensitivity})
    if not 0 <= cancellation_rate < 1: raise ValueError("cancellation_rate must be between 0 and less than 1")
    if not prices or (explicit_demand is not None and len(explicit_demand) != len(prices)): raise ValueError("prices and explicit demand must contain matching scenarios")
    rows = []; variable_cost = unit_cost + packaging + courier + ad_allocation
    for index, raw in enumerate(prices):
        price = float(raw)
        if price <= 0: raise ValueError("prices must be greater than zero")
        units = max(0, round(float(explicit_demand[index]))) if explicit_demand is not None else max(0, round(baseline_demand * (1 - sensitivity * ((price - baseline_price) / baseline_price))))
        successful = round(units * (1 - cancellation_rate), 1); net_price = max(0, price - discount); revenue = successful * net_price
        delivery_costs = successful * variable_cost; failed_costs = (units - successful) * (courier + packaging); total = delivery_costs + failed_costs; profit = revenue - total; contribution = net_price - variable_cost
        rows.append({"selling_price": round(price, 2), "expected_units": units, "successful_deliveries": successful, "revenue": round(revenue, 2), "total_costs": round(total, 2), "profit": round(profit, 2), "profit_margin_pct": round(profit / revenue * 100, 2) if revenue else 0, "contribution_per_delivery": round(contribution, 2), "break_even_orders": math.ceil(failed_costs / contribution) if contribution > 0 else None})
    viable = [r for r in rows if r["successful_deliveries"] > 0]
    return {"scenarios": rows, "recommended_scenario": max(viable, key=lambda r: r["profit"]) if viable else None, "assumptions": {"baseline_price": baseline_price, "baseline_demand": baseline_demand, "price_sensitivity": sensitivity, "cancellation_rate_pct": cancellation_rate * 100, "competitor_price": competitor_price, "discount_per_order": discount, "demand_source": "Owner-entered" if explicit_demand is not None else "Selected sensitivity profile"}, "confidence": confidence}


def forecast_cash(current_cash: float, monthly_sales: float, monthly_variable_costs: float, monthly_ads: float, monthly_inventory: float, other_expenses: float, financing_payment: float = 0, growth_rate: float = 0, months: int = 3) -> dict:
    validate_non_negative({"current_cash": current_cash, "monthly_sales": monthly_sales, "monthly_variable_costs": monthly_variable_costs, "monthly_ads": monthly_ads, "monthly_inventory": monthly_inventory, "other_expenses": other_expenses, "financing_payment": financing_payment, "growth_rate": growth_rate})
    if not 3 <= months <= 24: raise ValueError("months must be between 3 and 24")
    balance = float(current_cash); rows = []; alerts = []; today = pd.Timestamp.today().normalize()
    for index in range(1, months + 1):
        revenue = monthly_sales * ((1 + growth_rate) ** (index - 1)); outflows = monthly_variable_costs * ((1 + growth_rate) ** (index - 1)) + monthly_ads + monthly_inventory + other_expenses + financing_payment
        opening = balance; balance = opening + revenue - outflows; month = (today + pd.DateOffset(months=index)).strftime("%b %Y")
        rows.append({"month": month, "opening_cash": round(opening, 2), "cash_inflow": round(revenue, 2), "cash_outflow": round(outflows, 2), "closing_cash": round(balance, 2)})
        if balance < 0: alerts.append(f"Cash shortage of ৳{abs(balance):,.0f} projected for {month}.")
        elif balance < outflows * .2: alerts.append(f"Low cash buffer projected for {month}.")
    return {"forecast": rows, "alerts": alerts, "shortage_expected": any(r["closing_cash"] < 0 for r in rows), "suggested_actions": ["Delay non-essential inventory purchases.", "Reduce discretionary campaign spending.", "Negotiate supplier credit before high-cost financing."] if alerts else ["Maintain a cash buffer and review actuals monthly."], "assumptions": {"monthly_growth_rate_pct": growth_rate * 100, "forecast_months": months}}


def compare_financing(amount: float, months: int, expected_monthly_revenue: float) -> dict:
    validate_non_negative({"amount": amount, "expected_monthly_revenue": expected_monthly_revenue})
    if amount <= 0 or months < 1: raise ValueError("amount and months must be positive")
    options = []
    for name, rate, fee, note in [("Small-business loan", .12, .01, "Fixed monthly repayment"), ("Supplier credit", .06, 0, "Inventory-focused; negotiate with supplier"), ("Revenue-based financing", .18, 0, "Approx. 10% of monthly revenue until repaid")]:
        total = amount * (1 + rate) + amount * fee; payment = total / months if name != "Revenue-based financing" else min(expected_monthly_revenue * .10, total)
        options.append({"option": name, "amount": round(amount, 2), "approx_total_repayment": round(total, 2), "approx_cost": round(total - amount, 2), "monthly_burden": round(payment, 2), "burden_pct_of_revenue": round(payment / expected_monthly_revenue * 100, 2) if expected_monthly_revenue else None, "note": note})
    options.append({"option": "No financing / reduce expenses", "amount": 0, "approx_total_repayment": 0, "approx_cost": 0, "monthly_burden": 0, "burden_pct_of_revenue": 0, "note": "Preserves borrowing capacity; may slow growth."})
    return {"options": options, "educational_notice": "Simulated educational examples only — not real offers or financial advice.", "confirmation_required": True}


def build_product_summary(orders: pd.DataFrame) -> pd.DataFrame:
    """Legacy helper retained for compatibility with the first version."""
    rows = []
    for product, group in orders.groupby("Product", sort=False):
        delivered = group[group["Status"] == "Delivered"]; returned = int((group["Status"] == "Returned").sum()); sales = float(delivered["Selling price"].sum()); costs = float(delivered["Unit cost"].sum())
        rows.append({"Product": product, "Selling price": float(group["Selling price"].iloc[0]), "Unit cost": float(group["Unit cost"].iloc[0]), "Delivered": len(delivered), "Returned": returned, "Return rate": returned / len(group) * 100, "Sales": sales, "Costs": costs, "Profit": sales - costs})
    return pd.DataFrame(rows).sort_values("Sales", ascending=False).reset_index(drop=True)


def calculate_price_scenarios(unit_cost: float, expected_units: int, prices: Iterable[float]) -> pd.DataFrame:
    price_list = list(prices); result = compare_pricing(price_list, unit_cost, 0, 0, 0, 0, 0, price_list[0], expected_units, 0)
    return pd.DataFrame([{"Selling price": r["selling_price"], "Expected units": r["expected_units"], "Revenue": r["revenue"], "Total cost": r["total_costs"], "Profit": r["profit"], "Profit margin": r["profit_margin_pct"]} for r in result["scenarios"]])
