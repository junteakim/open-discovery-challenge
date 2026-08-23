from meeting_copilot.ontology import normalize_ontology, ontology_prompt_block


def test_json_ld_graph():
    raw = {
        "@context": "https://schema.org",
        "@graph": [
            {"@id": "ex:foo", "@type": "Organization", "name": "Foo Inc"},
        ],
        "terms": {"API": "Application programming interface"},
    }
    norm = normalize_ontology(raw)
    assert norm["format"] == "json-ld"
    assert len(norm["entities"]) == 1
    block = ontology_prompt_block(raw)
    assert "API" in block
    assert "Foo" in block or "ex:foo" in block
