from meeting_copilot.live.server import LiveHub


def test_live_hub_publish_subscribe():
    hub = LiveHub()
    q = hub.subscribe()
    hub.publish({"text": "hello", "translated": "안녕", "lang": "en", "target_lang": "ko", "partial": False})
    data = q.get_nowait()
    assert "hello" in data
    assert "안녕" in data


def test_resolve_lang():
    from meeting_copilot.live.translate_fast import resolve_lang

    assert resolve_lang("ko")[0] == "ko"
    assert resolve_lang("english")[0] == "en"
