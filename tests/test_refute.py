from devils_receipt.refute import merge, ungrounded_quotes

ITEMS = [
    {"url": "a", "relevance": 0.2, "date": "2026-01-01",
     "title": "Corn crop cut sharply", "body": "yields collapse this season"},
    {"url": "a", "relevance": 0.9, "date": "2026-02-01"},          # dup url -> dropped
    {"url": "b", "relevance": 0.9, "date": "2026-01-02", "title": "x", "body": "y"},
    {"relevance": 0.99, "title": "no url"},                         # urlless -> dropped
]


def test_merge_dedupes_and_ranks():
    out = merge(ITEMS)
    assert [it["url"] for it in out] == ["b", "a"]  # url 'a' kept once, ranked by relevance


def test_ungrounded_quotes_passes_real_quote():
    assert ungrounded_quotes('he said "yields collapse this season"', ITEMS) == []


def test_ungrounded_quotes_flags_fabrication():
    assert ungrounded_quotes('"a totally fabricated sentence right here"', ITEMS)


def test_short_quotes_ignored():
    # < 4 words is not a citation-grade quote
    assert ungrounded_quotes('"too short here"', ITEMS) == []
