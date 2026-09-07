"""Simple, explainable ingredient-name matching.

Exact string equality is far too brittle for matching a user's pantry
inventory against recipe ingredient lists: "tomato" vs "tomatoes" vs
"Roma tomato" are all the same ingredient for our purposes, but "egg" and
"eggplant" are not.

This module deliberately avoids any NLP/ML approach. It:
  1. Lowercases and tokenizes into alphanumeric words.
  2. Applies a small set of hand-written English pluralization rules to each
     word (so "tomatoes" -> "tomato", "berries" -> "berry").
  3. Treats two ingredient names as the same if one's normalized word
     sequence appears as a whole-word phrase inside the other's (so
     "tomato" matches "roma tomato", but "egg" does NOT match "eggplant"
     because word boundaries are enforced).

This is intentionally approximate -- it's a rule-based MVP, not an
ingredient-understanding model.
"""
from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z0-9]+")


def _singularize_word(word: str) -> str:
    """Best-effort singularization of a single lowercase word."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("oes") and len(word) > 4:
        return word[:-2]
    if word.endswith("es") and len(word) > 3:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def normalize_ingredient_name(name: str) -> str:
    """Lowercase, tokenize, and singularize an ingredient name.

    Returns a space-joined string of normalized words, e.g.
    "Roma Tomatoes" -> "roma tomato".
    """
    words = [_singularize_word(word) for word in _WORD_RE.findall(name.lower())]
    return " ".join(words)


def ingredients_match(have_name: str, need_name: str) -> bool:
    """Whether an on-hand ingredient (`have_name`) satisfies a recipe
    ingredient requirement (`need_name`).

    Matching is symmetric whole-word-phrase containment on the normalized
    names: either name's normalized word sequence must appear as a
    contiguous, word-boundary-aligned phrase inside the other's. Padding
    both normalized strings with spaces before doing a substring check is
    what enforces the word boundary -- it's what keeps "egg" from matching
    "eggplant" while still letting "tomato" match "roma tomato".
    """
    have_key = normalize_ingredient_name(have_name)
    need_key = normalize_ingredient_name(need_name)
    if not have_key or not need_key:
        return False

    padded_have = f" {have_key} "
    padded_need = f" {need_key} "
    return padded_have in padded_need or padded_need in padded_have
