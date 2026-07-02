import json
import importlib


def test_run_document_generator_all_fields():
    with open("references/department-field-requirements.json") as f:
        dept_config = json.load(f)

    extracted_slots = {
        "Name": "John Doe",
        "Member_ID": "HMO123456",
        "Company": "ACME Corp",
        "Diagnosis": "Fever and cough",
        "Procedures": "CBC, Chest X-ray",
    }

    sa = importlib.import_module("streamlit_app")

    for dept in dept_config.keys():
        rendered, missing = sa.run_document_generator(dept, extracted_slots, dept_config)
        assert isinstance(rendered, str)
        assert missing == []
