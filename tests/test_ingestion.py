"""Unit tests for ingestion pipeline components."""

import pytest
from pathlib import Path
from clause.ingestion.chunkers import LegalChunk
from clause.ingestion.chunkers.section_chunker import (
    create_legal_chunks,
    extract_cross_references,
    count_tokens,
    merge_dependent_chunks,
    is_proviso,
    is_explanation,
)


class TestCrossReferenceExtraction:
    """Test cross-reference extraction."""

    def test_section_reference(self):
        text = "As per Section 42 of the Companies Act, this applies."
        refs = extract_cross_references(text)
        assert "Section 42" in refs

    def test_rule_reference(self):
        text = "See Rule 14A for details."
        refs = extract_cross_references(text)
        assert "Rule 14A" in refs

    def test_multiple_references(self):
        text = "Section 42(3) and Rule 14 both apply. See Schedule IV."
        refs = extract_cross_references(text)
        assert len(refs) >= 3


class TestTokenCounting:
    """Test token counting."""

    def test_short_text(self):
        text = "Hello world"
        tokens = count_tokens(text)
        assert tokens > 0

    def test_empty_text(self):
        tokens = count_tokens("")
        assert tokens == 0

    def test_longer_text(self):
        text = "A" * 1000  # Large text
        tokens = count_tokens(text)
        assert tokens > 100


class TestProvisoDependency:
    """Test proviso detection."""

    def test_proviso_detection(self):
        assert is_proviso("Provided that the company shall...")
        assert is_proviso("Provided further that...")
        assert not is_proviso("The company shall...")

    def test_explanation_detection(self):
        assert is_explanation("Explanation — For the purposes...")
        assert not is_explanation("Other text")


class TestChunkMerging:
    """Test merging of dependent chunks."""

    def test_merge_proviso(self):
        chunks = [
            "Condition A",
            "Provided that exemption applies",
            "Condition B",
        ]
        merged = merge_dependent_chunks(chunks)
        assert len(merged) == 2  # Proviso merged with previous

    def test_no_merge_needed(self):
        chunks = [
            "Section 1",
            "Section 2",
        ]
        merged = merge_dependent_chunks(chunks)
        assert len(merged) == 2


class TestLegalChunkCreation:
    """Test LegalChunk model."""

    def test_chunk_creation(self):
        chunk = LegalChunk(
            chunk_id="CA2013_S42",
            type="parent",
            act="Companies Act 2013",
            section_number="42",
            text="Test text",
            tokens=100,
            source_file="test.pdf",
        )
        assert chunk.chunk_id == "CA2013_S42"
        assert chunk.type == "parent"

    def test_child_chunk_with_parent(self):
        chunk = LegalChunk(
            chunk_id="CA2013_S42_1",
            type="child",
            parent_id="CA2013_S42",
            act="Companies Act 2013",
            section_number="42",
            text="Sub-section text",
            tokens=150,
            source_file="test.pdf",
        )
        assert chunk.parent_id == "CA2013_S42"


class TestHierarchicalChunking:
    """Test hierarchical chunk creation."""

    def test_simple_text_chunking(self):
        text = """
Section 42. Private Placements

(1) The company shall not issue fresh offers.

(2) Provided that exemptions apply.

Section 43. Rights of shareholders

(1) The shareholder has rights.
        """

        chunks = create_legal_chunks(
            text=text,
            act="Companies Act 2013",
            source_file="test.pdf",
        )

        # Should have parent chunks (sections) and child chunks (subsections)
        assert len(chunks) > 0

        # Check chunk types
        types = {c.type for c in chunks}
        assert "parent" in types
        assert "child" in types

    def test_chunk_ids_deterministic(self):
        text = "Section 42. Title\n(1) Content\n(2) More content"
        chunks1 = create_legal_chunks(text, "Companies Act 2013", "test.pdf")
        chunks2 = create_legal_chunks(text, "Companies Act 2013", "test.pdf")

        ids1 = sorted([c.chunk_id for c in chunks1])
        ids2 = sorted([c.chunk_id for c in chunks2])
        assert ids1 == ids2  # Deterministic


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
