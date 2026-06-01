"use client";

import { useState, useRef, useEffect } from "react";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Citation {
  act: string;
  section_type: string;
  section_number: string;
  section_title?: string;
  chunk_id?: string;
  text_excerpt?: string;
}

interface RetrievalStats {
  vector_hits: number;
  bm25_hits: number;
  graph_hits: number;
  candidates: number;
}

interface QueryResponse {
  answer: string;
  citations: Citation[];
  query: string;
  final_query: string;
  iterations: number;
  crag_score: number;
  chunks_used: number;
  provider: string;
  retrieval: RetrievalStats;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
  timestamp: Date;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SAMPLE_QUESTIONS = [
  "What are the duties of a director under the Companies Act?",
  "What is the definition of a small company?",
  "What are the penalties for late annual return filing?",
  "What are conditions for a private placement of shares?",
];

// ── Components ─────────────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="pulse-dot w-1.5 h-1.5 rounded-full"
          style={{ background: "var(--accent)", animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}

function CitationBadge({ citation, index }: { citation: Citation; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="rounded-lg overflow-hidden transition-all duration-200"
      style={{ border: "1px solid var(--border)", background: "var(--bg-elevated)" }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition-colors"
      >
        <span
          className="text-xs font-bold px-1.5 py-0.5 rounded"
          style={{ background: "var(--accent-glow)", color: "var(--accent)" }}
        >
          {index + 1}
        </span>
        <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
          {citation.act}
        </span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {citation.section_type} {citation.section_number}
        </span>
        {citation.section_title && (
          <span className="text-xs truncate flex-1" style={{ color: "var(--text-muted)" }}>
            — {citation.section_title}
          </span>
        )}
        <svg
          className={`w-3 h-3 ml-auto transition-transform ${open ? "rotate-180" : ""}`}
          style={{ color: "var(--text-muted)" }}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && citation.text_excerpt && (
        <div
          className="px-3 pb-3 pt-1 text-xs leading-relaxed"
          style={{ color: "var(--text-muted)", borderTop: "1px solid var(--border)" }}
        >
          <span
            className="block mb-1 text-xs font-medium"
            style={{ color: "var(--text-dim)" }}
          >
            Excerpt
          </span>
          {citation.text_excerpt}…
        </div>
      )}
    </div>
  );
}

function MetadataChip({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div
      className="flex flex-col items-center px-3 py-2 rounded-lg"
      style={{
        background: highlight ? "var(--accent-glow)" : "var(--bg-elevated)",
        border: `1px solid ${highlight ? "rgba(99,102,241,0.3)" : "var(--border)"}`,
      }}
    >
      <span className="text-xs font-bold" style={{ color: highlight ? "var(--accent)" : "var(--text-primary)" }}>
        {value}
      </span>
      <span className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
        {label}
      </span>
    </div>
  );
}

function AssistantMessage({ msg }: { msg: Message }) {
  const r = msg.response;
  return (
    <div className="fade-up flex gap-3 max-w-3xl">
      {/* Avatar */}
      <div
        className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold"
        style={{ background: "var(--accent-glow)", color: "var(--accent)", border: "1px solid rgba(99,102,241,0.3)" }}
      >
        ⚖
      </div>

      <div className="flex-1 space-y-3">
        {/* Answer */}
        <div
          className="glass rounded-xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap"
          style={{ color: "var(--text-primary)" }}
        >
          {msg.content}
        </div>

        {/* Metadata chips */}
        {r && (
          <div className="flex flex-wrap gap-2">
            <MetadataChip label="CRAG" value={r.crag_score.toFixed(2)} highlight={r.crag_score >= 0.7} />
            <MetadataChip label="Iterations" value={r.iterations} />
            <MetadataChip label="Chunks" value={r.chunks_used} />
            <MetadataChip label="Vector" value={r.retrieval.vector_hits} />
            <MetadataChip label="BM25" value={r.retrieval.bm25_hits} />
            <MetadataChip label="Graph" value={r.retrieval.graph_hits} />
            <MetadataChip label="Provider" value={r.provider} />
          </div>
        )}

        {/* Citations */}
        {r && r.citations.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
              {r.citations.length} Citation{r.citations.length > 1 ? "s" : ""}
            </p>
            {r.citations.map((c, i) => (
              <CitationBadge key={i} citation={c} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function UserMessage({ msg }: { msg: Message }) {
  return (
    <div className="fade-up flex justify-end">
      <div
        className="max-w-xl px-4 py-2.5 rounded-xl text-sm leading-relaxed"
        style={{ background: "var(--accent)", color: "#fff" }}
      >
        {msg.content}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [useCrag, setUseCrag] = useState(true);
  const [useGraph, setUseGraph] = useState(true);
  const [filterAct, setFilterAct] = useState("");
  const [health, setHealth] = useState<Record<string, string> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Health check on mount
  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable" }));
  }, []);

  const sendQuery = async (query: string) => {
    if (!query.trim() || loading) return;
    setInput("");
    setLoading(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          filter_act: filterAct || null,
          use_crag: useCrag,
          use_graph: useGraph,
        }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data: QueryResponse = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        response: data,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : "Request failed"}. Make sure the API is running on port 8000.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendQuery(input);
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="relative flex h-screen overflow-hidden" style={{ background: "var(--bg-primary)" }}>
      <div className="gradient-mesh" />

      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      <aside
        className="relative z-10 flex flex-col w-64 flex-shrink-0 p-4 gap-4"
        style={{ borderRight: "1px solid var(--border)", background: "rgba(10,10,15,0.6)" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-2.5 pt-1 pb-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
            style={{ background: "var(--accent-glow)", border: "1px solid rgba(99,102,241,0.4)" }}
          >
            ⚖️
          </div>
          <div>
            <div className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
              Clause
            </div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>
              Legal AI
            </div>
          </div>
        </div>

        {/* New Chat */}
        <button
          onClick={() => setMessages([])}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all hover:opacity-80 active:scale-95"
          style={{ background: "var(--accent)", color: "#fff" }}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>

        {/* Filters */}
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
            Settings
          </p>

          <div className="space-y-1.5">
            <label className="text-xs" style={{ color: "var(--text-muted)" }}>
              Filter Act
            </label>
            <select
              value={filterAct}
              onChange={(e) => setFilterAct(e.target.value)}
              className="w-full text-xs px-2.5 py-1.5 rounded-md outline-none"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
            >
              <option value="">All Acts</option>
              <option value="Companies">Companies Act</option>
              <option value="SEBI">SEBI</option>
              <option value="DPIIT">DPIIT</option>
              <option value="Startup">Startup</option>
            </select>
          </div>

          {[
            { label: "CRAG Check", value: useCrag, set: setUseCrag, tip: "Quality check + retry" },
            { label: "Graph Expand", value: useGraph, set: setUseGraph, tip: "Neo4j traversal" },
          ].map(({ label, value, set, tip }) => (
            <div key={label} className="flex items-center justify-between">
              <div>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{label}</p>
                <p className="text-xs" style={{ color: "var(--text-dim)" }}>{tip}</p>
              </div>
              <button
                onClick={() => set(!value)}
                className={`relative w-8 h-4 rounded-full transition-colors ${value ? "" : "opacity-40"}`}
                style={{ background: value ? "var(--accent)" : "var(--border)" }}
              >
                <span
                  className="absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform"
                  style={{ transform: `translateX(${value ? "17px" : "2px"})` }}
                />
              </button>
            </div>
          ))}
        </div>

        {/* Health */}
        {health && (
          <div className="mt-auto space-y-1.5">
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
              Services
            </p>
            {Object.entries(health)
              .filter(([k]) => k !== "status")
              .map(([k, v]) => (
                <div key={k} className="flex items-center justify-between">
                  <span className="text-xs capitalize" style={{ color: "var(--text-muted)" }}>
                    {k}
                  </span>
                  <span
                    className="text-xs font-medium"
                    style={{ color: v === "ok" ? "var(--success)" : "var(--warning)" }}
                  >
                    {v === "ok" ? "● ok" : "● err"}
                  </span>
                </div>
              ))}
          </div>
        )}
      </aside>

      {/* ── Main ────────────────────────────────────────────────────────────── */}
      <main className="relative z-10 flex flex-col flex-1 overflow-hidden">
        {/* Empty state */}
        {isEmpty && (
          <div className="flex-1 flex flex-col items-center justify-center px-8 gap-8">
            <div className="text-center space-y-3">
              <div
                className="text-5xl mb-4"
                style={{ filter: "drop-shadow(0 0 20px rgba(99,102,241,0.4))" }}
              >
                ⚖️
              </div>
              <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
                Clause Legal AI
              </h1>
              <p className="text-sm max-w-md" style={{ color: "var(--text-muted)" }}>
                Ask anything about the Companies Act 2013, SEBI Regulations, or DPIIT Startup Guidelines.
                Powered by hybrid GraphRAG with inline citations.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-w-2xl w-full">
              {SAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendQuery(q)}
                  className="text-left px-4 py-3 rounded-xl text-sm transition-all hover:scale-[1.02] active:scale-100"
                  style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    color: "var(--text-muted)",
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {!isEmpty && (
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {messages.map((msg) =>
              msg.role === "user" ? (
                <UserMessage key={msg.id} msg={msg} />
              ) : (
                <AssistantMessage key={msg.id} msg={msg} />
              )
            )}
            {loading && (
              <div className="flex gap-3">
                <div
                  className="w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center text-sm"
                  style={{ background: "var(--accent-glow)", border: "1px solid rgba(99,102,241,0.3)", color: "var(--accent)" }}
                >
                  ⚖
                </div>
                <div
                  className="glass rounded-xl"
                  style={{ minWidth: "80px" }}
                >
                  <TypingIndicator />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Input */}
        <div
          className="px-6 py-4"
          style={{ borderTop: "1px solid var(--border)", background: "rgba(10,10,15,0.8)" }}
        >
          <form onSubmit={handleSubmit} className="flex gap-3 max-w-3xl mx-auto">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a legal question…"
              disabled={loading}
              className="flex-1 px-4 py-3 rounded-xl text-sm outline-none transition-all"
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "rgba(99,102,241,0.5)";
                e.target.style.boxShadow = "0 0 0 3px var(--accent-glow)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "var(--border)";
                e.target.style.boxShadow = "none";
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-3 rounded-xl text-sm font-medium transition-all disabled:opacity-40 hover:opacity-90 active:scale-95"
              style={{ background: "var(--accent)", color: "#fff", minWidth: "80px" }}
            >
              {loading ? "…" : "Send"}
            </button>
          </form>
          <p className="text-center text-xs mt-2" style={{ color: "var(--text-dim)" }}>
            Answers are AI-generated from Indian legal statutes. Always verify with a qualified legal professional.
          </p>
        </div>
      </main>
    </div>
  );
}
