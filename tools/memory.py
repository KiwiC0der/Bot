#!/usr/bin/env python3
"""
ChromaDB vector memory for Nova V2. Embeddings via Ollama nomic-embed-text.
Env:
  NOVA_OLLAMA_BASE_URL (default http://172.27.80.201:11434)
  NOVA_CHROMA_PATH (default ~/Bot/.chroma)
  NOVA_BOT_ROOT (default ~/Bot) — used only for default chroma path
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

COLLECTION = "nova_memory"


def _bot_root() -> Path:
    return Path(os.path.expanduser(os.environ.get("NOVA_BOT_ROOT", "~/Bot"))).resolve()


def _chroma_path() -> Path:
    env = os.environ.get("NOVA_CHROMA_PATH")
    if env:
        return Path(os.path.expanduser(env)).resolve()
    return (_bot_root() / ".chroma").resolve()


def _ollama_url() -> str:
    return os.environ.get("NOVA_OLLAMA_BASE_URL", "http://172.27.80.201:11434").rstrip("/")


def _client():
    import chromadb
    from chromadb.utils import embedding_functions

    path = _chroma_path()
    path.mkdir(parents=True, exist_ok=True)
    ef = embedding_functions.OllamaEmbeddingFunction(
        url_base=_ollama_url(),
        model_name="nomic-embed-text:latest",
    )
    return chromadb.PersistentClient(path=str(path)), ef


def get_collection():
    client, ef = _client()
    return client.get_or_create_collection(name=COLLECTION, embedding_function=ef)


def add_memory(content: str, metadata: dict[str, Any] | None = None) -> str:
    """Insert one document; returns Chroma id."""
    col = get_collection()
    import uuid

    doc_id = str(uuid.uuid4())
    meta = dict(metadata or {})
    col.add(ids=[doc_id], documents=[content], metadatas=[meta])
    return doc_id


def search_memory(query: str, n: int = 5) -> list[dict[str, Any]]:
    col = get_collection()
    res = col.query(query_texts=[query], n_results=n)
    out: list[dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0] if res.get("distances") else [None] * len(ids)
    for i, doc_id in enumerate(ids):
        out.append(
            {
                "id": doc_id,
                "document": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Nova Chroma memory (Ollama embeddings)")
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add", help="Add a memory line")
    pa.add_argument("text")
    pa.add_argument("--meta", default="{}", help="JSON object metadata")
    ps = sub.add_parser("search", help="Search memories")
    ps.add_argument("query")
    ps.add_argument("-n", type=int, default=5)
    args = p.parse_args()
    if args.cmd == "add":
        meta = json.loads(args.meta)
        doc_id = add_memory(args.text, meta)
        print(doc_id)
    else:
        for row in search_memory(args.query, n=args.n):
            print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
