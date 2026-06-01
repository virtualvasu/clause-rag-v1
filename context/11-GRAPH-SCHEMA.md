# 11 — Neo4j Graph Schema

Complete graph data model: node labels, properties, relationship types, and key Cypher queries.

---

## Node Labels & Properties

### Act

Represents a legal act (statute).

```cypher
(:Act {
  name: "Companies Act 2013",
  year: 2013,
  ministry: "MCA",
  status: "active",
  source_url: "...",
  chunk_id: "CA2013"
})
```

### Section

A numbered section within an act.

```cypher
(:Section {
  number: "42",
  title: "Private Placements",
  act_name: "Companies Act 2013",
  chapter: "Chapter IV",
  chunk_id: "CA2013_S42"
})
```

### Rule

A rule issued under an act.

```cypher
(:Rule {
  number: "14",
  title: "Contents of Articles",
  parent_act: "Companies Act 2013",
  rule_set: "Incorporation Rules 2014",
  chunk_id: "CIR2014_R14"
})
```

### Regulation

A regulation issued by regulatory authority.

```cypher
(:Regulation {
  number: "26",
  title: "Offer document",
  issuing_authority: "SEBI",
  chunk_id: "ICDR2018_R26"
})
```

### Amendment

Records changes to sections/acts.

```cypher
(:Amendment {
  year: 2020,
  act_amended: "Companies Act 2013",
  effective_date: "2020-10-23",
  description: "Inserted new proviso to Section 42"
})
```

### Definition

Defined terms within legal text.

```cypher
(:Definition {
  term: "Small Company",
  definition_text: "A company which has a paid-up capital of not more than...",
  defined_in: "Section 2(85)"
})
```

### ComplianceObligation

A requirement imposed on entities.

```cypher
(:ComplianceObligation {
  name: "Annual Return Filing",
  description: "Every company must file annual return with ROC within 30 days",
  frequency: "annual",
  due_date_logic: "Within 30 days of AGM"
})
```

### Penalty

Consequences for non-compliance.

```cypher
(:Penalty {
  amount_min: 10000.0,
  amount_max: 100000.0,
  type: "fine",
  currency: "INR"
})
```

### EntityType

Categories of legal entities.

```cypher
(:EntityType {
  name: "PrivateLimited"
})

(:EntityType {
  name: "SmallCompany"
})
```

### Threshold

Quantitative boundaries (turnovers, member counts, etc.).

```cypher
(:Threshold {
  metric: "Annual Turnover",
  value: 200000000.0,
  unit: "INR"
})
```

### Authority

Regulatory and enforcement bodies.

```cypher
(:Authority {
  name: "Ministry of Corporate Affairs",
  type: "Government"
})

(:Authority {
  name: "SEBI",
  type: "Regulatory"
})
```

### Exemption

Exceptions to compliance rules.

```cypher
(:Exemption {
  description: "Small companies exempt from independent audit",
  condition: "turnover < 200 lakh, members < 50"
})
```

---

## Relationship Types (Directed)

| From | Relationship | To | Purpose |
|------|--------------|-----|---------|
| Section | PART_OF | Act | Structural hierarchy |
| Rule | ISSUED_UNDER | Section | Rule governance |
| Regulation | ISSUED_UNDER | Act | Regulatory governance |
| Section | AMENDED_BY | Amendment | Amendment tracking |
| Section | CROSS_REFERENCES | Section | Inter-section links |
| Section | DEFINES | Definition | Defined terms |
| ComplianceObligation | GOVERNED_BY | Section | Legal basis |
| ComplianceObligation | APPLIES_TO | EntityType | Applicability |
| ComplianceObligation | HAS_CONDITION | Threshold | Conditional applicability |
| ComplianceObligation | PENALTY_FOR_BREACH | Penalty | Consequence linkage |
| ComplianceObligation | ENFORCED_BY | Authority | Enforcement body |
| EntityType | EXEMPT_FROM {condition: str} | ComplianceObligation | Exception conditions |
| Offense | PUNISHABLE_UNDER | Section | Criminal linkage |
| Offense | CARRIES_PENALTY | Penalty | Penalty linkage |

---

## Example Cypher Queries

### Multi-hop: Find all obligations + penalties for an entity type

```cypher
MATCH (et:EntityType {name: $entity_type})
      -[:APPLIES_TO|EXEMPT_FROM*1..2]-(co:ComplianceObligation)
      -[:PENALTY_FOR_BREACH]->(p:Penalty)
      -[:GOVERNED_BY]->(s:Section)
RETURN et, co, p, s
ORDER BY p.amount_max DESC
```

**Use case:** "What penalties apply to directors of private limited companies?"

### Cross-document: Find all regulations issued under a section

```cypher
MATCH (r:Regulation)-[:ISSUED_UNDER]->(s:Section {number: $section_number})
RETURN r, s
```

**Use case:** "What SEBI regulations relate to Section 42?"

### Amendment history for a section

```cypher
MATCH (s:Section {number: $section_number})-[:AMENDED_BY]->(a:Amendment)
RETURN s, a 
ORDER BY a.year DESC
```

**Use case:** "Has Section 42 been amended? When?"

### All cross-references from a section

```cypher
MATCH (s:Section {number: $section_number})-[:CROSS_REFERENCES]->(related:Section)
RETURN related.chunk_id, related.number, related.title
LIMIT 20
```

**Use case:** "What other sections are referenced in Section 42?"

### Find exemptions for a condition

```cypher
MATCH (et:EntityType {name: $entity_type})
      -[e:EXEMPT_FROM]->(co:ComplianceObligation)
RETURN co, e.condition
```

**Use case:** "Are small companies exempt from any filing requirements?"

### Complete obligation chain

```cypher
MATCH (s:Section {number: $section_number})
      -[:DEFINES]->(d:Definition),
      (s)-[:GOVERNED_BY|PART_OF*]->(co:ComplianceObligation)
      -[:PENALTY_FOR_BREACH]->(p:Penalty),
      (co)-[:ENFORCED_BY]->(auth:Authority)
RETURN s, d, co, p, auth
```

**Use case:** "Give me the complete picture of Section 42 — definition, obligations, penalties, enforcer."

---

## Index Strategy

```cypher
-- Label + property indexes for fast lookups
CREATE INDEX ON :Section(number)
CREATE INDEX ON :Section(act_name)
CREATE INDEX ON :Rule(number)
CREATE INDEX ON :ComplianceObligation(name)
CREATE INDEX ON :EntityType(name)
CREATE INDEX ON :Act(name)

-- Composite index for common queries
CREATE INDEX ON :ComplianceObligation(frequency, name)
```

---

## Upsert Pattern

All nodes are upserted (merge) to ensure idempotency:

```python
# Python driver code
def upsert_section(name, number, act):
    with driver.session() as session:
        session.run("""
            MERGE (s:Section {number: $number, act_name: $act})
            SET s.title = $title
            RETURN s
        """, parameters={
            "number": number,
            "act": act,
            "title": name
        })
```

This prevents duplicate nodes during re-ingestion.

---

## Graph Size Estimates

Based on Indian corporate law corpus (Phase 1):

| Entity | Count | Notes |
|--------|-------|-------|
| Acts | 9 | Companies Act, Rules, SEBI regs, DPIIT |
| Sections | 500+ | All numbered sections |
| Rules | 200+ | MCA rules |
| Regulations | 100+ | SEBI, DPIIT |
| Definitions | 150+ | Key legal terms |
| Obligations | 100+ | Filing, reporting, governance |
| Penalties | 80+ | Fines, imprisonment |
| Entity Types | 8 | OPC, Private Ltd, Public Ltd, LLP, etc. |
| Authorities | 10 | MCA, SEBI, RBI, NCLT, etc. |
| **Total Nodes** | **~1,500** | |
| **Total Edges** | **~4,000** | Cross-references + relationships |

---

## Data Integrity Constraints

1. **Section → Act** — Every section must reference exactly one act (enforced by chunking)
2. **Obligation → Section** — Every obligation must cite a section (enforced by extraction)
3. **Penalty → Currency** — All penalties must be in INR (enforced at extraction)
4. **Amendment → Date** — All amendments must have effective date (enforced at creation)

---

## 🔗 Next Steps

- Prompts: [12-PROMPTS.md](12-PROMPTS.md)
- Constraints: [13-CONSTRAINTS.md](13-CONSTRAINTS.md)
