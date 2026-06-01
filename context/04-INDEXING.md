# 04 — Indexing & Vector/Graph Stores

Covers Steps 4-6: Embedding & Vector Indexing, BM25 Sparse Indexing, Knowledge Graph Construction.

---

## Step 4 — Embedding & Vector Indexing

**File**: `clause/indexing/vector_store.py`

```python
# clause/indexing/vector_store.py

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, PayloadSchemaType
)

COLLECTION_NAME = "clause_chunks"
VECTOR_SIZE = 3072  # text-embedding-3-large output dimensions

def create_collection(client: QdrantClient):
    """
    Create Qdrant collection with named vectors and payload indexing.
    Call once on first run. Idempotent.
    """
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    # Index payload fields for filtered search
    client.create_payload_index(COLLECTION_NAME, "act", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "section_number", PayloadSchemaType.KEYWORD)
    client.create_payload_index(COLLECTION_NAME, "type", PayloadSchemaType.KEYWORD)

def build_payload(chunk: LegalChunk) -> dict:
    """
    Payload stored alongside vector in Qdrant.
    text = original text for citation display
    contextualized_text = what was embedded (for debugging)
    """
    return {
        "chunk_id": chunk.chunk_id,
        "parent_id": chunk.parent_id,
        "type": chunk.type,
        "act": chunk.act,
        "chapter": chunk.chapter,
        "section_number": chunk.section_number,
        "section_title": chunk.section_title,
        "text": chunk.text,                          # Original — shown to user
        "contextualized_text": chunk.contextualized_text,  # Embedded version
        "cross_references": chunk.cross_references,
        "tokens": chunk.tokens,
        "source_file": chunk.source_file,
    }
```

### Embedding + Upsert

```python
from openai import OpenAI
import uuid

def embed_and_upsert(chunks: list[LegalChunk], client: QdrantClient):
    """
    Embed child chunks and upsert into Qdrant in batches of 100.
    Only embed child chunks (type == "child") — parents are fetched by ID.
    """
    oai = OpenAI()
    child_chunks = [c for c in chunks if c.type == "child"]
    
    BATCH_SIZE = 100
    for i in range(0, len(child_chunks), BATCH_SIZE):
        batch = child_chunks[i:i + BATCH_SIZE]
        texts = [c.contextualized_text or c.text for c in batch]
        
        response = oai.embeddings.create(
            input=texts,
            model="text-embedding-3-large"
        )
        
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, c.chunk_id)),
                vector=response.data[j].embedding,
                payload=build_payload(c)
            )
            for j, c in enumerate(batch)
        ]
        
        client.upsert(collection_name=COLLECTION_NAME, points=points)
```

---

## Step 5 — BM25 Sparse Indexing

**File**: `clause/indexing/bm25_index.py`

```python
# clause/indexing/bm25_index.py

import pickle
from bm25s import BM25
from pathlib import Path

INDEX_PATH = "data/processed/bm25_index.pkl"

def build_bm25_index(chunks: list[LegalChunk]) -> BM25:
    """
    Build BM25 index over child chunk texts.
    Persist to disk — rebuild only when corpus changes.
    
    Stores chunk_id alongside index for retrieval mapping.
    """
    child_chunks = [c for c in chunks if c.type == "child"]
    corpus = [c.text for c in child_chunks]
    chunk_ids = [c.chunk_id for c in child_chunks]
    
    retriever = BM25()
    retriever.index(corpus)
    
    # Persist both index and chunk_id mapping
    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"index": retriever, "chunk_ids": chunk_ids, "corpus": corpus}, f)
    
    return retriever, chunk_ids

def load_bm25_index() -> tuple[BM25, list[str], list[str]]:
    with open(INDEX_PATH, "rb") as f:
        data = pickle.load(f)
    return data["index"], data["chunk_ids"], data["corpus"]

def search_bm25(query: str, top_k: int = 20) -> list[dict]:
    """
    Returns list of {chunk_id, score} dicts ranked by BM25 score.
    """
    retriever, chunk_ids, corpus = load_bm25_index()
    results, scores = retriever.retrieve([query], corpus=corpus, k=top_k)
    
    return [
        {"chunk_id": chunk_ids[idx], "score": float(score)}
        for idx, score in zip(results[0], scores[0])
    ]
```

---

## Step 6 — Knowledge Graph Construction

**Files**: `clause/ingestion/extractors/` | `clause/graph/` | `clause/indexing/graph_store.py`

### Entity Extraction

```python
# clause/ingestion/extractors/entity_extractor.py

ENTITY_EXTRACTION_PROMPT = """You are extracting structured legal entities from a section of Indian corporate law.

Section text:
<section>
{section_text}
</section>

Extract all entities of these types. Return ONLY valid JSON, no explanation.

{{
  "acts": [{{"name": str, "year": int}}],
  "sections": [{{"number": str, "title": str, "act": str}}],
  "definitions": [{{"term": str, "definition": str, "defined_in": str}}],
  "compliance_obligations": [{{
    "name": str,
    "description": str,
    "frequency": str,  // "annual" | "quarterly" | "one-time" | "event-triggered"
    "due_date_logic": str
  }}],
  "penalties": [{{
    "amount_min": float,
    "amount_max": float,
    "type": str,  // "fine" | "imprisonment" | "both"
    "currency": "INR"
  }}],
  "entity_types": [{{"name": str}}],  // PrivateLimited, PublicLimited, OPC, LLP, SmallCompany
  "thresholds": [{{"metric": str, "value": float, "unit": str}}],
  "authorities": [{{"name": str, "type": str}}]  // MCA, SEBI, RBI, NCLT, NCLAT
}}

Return empty lists for entity types not found. Numbers only for amounts (no "lakh" — convert: 5 lakh = 500000).
"""
```

### Relation Extraction Prompt

```python
# clause/ingestion/extractors/relation_extractor.py

RELATION_EXTRACTION_PROMPT = """Given these entities extracted from a legal section, extract relationships between them.

Entities:
{entities_json}

Section text:
<section>
{section_text}
</section>

Return ONLY valid JSON with this exact structure:
{{
  "relationships": [
    {{
      "from_type": str,      // node label: Section, ComplianceObligation, etc.
      "from_id": str,        // identifying field value
      "relationship": str,   // GOVERNED_BY | APPLIES_TO | HAS_CONDITION | PENALTY_FOR_BREACH | ENFORCED_BY | DEFINES | CROSS_REFERENCES | AMENDED_BY | EXEMPT_FROM | ISSUED_UNDER
      "to_type": str,
      "to_id": str
    }}
  ]
}}

Only extract relationships explicitly stated in the text. Do not infer.
"""
```

### Neo4j Graph Store

```python
# clause/indexing/graph_store.py

from neo4j import GraphDatabase

class GraphStore:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def upsert_node(self, label: str, properties: dict, merge_key: str):
        """Upsert node by merge_key — idempotent."""
        query = f"""
        MERGE (n:{label} {{{merge_key}: $props.{merge_key}}})
        SET n += $props
        RETURN n
        """
        with self.driver.session() as session:
            session.run(query, props=properties)

    def upsert_relationship(
        self,
        from_label: str, from_key: str, from_val: str,
        rel_type: str,
        to_label: str, to_key: str, to_val: str,
        rel_props: dict = {}
    ):
        """Upsert typed relationship between two nodes — idempotent."""
        query = f"""
        MATCH (a:{from_label} {{{from_key}: $from_val}})
        MATCH (b:{to_label} {{{to_key}: $to_val}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props
        RETURN r
        """
        with self.driver.session() as session:
            session.run(query, from_val=from_val, to_val=to_val, props=rel_props)

    def link_chunk_to_section(self, chunk_id: str, section_number: str, act: str):
        """
        Critical bridge: links Qdrant chunk_id to Neo4j Section node.
        This is how graph context gets merged with vector results at query time.
        """
        query = """
        MATCH (s:Section {number: $section_number, act_name: $act})
        SET s.chunk_id = $chunk_id
        """
        with self.driver.session() as session:
            session.run(query, section_number=section_number, act=act, chunk_id=chunk_id)
```

---

## 🔗 Next Steps

- Query pipeline: [05-RETRIEVAL-PIPELINE.md](05-RETRIEVAL-PIPELINE.md)
- Agent loop: [06-AGENT-LOOP.md](06-AGENT-LOOP.md)
