import pandas as pd
import pytest
from finance import DEFAULT_COSTS, analyze_finances, compare_financing, compare_pricing, date_range_metrics, forecast_cash, generate_sample_orders

def test_sample_orders_are_repeatable_and_anonymous():
    first = generate_sample_orders(20, 7); second = generate_sample_orders(20, 7)
    pd.testing.assert_frame_equal(first, second); assert len(first) == 20
    assert set(first.columns) == {"order_id", "order_date", "product", "cod_amount", "courier_charge", "status", "settlement_status"}

def test_bengal_boots_default_average_buying_price():
    assert DEFAULT_COSTS["product_purchase_cost"] == 1100

def test_financial_calculations_and_statuses():
    orders = pd.DataFrame([
        {"order_id":"1","order_date":"2026-01-01","product":"Boot","cod_amount":2000,"courier_charge":100,"status":"Delivered","settlement_status":"Settled"},
        {"order_id":"2","order_date":"2026-01-02","product":"Boot","cod_amount":2000,"courier_charge":100,"status":"Cancelled","settlement_status":"Unsettled"},
        {"order_id":"3","order_date":"2026-01-03","product":"Boot","cod_amount":2000,"courier_charge":100,"status":"Partial delivery","settlement_status":"Unsettled"},])
    costs = DEFAULT_COSTS | {"product_purchase_cost": 1000, "packaging_cost_per_order": 50, "monthly_facebook_ads": 0, "influencer_expense": 0, "discount_amount": 0, "return_related_cost": 100, "other_monthly_expenses": 0}
    result = analyze_finances(orders, costs)
    assert result["total_recognized_revenue"] == 4000; assert result["delivered_orders"] == 1
    assert result["cancelled_orders"] == 1; assert result["partial_deliveries"] == 1
    assert result["delivery_success_rate_pct"] == pytest.approx(33.33)
    assert result["product_cost"] == 1000
    assert result["courier_cost"] == 300

def test_cancelled_resaleable_parcel_does_not_consume_product_cost():
    orders = pd.DataFrame([{"order_id":"1","order_date":"2026-01-01","product":"Boot","cod_amount":2000,"courier_charge":100,"status":"Cancelled","settlement_status":"Unsettled"}])
    result = analyze_finances(orders, DEFAULT_COSTS)
    assert result["product_cost"] == 0
    assert result["total_recognized_revenue"] == 0
    assert result["courier_cost"] == 100

def test_pricing_demand_changes_and_recommendation():
    result = compare_pricing([1800, 2500], 1000, 50, 100, 100, 0, .1, 2000, 100, 1.0)
    assert result["scenarios"][0]["expected_units"] > result["scenarios"][1]["expected_units"]
    assert result["recommended_scenario"] in result["scenarios"]
    assert result["scenarios"][0]["break_even_orders"] is not None

def test_explicit_demand_must_match_prices():
    with pytest.raises(ValueError): compare_pricing([1800, 2000], 1000, 50, 100, 0, 0, .1, 2000, 100, explicit_demand=[100])

def test_cash_forecast_detects_shortage():
    result = forecast_cash(1000, 1000, 1500, 500, 500, 500, months=3)
    assert result["shortage_expected"] is True; assert len(result["forecast"]) == 3; assert result["alerts"]

def test_financing_includes_no_financing_and_costs():
    result = compare_financing(100000, 12, 100000)
    assert len(result["options"]) == 4; assert result["options"][0]["approx_total_repayment"] > 100000
    assert result["options"][-1]["option"].startswith("No financing")

@pytest.mark.parametrize("bad", [-1, float("nan")])
def test_invalid_costs_rejected(bad):
    with pytest.raises(ValueError): analyze_finances(generate_sample_orders(2), DEFAULT_COSTS | {"product_purchase_cost": bad})

def test_selected_date_range_metrics_preserve_zero_cod_and_trends():
    orders = pd.DataFrame([
        {"order_id":"1","order_date":"2026-01-01","product":pd.NA,"cod_amount":2000,"courier_charge":100,"status":"Delivered","settlement_status":"Settled"},
        {"order_id":"2","order_date":"2026-01-02","product":pd.NA,"cod_amount":0,"courier_charge":80,"status":"Cancelled","settlement_status":"Unsettled"},
        {"order_id":"3","order_date":"2026-02-01","product":pd.NA,"cod_amount":500,"courier_charge":90,"status":"Partial delivery","settlement_status":"Unsettled"},])
    result = date_range_metrics(orders)
    assert result["total_orders"] == 3; assert result["delivered_cod_sales"] == 2000
    assert result["partial_delivery_collections"] == 500
    assert result["net_delivered_cod_after_courier"] == 1900
    assert result["zero_cod_anomalies"] == 1
    assert len(result["daily_trends"]) == 3 and len(result["monthly_trends"]) == 2
