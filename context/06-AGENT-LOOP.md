# 06 — Agent Loop (LangGraph)

Covers Step 8: Agentic orchestration with CRAG pattern.

---

## State Definition

**File**: `clause/agent/state.py`

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class ClauseState(TypedDict):
    # Input
    original_query: str
    query_type: str                    # SIMPLE | MULTI_HOP | CROSS_DOC | CONDITIONAL
    
    # Query processing
    expanded_queries: list[str]        # original + 3 expansions
    hyde_text: str                     # hypothetical document text
    
    # Retrieval
    retrieved_chunks: list[dict]       # after RRF + rerank
    parent_chunks: list[dict]          # fetched parent sections
    graph_context: list[dict]          # Neo4j traversal results
    
    # Evaluation
    context_score: float               # 0-1 relevance score from CRAG check
    iteration_count: int               # current retry count
    refinement_reason: str             # why context was insufficient
    
    # Generation
    final_context: list[dict]          # merged vector + graph context
    answer: str
    citations: list[dict]              # [{section, act, text_excerpt}]
    
    # Meta
    messages: Annotated[list, add_messages]
```

---

## Graph Nodes

**File**: `clause/agent/nodes.py`

```python
async def classify_query(state: ClauseState) -> ClauseState:
    """Classify query type. Determines routing through graph."""
    # Uses CLASSIFICATION_PROMPT from clause/generation/prompts.py
    ...

async def expand_and_hyde(state: ClauseState) -> ClauseState:
    """Query expansion + HyDE generation in parallel."""
    # Generates 3 expanded queries
    # Generates hypothetical document text
    ...

async def hybrid_retrieve(state: ClauseState) -> ClauseState:
    """Dense + BM25 + RRF + rerank + parent fetch."""
    # Calls retrieval pipeline from 05-RETRIEVAL-PIPELINE.md
    ...

async def graph_retrieve(state: ClauseState) -> ClauseState:
    """
    Neo4j traversal based on entities found in retrieved chunks.
    Extract section numbers from chunks → find related nodes in graph.
    Returns graph context (obligations, penalties, exemptions, cross-refs).
    Only runs for MULTI_HOP, CROSS_DOC, CONDITIONAL query types.
    """
    ...

async def crag_check(state: ClauseState) -> ClauseState:
    """
    Corrective RAG: evaluate whether retrieved context is sufficient.
    
    Uses LLM to score relevance 0-1.
    Threshold: 0.6 — below this, refine and re-retrieve.
    Sets state.context_score and state.refinement_reason.
    """
    CRAG_PROMPT = """Evaluate whether the retrieved context is sufficient to answer the query.

    Query: {query}
    
    Retrieved context summary:
    {context_summary}
    
    Score the context from 0.0 to 1.0:
    - 1.0: Context directly and completely answers the query
    - 0.7: Context mostly answers the query, minor gaps
    - 0.5: Context partially answers, significant gaps
    - 0.3: Context is tangentially related, major gaps
    - 0.0: Context is irrelevant to the query
    
    Also identify: what specific information is missing (if score < 0.6)?
    
    Return ONLY valid JSON:
    {{"score": float, "reason": str, "missing_info": str}}"""
    ...

async def refine_query(state: ClauseState) -> ClauseState:
    """
    Generate a refined query based on why the previous retrieval failed.
    Uses state.refinement_reason to produce a targeted new query.
    """
    ...

async def generate_answer(state: ClauseState) -> ClauseState:
    """
    Final generation using merged vector + graph context.
    Extracts inline citations (section numbers) from the answer.
    """
    ...
```

---

## Graph Edges (Routing Logic)

**File**: `clause/agent/edges.py`

```python
def route_after_classify(state: ClauseState) -> str:
    """SIMPLE queries skip graph retrieval."""
    if state["query_type"] == "SIMPLE":
        return "hybrid_retrieve"
    return "expand_and_hyde"

def route_after_crag(state: ClauseState) -> str:
    """Core CRAG routing logic."""
    if state["iteration_count"] >= 3:
        return "generate_answer"        # Force generate after max iterations
    if state["context_score"] >= 0.6:
        return "generate_answer"        # Sufficient context
    return "refine_query"              # Insufficient — retry

def route_after_retrieve(state: ClauseState) -> str:
    """Skip graph for SIMPLE queries."""
    if state["query_type"] == "SIMPLE":
        return "crag_check"
    return "graph_retrieve"
```

---

## Graph Assembly

**File**: `clause/agent/graph.py`

```python
from langgraph.graph import StateGraph, END

def build_graph() -> CompiledGraph:
    """
    Assemble the complete LangGraph state machine.
    """
    graph = StateGraph(ClauseState)
    
    # Add nodes
    graph.add_node("classify_query", classify_query)
    graph.add_node("expand_and_hyde", expand_and_hyde)
    graph.add_node("hybrid_retrieve", hybrid_retrieve)
    graph.add_node("graph_retrieve", graph_retrieve)
    graph.add_node("crag_check", crag_check)
    graph.add_node("refine_query", refine_query)
    graph.add_node("generate_answer", generate_answer)
    
    # Entry point
    graph.set_entry_point("classify_query")
    
    # Edges
    graph.add_conditional_edges("classify_query", route_after_classify)
    graph.add_edge("expand_and_hyde", "hybrid_retrieve")
    graph.add_conditional_edges("hybrid_retrieve", route_after_retrieve)
    graph.add_edge("graph_retrieve", "crag_check")
    graph.add_conditional_edges("crag_check", route_after_crag)
    graph.add_edge("refine_query", "hybrid_retrieve")
    graph.add_edge("generate_answer", END)
    
    return graph.compile()

# Single compiled instance
agent_graph = build_graph()
```

---

## Execution Flow

```python
# Main entry point
async def run_query(query: str) -> QueryResponse:
    """
    Execute the full agent loop.
    """
    initial_state = ClauseState(
        original_query=query,
        query_type="auto",
        expanded_queries=[],
        hyde_text="",
        retrieved_chunks=[],
        parent_chunks=[],
        graph_context=[],
        context_score=0.0,
        iteration_count=0,
        refinement_reason="",
        final_context=[],
        answer="",
        citations=[],
        messages=[]
    )
    
    result = await agent_graph.ainvoke(initial_state)
    
    return QueryResponse(
        answer=result["answer"],
        citations=result["citations"],
        query_type=result["query_type"],
        iterations=result["iteration_count"],
        context_chunks_used=len(result["final_context"]),
        graph_nodes_used=len(result["graph_context"])
    )
```

---

## Key Design Principles

1. **Idempotent State** — Each node operates on the full state. No side effects.
2. **Conditional Routing** — Complex logic is encoded in edges, not node implementations.
3. **Bounded Iterations** — `max_agent_iterations=3` prevents infinite loops.
4. **Context Quality Check** — CRAG evaluation (context_score) drives re-retrieval.
5. **Merged Context** — Final LLM receives both vector + graph context.

---

## 🔗 Next Steps

- Generation & citations: [07-GENERATION-CITATIONS.md](07-GENERATION-CITATIONS.md)
- Evaluation: [08-EVALUATION.md](08-EVALUATION.md)
