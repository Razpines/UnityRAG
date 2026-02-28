import sqlite3

from unity_docs_mcp.index.fts import search_fts


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, responses):
        self.responses = responses
        self.seen_queries = []

    def execute(self, _sql, params):
        query = params[0]
        self.seen_queries.append(query)
        response = self.responses.get(query, [])
        if isinstance(response, Exception):
            raise response
        return _FakeCursor(response)


def test_search_fts_returns_raw_hits_without_fallback():
    conn = _FakeConn(
        {
            "Rigidbody.AddForce": [("chunk-1", 0.1)],
        }
    )
    result = search_fts(conn, "Rigidbody.AddForce", limit=3)

    assert result == [("chunk-1", 0.1)]
    assert conn.seen_queries == ["Rigidbody.AddForce"]


def test_search_fts_retries_sanitized_query_after_zero_hit():
    conn = _FakeConn(
        {
            "Rigidbody.AddForce": [],
            "Rigidbody AddForce": [("chunk-2", 0.2)],
        }
    )
    result = search_fts(conn, "Rigidbody.AddForce", limit=3)

    assert result == [("chunk-2", 0.2)]
    assert conn.seen_queries == ["Rigidbody.AddForce", "Rigidbody AddForce"]


def test_search_fts_retries_next_variant_after_operational_error():
    conn = _FakeConn(
        {
            "List<Vector3>": sqlite3.OperationalError("malformed MATCH expression"),
            "List Vector3": [("chunk-3", 0.3)],
        }
    )
    result = search_fts(conn, "List<Vector3>", limit=3)

    assert result == [("chunk-3", 0.3)]
    assert conn.seen_queries == ["List<Vector3>", "List Vector3"]
