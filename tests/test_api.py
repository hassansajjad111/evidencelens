"""Unit tests for API routing decisions without requiring live store services.

Mock retrievers make these tests fast and deterministic; they protect the key
contract that requested modes call only their relevant backend and unimplemented
answer generation never returns fabricated text.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from evidencelens.api import main


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "expected_calls"),
    [
        ("bm25", ["bm25"]),
        ("dense", ["dense"]),
        ("hybrid", ["bm25", "dense"]),
    ],
)
async def test_search_dispatches_selected_retrievers(monkeypatch, mode, expected_calls):
    """Assert each search mode calls only its intended retriever(s)."""
    calls = []

    async def lexical(*args, **kwargs):
        calls.append("bm25")
        return ["chunk-a", "chunk-b"]

    async def dense(*args, **kwargs):
        calls.append("dense")
        return ["chunk-b", "chunk-c"]

    monkeypatch.setattr(main, "search_lexical", lexical)
    monkeypatch.setattr(main, "search_dense", dense)
    container = SimpleNamespace(
        es=object(),
        qc=object(),
        settings=SimpleNamespace(embed_model="BAAI/bge-small-en-v1.5"),
    )

    response = await main.search(main.SearchReq(query="diabetes", mode=mode), container)

    assert calls == expected_calls
    assert response["mode"] == mode
    assert response["results"]


def test_search_rejects_unimplemented_graph_mode():
    """Reject graph mode rather than suggesting graph retrieval is already wired."""
    with pytest.raises(ValidationError):
        main.SearchReq(query="diabetes", mode="graph")


@pytest.mark.asyncio
async def test_ask_does_not_return_a_hard_coded_answer():
    """Keep the unfinished RAG endpoint honest until grounded generation exists."""
    with pytest.raises(HTTPException) as exc_info:
        await main.ask(main.AskReq(question="What does the evidence say?"))

    assert exc_info.value.status_code == 501
