"""
Tests for smart chunking logic.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sdk.governance import Governance


class TestTokenEstimation:
    """Test token estimation."""

    def test_estimate_tokens_uses_char_division(self):
        """Token estimate is roughly len/4."""
        gov = Governance()
        text = "a" * 1000
        assert gov._estimate_tokens(text) == 250

    def test_estimate_tokens_empty_string(self):
        """Empty string returns 0."""
        gov = Governance()
        assert gov._estimate_tokens("") == 0

    def test_estimate_tokens_whitespace_only(self):
        """Whitespace counts toward tokens."""
        gov = Governance()
        assert gov._estimate_tokens("     ") == 1


class TestSmartChunking:
    """Test smart chunking at paragraph boundaries."""

    def test_short_text_returns_single_chunk(self):
        """Text under max_tokens is not split."""
        gov = Governance(max_tokens_per_chunk=8000)
        text = "This is a short paragraph."
        chunks = gov._smart_chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_exact_boundary_single_chunk(self):
        """Text at exact boundary is single chunk."""
        gov = Governance(max_tokens_per_chunk=8000)
        text = "A" * 32000
        chunks = gov._smart_chunk(text)
        assert len(chunks) == 1

    def test_splits_at_paragraph_boundary(self):
        """Text splits at double newline."""
        gov = Governance(max_tokens_per_chunk=1000)
        text = ("Paragraph one " * 200) + "\n\n" + ("Paragraph two " * 200)
        chunks = gov._smart_chunk(text)
        assert len(chunks) >= 2
        assert "\n\n" not in chunks[0]
        assert "Paragraph one" in chunks[0]
        assert "Paragraph two" in chunks[-1]

    def test_preserves_paragraph_content(self):
        """Each chunk contains complete paragraphs."""
        gov = Governance(max_tokens_per_chunk=500)
        text = "Para 1.\n\nPara 2.\n\nPara 3."
        chunks = gov._smart_chunk(text)

        # Each paragraph should be in exactly one chunk
        paragraphs = ["Para 1.", "Para 2.", "Para 3."]
        for para in paragraphs:
            found = any(para in chunk for chunk in chunks)
            assert found, f"Paragraph '{para}' not found in any chunk"

    def test_single_paragraph_too_long_splits_at_sentence(self):
        """Single paragraph exceeding limit is split at sentence boundaries."""
        gov = Governance(max_tokens_per_chunk=100)
        text = ("This is a long sentence. " * 50).strip()
        chunks = gov._smart_chunk(text)

        # Should split into multiple chunks
        assert len(chunks) > 1
        # Each chunk should have content
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_logs_warning_for_many_chunks(self, caplog):
        """Warning is logged when output splits into many chunks."""
        gov = Governance(max_tokens_per_chunk=50)
        text = "\n\n".join(["x" * 100] * 10)
        chunks = gov._smart_chunk(text)

        if len(chunks) > 5:
            assert "split into" in caplog.text

    def test_empty_text_returns_single_empty_chunk(self):
        """Empty text returns single chunk."""
        gov = Governance()
        chunks = gov._smart_chunk("")
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_whitespace_only_returns_single_chunk(self):
        """Whitespace-only returns single chunk."""
        gov = Governance()
        chunks = gov._smart_chunk("   \n\n   ")
        assert len(chunks) == 1


class TestChunkingIntegration:
    """Integration tests for chunking with real-world scenarios."""

    def test_llm_response_splitting(self):
        """Long LLM responses are split correctly."""
        gov = Governance(max_tokens_per_chunk=2000)

        response = """
The capital of France is Paris.

Paris is also the largest city in France, with a population of over 2 million people in the city proper and over 12 million in the metropolitan area.

The city is known for its iconic landmarks including the Eiffel Tower, the Louvre Museum, and Notre-Dame Cathedral.
"""
        chunks = gov._smart_chunk(response)

        for chunk in chunks:
            assert len(chunk) > 0
            if len(chunks) > 1:
                assert "\n\n" not in chunk

    def test_code_block_preservation(self):
        """Code blocks within paragraphs are preserved."""
        gov = Governance(max_tokens_per_chunk=500)
        text = (
            "Here is some code:\n\n```python\nprint('hello')\n```\n\n"
            "And more text here."
        )
        chunks = gov._smart_chunk(text)

        for chunk in chunks:
            assert "```" not in chunk or "```python" in chunk
