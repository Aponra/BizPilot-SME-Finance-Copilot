# BizPilot — Bengal Boots SME Finance Copilot

BizPilot is a presentation-ready Streamlit application for **Topic E: SME
Finance Copilot**. It helps Bengal Boots, a real small online footwear business,
understand profitability, courier performance, pricing demand, marketing
efficiency, cash risk, and simulated financing choices.

BizPilot is an educational decision-support application. Forecasts, pricing
scenarios, and financing comparisons are simulations; the included anonymized
courier extract is real business data. BizPilot cannot move money, apply for a
loan, purchase inventory, or guarantee a financial result.

## Main features

1. **AI Finance Copilot** — a real chat interface using the official OpenAI
   Python SDK, Responses API, and six calculation tools.
2. **Business Dashboard** — delivered revenue, estimated costs/profit, margins,
   courier KPIs, monthly trends, and product performance.
3. **Pricing and Marketing Simulator** — owner-entered demand or transparent
   price-sensitivity profiles, cancellation risk, competitor price, CAC, ROAS,
   campaign profit, and break-even analysis.
4. **Cash-Flow Forecast** — 3–12 month forecast, visible shortage alerts, and
   suggested actions.
5. **Financing Options** — simulated small-business loan, supplier credit,
   revenue-based finance, and no-financing comparisons.
6. **Data Upload** — validated Steadfast-style CSV/XLSX uploads with automatic
   removal of personal-information columns.
7. **Agent Activity Log** — expandable, downloadable, anonymized tool evidence.

## Architecture and agent workflow

```text
User question
  → Responses API chooses a declared tool
  → local Python function performs every calculation
  → aggregated tool result returns to the model
  → model explains facts, assumptions, estimates, and limitations
  → sanitized activity entry is recorded
```

Key files:

```text
app.py                       Streamlit interface and seven sections
agent.py                     Responses API function-calling loop
tools.py                     Tool schemas, routing, and dispatch
finance.py                   Deterministic financial calculations
data_loader.py               Upload parsing and validation
privacy.py                   PII column removal and chat redaction
sample_data.csv              Small visible anonymous sample
data/bengal_boots_steadfast_screenshot_extract.xlsx
                              Default partial anonymized Steadfast extract
courier_orders_template.csv  Downloadable upload template
tests/                       Calculation, privacy, routing, and mocked API tests
```

The model never calculates financial figures itself. Tool results contain only
aggregates or simulation inputs; raw courier rows are not included in API calls.

## Courier upload format

CSV and Excel files up to 5 MB are accepted. Required columns are:

| Column | Meaning |
|---|---|
| `order_id` | Non-personal order reference |
| `order_date` | Parseable order date |
| `product` | Product name or SKU |
| `cod_amount` | Non-negative COD amount |
| `courier_charge` | Non-negative courier charge |
| `status` | Delivered, Cancelled, Partial delivery, Pending, In review, or Exceptional |
| `settlement_status` | Settlement state |

Download `courier_orders_template.csv` inside the app. Never add customer names,
phone numbers, email addresses, or full addresses.

## Default dataset and date ranges

BizPilot starts with the `Orders` worksheet from the bundled anonymized workbook
and labels it **Partial anonymized Steadfast screenshot extract**. It contains
only the rows visible in the source screenshots and is not the complete Steadfast
history. A CSV or Excel upload temporarily replaces it for the current Streamlit
session; the default can be restored from the Data Upload page.

The sidebar date selector controls dashboard calculations and the data available
to AI tools. For the selected range, BizPilot calculates order outcomes, COD
sales and losses, partial collections, courier charges, net delivered COD,
average delivered value, success/cancellation rates, and daily/monthly trends.
`Unknown` products are displayed as missing product information. Zero COD values
remain in the source and receive a visible review flag instead of being removed.
The default average product buying-cost assumption is ৳1,100 per delivered
order and can be adjusted in the sidebar. Cancelled/returned footwear remains
saleable, so its purchase cost is not recognized again. Recorded courier charges
remain costs. Partial-delivery COD is counted as collected, but partial product
cost is excluded when the fulfilled quantity is unknown. All other owner-entered
expenses default to zero until actual values are supplied.

## Privacy protections

- Name, phone, mobile, address, email, customer, recipient, and contact columns
  are removed locally and trigger a visible warning.
- Common phone numbers and email addresses typed into chat are redacted.
- Only aggregated tool results are returned to the model.
- API keys are read from the environment, never displayed or logged.
- `.env` is git-ignored and the activity export is anonymized.

## Installation

Python 3.9 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\Activate.ps1`.

## Optional OpenAI setup

BizPilot works in dashboard-only mode without an API key. To enable AI chat:

```bash
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY` to your own secret. Set `OPENAI_MODEL` to a
model available to your OpenAI project. The example value is configurable and is
not hardcoded in application code. Restart Streamlit after changing `.env`.

Use the sidebar's **Test AI connection** button after restarting. The test sends
only a fixed connection-check message—no courier records, customer information,
financial totals, activity logs, or API key. Missing or invalid credentials show
a friendly error and do not stop the dashboard.

If a key has ever been pasted into chat, source code, or another shared location,
revoke it and create a replacement before adding it to `.env`.

The integration follows the official OpenAI Responses API function-calling
workflow documented in the [OpenAI function-calling guide](https://platform.openai.com/docs/guides/function-calling).

## Run and test

```bash
streamlit run app.py
```

Open <http://localhost:8501>. To run the complete tests:

```bash
python -m pytest -q
```

OpenAI calls are mocked in tests, so tests do not consume API credits.

## Deployment

BizPilot can be deployed from this repository on a Python-compatible Streamlit
host such as Streamlit Community Cloud:

1. Fork or select this repository in the hosting dashboard.
2. Set the application entry point to `app.py`.
3. Install dependencies from `requirements.txt`.
4. Add `OPENAI_API_KEY` and `OPENAI_MODEL` through the host's encrypted secrets
   or environment-variable settings. Never commit a populated `.env` file.
5. Start the application with `streamlit run app.py` and verify the health and
   **Test AI connection** controls.

Without `OPENAI_API_KEY`, the deployed dashboard, simulators, forecasts, upload
validation, and privacy controls continue to work; only live AI chat is disabled.
The included workbook is anonymized demonstration evidence, not complete
Steadfast history. Do not deploy customer PII or raw courier screenshots.

## Demo questions

- How is my business performing?
- What was my delivery success rate?
- How much COD value was lost through cancellations?
- Should I reduce my price from ৳2,000 to ৳1,800?
- Can I afford a ৳20,000 Facebook campaign?
- Was an influencer campaign profitable?
- Which product should I restock?
- Can I offer free delivery?
- Will I face a cash shortage next month?
- Which financing option is suitable for me?

## Limitations and disclaimer

Demand curves, partial-delivery recognition, campaign attribution, financing
rates, and future cash flows are simulations based on explicit assumptions, not
forecasts or real offers. The included Steadfast data is a partial, anonymized,
screenshot-derived extract from the real business; it is not the complete
business history. Uploaded data quality directly affects the analysis. BizPilot
provides educational decision support, not accounting,
investment, lending, legal, or tax advice. An owner must confirm every proposed
simulated action and independently verify decisions with qualified professionals.
