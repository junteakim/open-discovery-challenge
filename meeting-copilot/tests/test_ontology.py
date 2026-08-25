from meeting_copilot.ontology import extract_matched_terms, glossary_for_ui, normalize_ontology


def test_glossary_for_ui(tmp_path):
    ctx = tmp_path / "context"
    ctx.mkdir()
    (ctx / "ontology.json").write_text(
        '{"terms": {"QBR": "Quarterly review"}, '
        '"entities": [{"labels": {"en": "Company X"}, "facts": ["Series B"]}]}',
        encoding="utf-8",
    )
    items = glossary_for_ui(str(ctx))
    assert any(i["term"] == "QBR" for i in items)


def test_extract_matched_terms(tmp_path):
    ctx = tmp_path / "context"
    ctx.mkdir()
    (ctx / "ontology.json").write_text('{"terms": {"QBR": "Quarterly review"}}', encoding="utf-8")
    matched = extract_matched_terms("We discussed the QBR timeline", str(ctx))
    assert "QBR" in matched


def test_normalize_json_ld():
    raw = {"@graph": [{"@id": "ex:1", "name": "Test"}], "terms": {"API": "interface"}}
    norm = normalize_ontology(raw)
    assert norm["format"] == "json-ld"
