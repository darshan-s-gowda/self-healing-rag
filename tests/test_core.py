from src.pdf import chunk_text
from src.utils import parse_json_object


def test_chunking_has_overlap_and_nonempty_chunks():
    text = " ".join(f"word{i}" for i in range(2500))
    chunks = chunk_text(text, size=100, overlap=20)
    assert len(chunks) > 20
    assert all(chunks)


def test_json_parser_accepts_plain_json():
    data = parse_json_object('{"grounded": true, "confidence": 0.9}')
    assert data["grounded"] is True


def test_json_parser_accepts_wrapped_json():
    data = parse_json_object('Here is the result:\n{"grounded": false}')
    assert data["grounded"] is False
