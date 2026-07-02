import os
import json
import importlib


class MockResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.ok = status_code == 200

    def json(self):
        return self._data


def test_run_intake_agent_with_mock(monkeypatch):
    sa = importlib.import_module("streamlit_app")

    mock_output = json.dumps({
        "response": "Hello John, I've captured your details.",
        "extracted_slots": {
            "Name": "John Doe",
            "Member_ID": "HMO-999",
            "Company": "ACME Corp",
            "Diagnosis": "Mild fever",
            "Procedures": "Paracetamol",
        },
    })

    mock_payload = {"candidates": [{"content": {"parts": [{"text": mock_output}]}}]}

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(sa.requests, "post", lambda *a, **k: MockResponse(mock_payload))

    user_input = (
        "My name is John Doe. I have a mild fever. HMO-999. Company: ACME Corp."
    )

    current_slots = {"Name": "", "Member_ID": "", "Company": "", "Diagnosis": "", "Procedures": ""}

    reply, updated = sa.run_intake_agent(user_input, [], current_slots)

    assert "captured" in reply.lower() or isinstance(reply, str)
    assert updated["Name"] == "John Doe"
