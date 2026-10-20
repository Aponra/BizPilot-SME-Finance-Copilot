"""Validate and sanitize Steadfast-style courier uploads."""
from pathlib import Path
import pandas as pd
from finance import generate_sample_orders
from privacy import remove_personal_information

REQUIRED_COLUMNS = {"order_id", "order_date", "product", "cod_amount", "courier_charge", "status", "settlement_status"}
OPTIONAL_COLUMNS = {"source_note"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_WORKBOOK = Path(__file__).parent / "data" / "bengal_boots_steadfast_screenshot_extract.xlsx"
DEFAULT_SOURCE_LABEL = "Partial anonymized Steadfast screenshot extract"
DEFAULT_SOURCE_WARNING = "This file contains only the rows visible in the source screenshots. It is not the complete Steadfast history."
STATUS_MAP = {"delivered": "Delivered", "cancelled": "Cancelled", "canceled": "Cancelled", "partial delivery": "Partial delivery", "partial delivered": "Partial delivery", "pending": "Pending", "in review": "In review", "exceptional": "Exceptional"}

def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(); result.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in result.columns]; return result

def validate_and_clean(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    frame, removed = remove_personal_information(normalize_columns(frame)); missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing: raise ValueError("Missing required columns: " + ", ".join(missing))
    selected = sorted(REQUIRED_COLUMNS | (OPTIONAL_COLUMNS & set(frame.columns)))
    cleaned = frame[selected].copy(); cleaned["order_date"] = pd.to_datetime(cleaned["order_date"], errors="coerce")
    for column in ("cod_amount", "courier_charge"): cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    if cleaned[["order_date", "cod_amount", "courier_charge"]].isna().any().any(): raise ValueError("Dates and numeric fields must contain valid values")
    if (cleaned[["cod_amount", "courier_charge"]] < 0).any().any(): raise ValueError("COD amounts and courier charges cannot be negative")
    cleaned["status"] = cleaned["status"].astype(str).str.strip().str.lower().map(STATUS_MAP)
    if cleaned["status"].isna().any(): raise ValueError("One or more courier statuses are not recognized")
    for column in ("order_id", "product", "settlement_status"):
        cleaned[column] = cleaned[column].astype(str).str.strip()
        if cleaned[column].eq("").any(): raise ValueError(f"{column} cannot be blank")
    cleaned.loc[cleaned["product"].str.casefold().eq("unknown"), "product"] = pd.NA
    cleaned["review_flag"] = ""
    cleaned.loc[cleaned["cod_amount"].eq(0), "review_flag"] = "Zero COD value — review source anomaly"
    return cleaned.sort_values("order_date").reset_index(drop=True), removed

def load_upload(uploaded_file) -> tuple[pd.DataFrame, list[str]]:
    if getattr(uploaded_file, "size", 0) > MAX_UPLOAD_BYTES: raise ValueError("File is larger than the 5 MB upload limit")
    name = str(uploaded_file.name).lower()
    if name.endswith(".csv"): raw = pd.read_csv(uploaded_file)
    elif name.endswith((".xlsx", ".xls")): raw = pd.read_excel(uploaded_file)
    else: raise ValueError("Upload a CSV or Excel file")
    return validate_and_clean(raw)

def sample_data() -> pd.DataFrame: return generate_sample_orders()

def default_data() -> pd.DataFrame:
    """Load the bundled partial screenshot extract from its Orders worksheet."""
    raw = pd.read_excel(DEFAULT_WORKBOOK, sheet_name="Orders")
    cleaned, _ = validate_and_clean(raw)
    return cleaned

def template_csv() -> bytes:
    return pd.DataFrame([{"order_id": "BB-00001", "order_date": "2026-10-01", "product": "Bengal Leather Boot", "cod_amount": 3600, "courier_charge": 100, "status": "Delivered", "settlement_status": "Settled"}]).to_csv(index=False).encode()
