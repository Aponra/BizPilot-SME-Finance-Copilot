import pandas as pd
import pytest
from data_loader import DEFAULT_SOURCE_LABEL, DEFAULT_SOURCE_WARNING, default_data, validate_and_clean
from privacy import redact_text

def valid_frame():
    return pd.DataFrame([{"order_id":"1","order_date":"2026-01-01","product":"Boot","cod_amount":2000,"courier_charge":100,"status":"delivered","settlement_status":"settled"}])

def test_personal_information_is_removed():
    frame = valid_frame(); frame["customer_name"] = ["Private Person"]; frame["phone"] = ["01700000000"]
    cleaned, removed = validate_and_clean(frame)
    assert "customer_name" in removed and "phone" in removed
    assert "customer_name" not in cleaned.columns and "phone" not in cleaned.columns

def test_missing_column_rejected():
    with pytest.raises(ValueError, match="Missing required columns"): validate_and_clean(valid_frame().drop(columns="product"))

def test_negative_numeric_value_rejected():
    frame = valid_frame(); frame.loc[0, "cod_amount"] = -1
    with pytest.raises(ValueError): validate_and_clean(frame)

def test_unknown_status_rejected():
    frame = valid_frame(); frame.loc[0, "status"] = "mystery"
    with pytest.raises(ValueError): validate_and_clean(frame)

def test_chat_text_redaction():
    value = redact_text("Customer 01712345678 uses a@b.com")
    assert "01712345678" not in value and "a@b.com" not in value

def test_default_screenshot_extract_is_loaded_and_limited():
    frame = default_data()
    assert len(frame) == 65
    assert frame["product"].isna().all()
    assert frame["cod_amount"].eq(0).sum() == 1
    assert frame.loc[frame["cod_amount"].eq(0), "review_flag"].str.contains("review").all()
    assert DEFAULT_SOURCE_LABEL == "Partial anonymized Steadfast screenshot extract"
    assert "only the rows visible" in DEFAULT_SOURCE_WARNING

def test_source_note_is_preserved_when_present():
    frame = valid_frame(); frame["source_note"] = "Screenshot extract; PII removed"
    cleaned, _ = validate_and_clean(frame)
    assert cleaned.loc[0, "source_note"] == "Screenshot extract; PII removed"
