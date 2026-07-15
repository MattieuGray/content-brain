import pytest
import corpus_pass as cp


def test_extract_json_plain():
    assert cp.extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_fence():
    assert cp.extract_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_extract_json_with_prose_around():
    s = 'Sure, here it is:\n{"a": 3, "b": [1,2]}\nHope that helps!'
    assert cp.extract_json(s) == {"a": 3, "b": [1, 2]}


def test_extract_json_nested_braces():
    assert cp.extract_json('noise {"a": {"b": 1}} noise') == {"a": {"b": 1}}


def test_extract_json_raises_on_none():
    with pytest.raises(ValueError):
        cp.extract_json(None)


def test_extract_json_raises_when_absent():
    with pytest.raises(ValueError):
        cp.extract_json("no json here")
