"""Regression: vibe hearts must scan only typed text, never attached context.

``_emit_reaction`` sees the user message AFTER @-reference expansion:
``agent/context_references.py`` appends ``--- Context Warnings ---`` and
``--- Attached Context ---`` footers below the typed words. Affection tokens
inside those footers are app/page text, not the user's — live triggers were a
GitHub page footer ("Made with ❤️ by humans.txt") inside an @url expansion and
"Thanks for choosing Google Cloud" inside a pasted @file. The detector lexicon
itself (agent/reactions.py) is deliberately untouched.
"""

from __future__ import annotations

from types import SimpleNamespace

from agent.reactions import VIBE
from agent.turn_context import _emit_reaction

# Footer shapes exactly as preprocess_context_references_async builds them.
_ATTACHED_FOOTER = (
    "\n\n--- Attached Context ---\n\n"
    "📄 @file:pasted_content.txt (9 tokens)\n"
    "```text\nThanks for choosing Google Cloud\n```\n\n"
    "🔗 @url:https://github.com/example/repo (210 tokens)\n"
    "Made with ❤️ by humans.txt\n"
)
_WARNINGS_FOOTER = (
    "\n\n--- Context Warnings ---\n"
    "- @file:thanks.md: path is outside the allowed workspace"
)


def _agent():
    fired: list[str] = []
    return SimpleNamespace(reaction_callback=fired.append), fired


def test_attachment_affection_tokens_do_not_fire():
    """'Thanks'/'❤' inside an attached block are page text, not affection."""
    agent, fired = _agent()
    _emit_reaction(agent, "summarize this page" + _ATTACHED_FOOTER)
    assert fired == []


def test_typed_thanks_with_attachment_still_fires():
    """Stripping the footer must never swallow affection the user actually typed."""
    agent, fired = _agent()
    _emit_reaction(agent, "thanks, summarize this page" + _ATTACHED_FOOTER)
    assert fired == [VIBE]


def test_warnings_footer_affection_token_does_not_fire():
    """Warnings are app text too — a 'thanks.md' filename in one is not affection."""
    agent, fired = _agent()
    _emit_reaction(agent, "attach the report" + _WARNINGS_FOOTER)
    assert fired == []


def test_both_footers_are_stripped():
    agent, fired = _agent()
    _emit_reaction(agent, "attach the report" + _WARNINGS_FOOTER + _ATTACHED_FOOTER)
    assert fired == []


def test_typed_affection_without_attachment_still_fires():
    agent, fired = _agent()
    _emit_reaction(agent, "ily")
    assert fired == [VIBE]


def test_neutral_typed_text_does_not_fire():
    agent, fired = _agent()
    _emit_reaction(agent, "run the tests")
    assert fired == []


def test_multimodal_content_passes_through_unchanged():
    """Non-str content keeps today's silent no-op (the detector raises, suppressed)."""
    agent, fired = _agent()
    content = [
        {"type": "text", "text": "thanks"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]
    _emit_reaction(agent, content)
    assert fired == []


def test_hidden_display_kind_never_fires():
    agent, fired = _agent()
    _emit_reaction(agent, "ily", display_kind="hidden")
    assert fired == []


def test_missing_callback_is_a_noop():
    _emit_reaction(SimpleNamespace(), "ily")  # must not raise


class TestStripContextFooters:
    """The shared helper lives in the module that PRODUCES the footers."""

    def test_strips_both_footers_to_the_typed_text(self):
        from agent.context_references import strip_context_footers

        typed = "summarize this page"
        assert strip_context_footers(typed + _WARNINGS_FOOTER + _ATTACHED_FOOTER) == typed

    def test_noop_without_footers(self):
        from agent.context_references import strip_context_footers

        assert strip_context_footers("run the tests") == "run the tests"
        assert strip_context_footers("") == ""
        # A horizontal rule in typed prose is not a footer.
        assert strip_context_footers("before\n---\nafter") == "before\n---\nafter"

    def test_typed_affection_survives_the_strip(self):
        from agent.context_references import strip_context_footers

        assert strip_context_footers("thanks" + _ATTACHED_FOOTER) == "thanks"
