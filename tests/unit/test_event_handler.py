from src.infrastructure.adapters.agent.event_handler import EventHandler


def test_event_handler_stream_queue():
    class DummyText:
        def __init__(self, value):
            self.text = {"value": value}

    class DummyDelta:
        def __init__(self, content):
            self.content = content

    class DummyChunk:
        def __init__(self, value):
            self.text = {"value": value}

    class DummyMessageDelta:
        def __init__(self, value, msg_id="m1"):
            self.id = msg_id
            self.delta = DummyDelta([DummyChunk(value)])

    handler = EventHandler()
    handler.on_message_delta(DummyMessageDelta("hi"))

    assert handler.has_chunks() is True
    chunks = list(handler.get_stream_chunks())
    assert chunks == ["hi"]
    assert handler.has_chunks() is False
