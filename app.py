"""BizPilot — AI-powered SME Finance Copilot for Bengal Boots."""
from __future__ import annotations
import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from agent import api_configuration, ask_copilot, test_ai_connection
from data_loader import DEFAULT_SOURCE_LABEL, DEFAULT_SOURCE_WARNING, default_data, load_upload, template_csv
from finance import DEFAULT_COSTS, analyze_finances, compare_financing, compare_pricing, date_range_metrics, forecast_cash
from tools import analyze_marketing_campaign

load_dotenv(); st.set_page_config(page_title="BizPilot | Bengal Boots", page_icon="🥾", layout="wide")
st.markdown("""<style>.stApp{background:linear-gradient(180deg,#f7faf8 0%,#fff 30%)}[data-testid="stMetric"]{background:white;border:1px solid #e2e8e5;border-radius:14px;padding:14px}.hero{padding:1.25rem 1.5rem;border-radius:18px;background:linear-gradient(125deg,#123c2d,#206b4f);color:white;margin-bottom:1rem}.hero h1{margin:0;color:white}.hero p{margin:.35rem 0 0;color:#d8eee5}.notice{padding:.75rem 1rem;border-left:4px solid #d59b2b;background:#fff8e8;border-radius:8px}</style>""", unsafe_allow_html=True)
SECTIONS = ["AI Finance Copilot", "Business Dashboard", "Pricing and Marketing Simulator", "Cash-Flow Forecast", "Financing Options", "Data Upload", "Agent Activity Log"]
if "orders" not in st.session_state: st.session_state.orders = default_data()
if "data_source" not in st.session_state: st.session_state.data_source = DEFAULT_SOURCE_LABEL
if "costs" not in st.session_state: st.session_state.costs = DEFAULT_COSTS.copy()
if "messages" not in st.session_state: st.session_state.messages = []
if "activity_log" not in st.session_state: st.session_state.activity_log = []
def add_log(entry): st.session_state.activity_log.append(entry)
def money(value): return f"৳{value:,.0f}"

with st.sidebar:
    st.markdown("## 🥾 BizPilot"); st.caption("Bengal Boots · SME Finance Copilot")
    section = st.radio("Navigate", SECTIONS, label_visibility="collapsed"); st.divider(); st.caption("DATA SOURCE"); st.success(st.session_state.data_source)
    if st.session_state.data_source == DEFAULT_SOURCE_LABEL: st.warning(DEFAULT_SOURCE_WARNING)
    all_dates = pd.to_datetime(st.session_state.orders["order_date"])
    st.caption("DATE RANGE")
    selected_dates = st.date_input("Analysis period", value=(all_dates.min().date(), all_dates.max().date()), min_value=all_dates.min().date(), max_value=all_dates.max().date(), label_visibility="collapsed")
    with st.expander("Business cost assumptions"):
        labels = {"product_purchase_cost": "Product purchase cost / order", "packaging_cost_per_order": "Packaging cost / order", "monthly_facebook_ads": "Monthly Facebook advertising", "influencer_expense": "Influencer expense", "discount_amount": "Discount / delivered order", "return_related_cost": "Return cost / failed order", "current_cash": "Current available cash", "planned_inventory_purchases": "Monthly planned inventory", "other_monthly_expenses": "Other monthly expenses"}
        with st.form("cost_form"):
            new_costs = {key: st.number_input(label, min_value=0.0, value=float(st.session_state.costs[key]), step=100.0) for key, label in labels.items()}
            if st.form_submit_button("Save assumptions", width="stretch"): st.session_state.costs = new_costs; st.success("Saved")
    config = api_configuration(); st.caption("AI STATUS"); st.info("Connected" if config["enabled"] else "Dashboard-only mode")
    if st.button("Test AI connection", width="stretch"):
        with st.spinner("Checking OpenAI connection…"):
            connection = test_ai_connection()
        if connection["ok"]: st.success(connection["message"])
        else: st.error(connection["message"])

raw_orders, costs = st.session_state.orders, st.session_state.costs
if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates
orders = raw_orders.loc[pd.to_datetime(raw_orders["order_date"]).dt.date.between(start_date, end_date)].copy()
finances = analyze_finances(orders, costs); range_metrics = date_range_metrics(orders)
st.markdown('<div class="hero"><h1>Bengal Boots · BizPilot</h1><p>Clearer decisions for pricing, cash flow, marketing and financing.</p></div>', unsafe_allow_html=True)
st.markdown('<div class="notice">Educational simulation only. No guaranteed outcomes, payments, loan applications, or inventory purchases. Owner confirmation is required before any simulated action.</div>', unsafe_allow_html=True)

if section == "AI Finance Copilot":
    st.subheader("AI Finance Copilot"); st.caption("Python tools calculate every number. Only aggregated, anonymized results are sent to OpenAI.")
    if not config["enabled"]: st.warning("AI chat is not configured. Add `OPENAI_API_KEY` and `OPENAI_MODEL` to `.env`, then restart. All other sections still work.")
    st.caption("Try: How is my business performing? · What was my delivery success rate? · Can I afford a ৳20,000 Facebook campaign?")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"])
    prompt = st.chat_input("Ask BizPilot about your business…", disabled=not config["enabled"])
    if prompt:
        history = st.session_state.messages.copy(); st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Running the appropriate finance tool…"):
                try: answer = ask_copilot(prompt, history, orders, costs, logger=add_log)
                except Exception as exc: answer = f"I couldn't complete that analysis safely. Check the model configuration and try again. ({type(exc).__name__})"
            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

elif section == "Business Dashboard":
    st.subheader("Business Dashboard")
    if st.session_state.data_source == DEFAULT_SOURCE_LABEL: st.warning(DEFAULT_SOURCE_WARNING)
    if range_metrics["zero_cod_anomalies"]: st.warning(f'{range_metrics["zero_cod_anomalies"]} zero-COD source anomaly requires review. The row remains included.')
    values = [("Total orders", range_metrics["total_orders"]), ("Delivered orders", range_metrics["delivered_orders"]), ("Cancelled orders", range_metrics["cancelled_orders"]), ("Partial deliveries", range_metrics["partial_deliveries"]), ("Delivered COD sales", money(range_metrics["delivered_cod_sales"])), ("Cancelled order value", money(range_metrics["cancelled_order_value"])), ("Partial collections", money(range_metrics["partial_delivery_collections"])), ("Total courier charges", money(range_metrics["total_courier_charges"])), ("Net delivered COD", money(range_metrics["net_delivered_cod_after_courier"])), ("Avg delivered value", money(range_metrics["average_delivered_order_value"])), ("Delivery success", f'{range_metrics["delivery_success_rate_pct"]:.1f}%'), ("Cancellation rate", f'{range_metrics["cancellation_rate_pct"]:.1f}%')]
    for start in (0, 4, 8):
        for col, (label, value) in zip(st.columns(4), values[start:start + 4]): col.metric(label, value)
    st.markdown("#### Estimated profitability")
    for col, (label, value) in zip(st.columns(4), [("Recognized revenue", money(finances["total_recognized_revenue"])), ("Estimated costs", money(finances["estimated_total_costs"])), ("Estimated profit", money(finances["estimated_net_profit"])), ("Estimated margin", f'{finances["estimated_profit_margin_pct"]:.1f}%')]): col.metric(label, value)
    st.caption("Costs and profit are estimates based on sidebar assumptions.")
    with st.expander("See the cost calculation"):
        st.dataframe(pd.DataFrame([
            {"Cost": "Product cost — delivered orders only", "Amount": finances["product_cost"]},
            {"Cost": "Recorded courier charges — all rows", "Amount": finances["courier_cost"]},
            {"Cost": "Packaging", "Amount": finances["packaging_cost"]},
            {"Cost": "Discounts", "Amount": finances["discount_cost"]},
            {"Cost": "Owner-entered return costs", "Amount": finances["return_related_cost"]},
            {"Cost": "Advertising and influencer", "Amount": finances["advertising_and_influencer_cost"]},
            {"Cost": "Other operating expenses", "Amount": finances["other_operating_cost"]},
        ]), width="stretch", hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="৳%.0f")})
        for assumption in finances["assumptions"]: st.caption("• " + assumption)
    daily, monthly = pd.DataFrame(range_metrics["daily_trends"]), pd.DataFrame(range_metrics["monthly_trends"])
    st.markdown("#### Daily and monthly delivered sales trends")
    c1, c2 = st.columns(2); c1.altair_chart(alt.Chart(daily).mark_line(point=True, color="#206b4f").encode(x=alt.X("period:N", title=None), y="sales:Q", tooltip=["period", "sales", "orders"]), use_container_width=True); c2.altair_chart(alt.Chart(monthly).mark_bar(color="#d59b2b").encode(x=alt.X("period:N", title=None), y="sales:Q", tooltip=["period", "sales", "orders"]), use_container_width=True)
    product_orders = orders.assign(product=orders["product"].fillna("Missing product information"))
    product = product_orders.assign(delivered_revenue=product_orders.cod_amount.where(product_orders.status.eq("Delivered"), 0), delivered=product_orders.status.eq("Delivered"), cancelled=product_orders.status.eq("Cancelled")).groupby("product").agg(orders=("order_id", "count"), delivered=("delivered", "sum"), cancelled=("cancelled", "sum"), revenue=("delivered_revenue", "sum"), courier_cost=("courier_charge", "sum")).reset_index(); product["estimated_product_cost"] = product.delivered * costs["product_purchase_cost"]; product["estimated_profit_before_overheads"] = product.revenue - product.estimated_product_cost - product.courier_cost - product.delivered * costs["packaging_cost_per_order"]
    st.markdown("#### Product performance"); st.dataframe(product, width="stretch", hide_index=True)
    chart_data = product[["product", "revenue", "estimated_product_cost"]].melt("product", var_name="type", value_name="amount"); st.markdown("#### Revenue versus estimated product cost"); st.altair_chart(alt.Chart(chart_data).mark_bar().encode(x=alt.X("product:N", title=None), y="amount:Q", color="type:N", xOffset="type:N", tooltip=["product", "type", "amount"]), use_container_width=True)
    if finances["estimated_net_profit"] < 0: st.error("Cash-flow warning: estimated costs exceed recognized revenue.")
    elif costs["current_cash"] < costs["planned_inventory_purchases"]: st.warning("Cash-flow warning: planned inventory exceeds current cash.")

elif section == "Pricing and Marketing Simulator":
    st.subheader("Pricing and Marketing Simulator"); tab1, tab2 = st.tabs(["Demand-sensitive pricing", "Campaign analysis"])
    with tab1:
        c1, c2, c3 = st.columns(3); mode = c1.radio("Demand input", ["Assumption profile", "Enter units by price"]); profile = c2.selectbox("Profile", ["Conservative", "Moderate", "Optimistic"], disabled=mode != "Assumption profile"); sensitivity = c3.slider("Price sensitivity", .1, 2.5, {"Conservative": 1.5, "Moderate": 1.0, "Optimistic": .6}[profile], .1)
        c1, c2, c3, c4 = st.columns(4); prices_text = c1.text_input("Prices (comma-separated)", "1800, 2000, 2500, 2800"); baseline_price = c2.number_input("Baseline price", 1.0, value=2000.0); baseline_demand = c3.number_input("Orders at baseline", 1.0, value=100.0); competitor = c4.number_input("Competitor price", 0.0, value=1800.0); cancellation = st.slider("Expected cancellation rate", 0, 50, int(finances["cancellation_rate_pct"])) / 100
        explicit = [float(x.strip()) for x in st.text_input("Expected units for each price", "125, 110, 75, 60").split(",")] if mode == "Enter units by price" else None
        try:
            result = compare_pricing([float(x.strip()) for x in prices_text.split(",")], costs["product_purchase_cost"], costs["packaging_cost_per_order"], finances["average_courier_cost"], costs["monthly_facebook_ads"] / max(len(orders), 1), costs["discount_amount"], cancellation, baseline_price, baseline_demand, sensitivity, explicit, competitor, "Medium — owner assumptions informed by courier data"); table = pd.DataFrame(result["scenarios"]); st.dataframe(table, width="stretch", hide_index=True); best = result["recommended_scenario"]
            if best: st.success(f"Recommended under these assumptions: {money(best['selling_price'])}; estimated profit {money(best['profit'])}. Not a guarantee.")
            st.altair_chart(alt.Chart(table).mark_line(point=True, color="#206b4f").encode(x=alt.X("selling_price:Q", scale=alt.Scale(zero=False)), y="profit:Q", tooltip=list(table.columns)), use_container_width=True)
            with st.expander("Assumptions and confidence"): st.json({"assumptions": result["assumptions"], "confidence": result["confidence"]})
        except ValueError as exc: st.error(str(exc))
    with tab2:
        c1, c2 = st.columns(2); campaign_type = c1.selectbox("Campaign type", ["Facebook advertising", "Influencer"]); spend = c2.number_input("Campaign spend", 0.0, value=20000.0)
        c1, c2, c3 = st.columns(3); attributed_orders = c1.number_input("Attributed orders", 0, value=25); attributed_revenue = c2.number_input("Attributed revenue", 0.0, value=62500.0); contribution = c3.number_input("Contribution per order", 0.0, value=700.0); st.json(analyze_marketing_campaign(campaign_type, spend, attributed_orders, attributed_revenue, contribution))

elif section == "Cash-Flow Forecast":
    st.subheader("Cash-Flow Forecast"); c1, c2, c3 = st.columns(3); monthly_sales = c1.number_input("Expected monthly sales", 0.0, value=float(finances["total_recognized_revenue"] / 6)); variable = c2.number_input("Monthly variable costs", 0.0, value=float((finances["product_cost"] + finances["courier_cost"] + finances["packaging_cost"]) / 6)); payment = c3.number_input("Monthly financing payment", 0.0, value=0.0); c1, c2 = st.columns(2); growth = c1.slider("Monthly growth", 0, 20, 2) / 100; months = c2.slider("Forecast months", 3, 12, 3)
    forecast = forecast_cash(costs["current_cash"], monthly_sales, variable, costs["monthly_facebook_ads"], costs["planned_inventory_purchases"], costs["other_monthly_expenses"], payment, growth, months); frame = pd.DataFrame(forecast["forecast"])
    for alert in forecast["alerts"]: st.error(alert)
    if not forecast["alerts"]: st.success("No shortage detected under current assumptions.")
    st.altair_chart(alt.Chart(frame).mark_line(point=True).encode(x="month:N", y="closing_cash:Q", tooltip=list(frame.columns)), use_container_width=True); st.dataframe(frame, width="stretch", hide_index=True); st.write("**Suggested actions:**", " ".join(forecast["suggested_actions"]))

elif section == "Financing Options":
    st.subheader("Financing Options"); c1, c2, c3 = st.columns(3); amount = c1.number_input("Funding needed", 1.0, value=100000.0); term = c2.slider("Term (months)", 1, 24, 12); revenue = c3.number_input("Expected monthly revenue", 0.0, value=max(1.0, float(finances["total_recognized_revenue"] / 6))); result = compare_financing(amount, term, revenue); st.dataframe(pd.DataFrame(result["options"]), width="stretch", hide_index=True); st.warning(result["educational_notice"]); st.info("Owner confirmation is required before any simulated next step. BizPilot cannot apply for financing.")

elif section == "Data Upload":
    st.subheader("Data Upload"); st.info("Do not upload names, phone numbers, emails, or full addresses. If present, those columns are removed locally and never sent to OpenAI."); st.download_button("Download courier CSV template", template_csv(), "courier_orders_template.csv", "text/csv"); upload = st.file_uploader("Upload Steadfast CSV or Excel (maximum 5 MB)", type=["csv", "xlsx", "xls"])
    if upload:
        try:
            cleaned, removed = load_upload(upload); st.session_state.orders = cleaned; st.session_state.data_source = upload.name
            if removed: st.warning("Ignored personal-information columns: " + ", ".join(removed))
            st.success(f"Loaded {len(cleaned)} anonymized orders."); st.dataframe(cleaned.head(25), width="stretch", hide_index=True)
        except Exception as exc: st.error(str(exc))
    if st.button("Restore default screenshot extract"): st.session_state.orders = default_data(); st.session_state.data_source = DEFAULT_SOURCE_LABEL; st.rerun()

else:
    st.subheader("Agent Activity Log"); st.caption("Anonymized execution evidence. API keys and customer personal information are never logged.")
    if not st.session_state.activity_log: st.info("No agent tools have run in this session yet.")
    for entry in reversed(st.session_state.activity_log):
        with st.expander(f'{entry["timestamp"]} · {entry["tool_selected"]}'):
            st.write("**Question:**", entry["user_question"]); st.write("**Sanitized inputs:**"); st.json(entry["sanitized_tool_inputs"]); st.write("**Result:**", entry["tool_result_summary"]); st.write("**Confirmation required:**", entry["confirmation_required"]); st.write("**Status:**", entry["final_status"])
    if st.session_state.activity_log: st.download_button("Download anonymized activity log", pd.DataFrame(st.session_state.activity_log).to_csv(index=False).encode(), "bizpilot_activity_log.csv", "text/csv")
