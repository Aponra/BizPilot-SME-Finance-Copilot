from types import SimpleNamespace
from agent import api_configuration, ask_copilot, test_ai_connection as check_ai_connection
from finance import DEFAULT_COSTS, generate_sample_orders
from tools import route_question

def test_missing_api_key_behavior():
    config = api_configuration({}); assert config["enabled"] is False; assert "OPENAI_API_KEY" in config["message"]

def test_connection_missing_key_is_friendly(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    result = check_ai_connection()
    assert result["ok"] is False and "missing" in result["message"].lower()

class FailingResponses:
    def create(self, **kwargs): raise RuntimeError("invalid secret details must not escape")

def test_connection_invalid_key_is_friendly_and_does_not_echo_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder"); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    result = check_ai_connection(SimpleNamespace(responses=FailingResponses()))
    assert result["ok"] is False and "invalid secret details" not in result["message"]

def test_connection_success_sends_no_business_data(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder"); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    fake = SimpleNamespace(responses=FakeResponses())
    result = check_ai_connection(fake)
    assert result["ok"] is True
    request = fake.responses.calls[0]
    assert request["input"] == "Reply with exactly: connection successful"
    assert request["max_output_tokens"] == 32
    assert "tools" not in request

def test_connection_reports_inactive_billing_without_provider_text(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder"); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    error = type("SafeBillingError", (Exception,), {"code": "billing_not_active", "status_code": 429})
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(error("private provider text"))))
    result = check_ai_connection(client)
    assert result["ok"] is False and "billing is not active" in result["message"]
    assert "private provider text" not in result["message"]

def test_connection_reports_rate_limit_without_provider_text(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder"); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    error = type("RateLimitError", (Exception,), {"status_code": 429})
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(error("private provider text"))))
    result = check_ai_connection(client)
    assert result["ok"] is False and "quota or rate limit" in result["message"]
    assert "private provider text" not in result["message"]

def test_tool_routing():
    assert route_question("Will I face a cash shortage?") == "forecast_cash_flow"
    assert route_question("Should I lower my price?") == "compare_pricing_scenarios"
    assert route_question("How am I performing?") == "analyze_business_finances"

class FakeResponses:
    def __init__(self): self.calls = []
    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            call = SimpleNamespace(type="function_call", name="analyze_business_finances", arguments="{}", call_id="call-1")
            return SimpleNamespace(output=[call], output_text="")
        return SimpleNamespace(output=[], output_text="Calculated from the finance tool.")

def test_responses_api_tool_call_is_mocked(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False); monkeypatch.delenv("OPENAI_MODEL", raising=False)
    fake = SimpleNamespace(responses=FakeResponses()); logs = []
    answer = ask_copilot("How am I doing?", [], generate_sample_orders(10), DEFAULT_COSTS, client=fake, logger=logs.append)
    assert "Calculated" in answer and "analyze_business_finances" in answer
    assert len(fake.responses.calls) == 2 and logs[0]["tool_selected"] == "analyze_business_finances"

def test_mock_call_redacts_phone():
    fake = SimpleNamespace(responses=FakeResponses()); ask_copilot("Customer 01712345678 performance", [], generate_sample_orders(5), DEFAULT_COSTS, client=fake)
    assert "01712345678" not in str(fake.responses.calls)

def test_rate_limit_uses_local_finance_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder"); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    error = type("RateLimitError", (Exception,), {"status_code": 429})
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(error("do not expose"))))
    logs = []
    answer = ask_copilot("How is business going?", [], generate_sample_orders(10), DEFAULT_COSTS, client=client, logger=logs.append)
    assert "deterministic finance tool locally" in answer
    assert "analyze_business_finances" in answer
    assert "do not expose" not in answer
    assert logs[0]["final_status"] == "completed_locally_after_api_limit"

def test_rate_limit_routes_assumption_heavy_questions_to_simulator(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder"); monkeypatch.setenv("OPENAI_MODEL", "gpt-5-mini")
    error = type("RateLimitError", (Exception,), {"status_code": 429})
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: (_ for _ in ()).throw(error())))
    answer = ask_copilot("Should I lower my price?", [], generate_sample_orders(10), DEFAULT_COSTS, client=client)
    assert "Pricing and Marketing Simulator" in answer
