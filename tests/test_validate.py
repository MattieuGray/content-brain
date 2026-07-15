import corpus_pass as cp

TAG_SPEC = {
    "columns": ["pillars", "keywords", "summary"],
    "list_fields": ["pillars", "keywords"],
    "allowed_values": {"pillars": ["Owner Financing", "Exits", "Leverage"]},
    "id_field": "note_id",
}


def test_validate_row_all_valid():
    row = {"pillars": ["Owner Financing", "Exits"], "keywords": ["notes"], "summary": "x"}
    out, viol = cp.validate_row(dict(row), TAG_SPEC)
    assert out["pillars"] == ["Owner Financing", "Exits"]
    assert viol == []


def test_validate_row_coerces_unknown_list_value():
    row = {"pillars": ["Owner Financing", "Bogus"], "keywords": [], "summary": "x"}
    out, viol = cp.validate_row(row, TAG_SPEC)
    assert out["pillars"] == ["Owner Financing", "other"]
    assert viol == ["pillars=Bogus"]


def test_validate_row_scalar_categorical():
    spec = {
        "columns": ["register"],
        "list_fields": [],
        "allowed_values": {"register": ["plain", "casual"]},
        "id_field": "id",
    }
    out, viol = cp.validate_row({"register": "corporate"}, spec)
    assert out["register"] == "other"
    assert viol == ["register=corporate"]


def test_validate_row_keywords_not_validated():
    row = {"pillars": ["Exits"], "keywords": ["anything", "goes"], "summary": "x"}
    out, viol = cp.validate_row(row, TAG_SPEC)
    assert out["keywords"] == ["anything", "goes"]
    assert viol == []


def test_validate_row_handles_string_for_list_field():
    row = {"pillars": "Owner Financing", "keywords": [], "summary": "x"}
    out, viol = cp.validate_row(row, TAG_SPEC)
    assert out["pillars"] == ["Owner Financing"]
    assert viol == []
