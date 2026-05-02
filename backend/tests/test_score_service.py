"""
Unit tests for score_service pure functions.

Pure-function tests (compute_points, compute_level, compute_impact_score, etc.)
run without Docker.  Integration tests (recalculate_workspace_scores) require
the full Docker stack.
"""
import sys
from unittest.mock import MagicMock

# Stub SQLAlchemy/asyncpg so pure functions can be imported without a live DB
for _mod in (
    "asyncpg",
    "app.database",
    "app.models.channel",
    "app.models.message",
    "app.models.user_score",
):
    sys.modules.setdefault(_mod, MagicMock())

from app.services.score_service import (  # noqa: E402
    WEIGHTS,
    QUALITY_WEIGHTS,
    QualityScores,
    compute_impact_score,
    compute_level,
    compute_points,
    normalize_enthusiasm,
    _is_important,
    _is_reply,
)

import pytest  # noqa: E402


# ── compute_points (activity only) ───────────────────────────────────

def test_compute_points_basic():
    pts = compute_points(
        message_count=10,
        reply_count=5,
        reaction_received_count=2,
        question_count=3,
        positive_count=4,
        important_message_count=1,
    )
    expected = (
        10 * WEIGHTS["message_count"]
        + 5 * WEIGHTS["reply_count"]
        + 2 * WEIGHTS["reaction_received_count"]
        + 3 * WEIGHTS["question_count"]
        + 4 * WEIGHTS["positive_count"]
        + 1 * WEIGHTS["important_message_count"]
    )
    assert pts == expected


def test_compute_points_zero():
    assert compute_points(
        message_count=0, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
    ) == 0


# ── compute_points with quality boost ────────────────────────────────

def test_compute_points_quality_boost_additive():
    base = compute_points(
        message_count=5, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
    )
    boosted = compute_points(
        message_count=5, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
        insight_quality_score=1.0,
        discussion_impact_score=1.0,
        decision_contribution_score=1.0,
    )
    quality_sum = sum(QUALITY_WEIGHTS.values())
    assert boosted == base + quality_sum


def test_compute_points_partial_quality():
    no_quality = compute_points(
        message_count=10, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
    )
    with_insight = compute_points(
        message_count=10, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
        insight_quality_score=0.5,
    )
    assert with_insight == no_quality + int(0.5 * QUALITY_WEIGHTS["insight_quality_score"])


def test_compute_points_quality_defaults_zero():
    """Calling without quality args should equal calling with zeros."""
    kw = dict(
        message_count=3, reply_count=1, reaction_received_count=0,
        question_count=1, positive_count=1, important_message_count=0,
    )
    assert compute_points(**kw) == compute_points(
        **kw,
        insight_quality_score=0.0,
        discussion_impact_score=0.0,
        decision_contribution_score=0.0,
    )


# ── compute_level ─────────────────────────────────────────────────────

@pytest.mark.parametrize("points,expected", [
    (1000, "Platinum"), (1500, "Platinum"),
    (500,  "Gold"),     (999,  "Gold"),
    (200,  "Silver"),   (499,  "Silver"),
    (0,    "Bronze"),   (199,  "Bronze"),
])
def test_compute_level(points: int, expected: str):
    assert compute_level(points) == expected


def test_compute_level_boundary_platinum():
    assert compute_level(999) == "Gold"
    assert compute_level(1000) == "Platinum"


def test_compute_level_boundary_gold():
    assert compute_level(499) == "Silver"
    assert compute_level(500) == "Gold"


def test_compute_level_boundary_silver():
    assert compute_level(199) == "Bronze"
    assert compute_level(200) == "Silver"


# ── quality can push a user into a higher level ───────────────────────

def test_quality_boost_crosses_level_boundary():
    # 198 rule points = Bronze; add max quality (35 pts) → 233 = Silver
    base = compute_points(
        message_count=99, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
    )
    # 99 * 2 = 198
    assert base == 198
    assert compute_level(base) == "Bronze"

    boosted = compute_points(
        message_count=99, reply_count=0, reaction_received_count=0,
        question_count=0, positive_count=0, important_message_count=0,
        insight_quality_score=1.0,
        discussion_impact_score=1.0,
        decision_contribution_score=1.0,
    )
    assert boosted == 198 + 35
    assert compute_level(boosted) == "Silver"


# ── normalize_enthusiasm ──────────────────────────────────────────────

def test_normalize_enthusiasm_half():
    assert normalize_enthusiasm(500, 1000) == 50.0


def test_normalize_enthusiasm_full():
    assert normalize_enthusiasm(1000, 1000) == 100.0


def test_normalize_enthusiasm_zero_max():
    assert normalize_enthusiasm(0, 0) == 0.0


def test_normalize_enthusiasm_zero_points():
    assert normalize_enthusiasm(0, 100) == 0.0


def test_normalize_enthusiasm_caps_at_100():
    assert normalize_enthusiasm(2000, 1000) == 100.0


# ── compute_impact_score ─────────────────────────────────────────────

def test_compute_impact_score_zero():
    assert compute_impact_score(0.0, 0.0, 0.0) == 0.0


def test_compute_impact_score_max():
    assert compute_impact_score(1.0, 1.0, 1.0) == 100.0


def test_compute_impact_score_partial():
    # Only decision_contribution = 1.0 → 20/35 * 100 ≈ 57.1
    result = compute_impact_score(0.0, 0.0, 1.0)
    assert result == round(QUALITY_WEIGHTS["decision_contribution_score"] / sum(QUALITY_WEIGHTS.values()) * 100, 1)


def test_compute_impact_score_clamped_at_100():
    # All at 2.0 (should clamp to 100)
    assert compute_impact_score(2.0, 2.0, 2.0) == 100.0


# ── QualityScores TypedDict ───────────────────────────────────────────

def test_quality_scores_typeddict_usage():
    qs: QualityScores = {
        "insight_quality": 0.7,
        "discussion_impact": 0.5,
        "decision_contribution": 0.9,
    }
    assert qs.get("insight_quality") == 0.7
    assert qs.get("missing_key", 0.0) == 0.0


# ── _is_reply ─────────────────────────────────────────────────────────

def test_is_reply_mention():
    assert _is_reply("@alice thanks!") is True


def test_is_reply_no_mention():
    assert _is_reply("hello world") is False


def test_is_reply_mention_not_at_start():
    assert _is_reply("hello @alice") is False


def test_is_reply_empty():
    assert _is_reply("") is False


# ── _is_important ─────────────────────────────────────────────────────

def test_is_important_ascii_exclamation():
    assert _is_important("Great work!") is True


def test_is_important_japanese_exclamation():
    assert _is_important("最高！") is True


def test_is_important_both():
    assert _is_important("すごい！ Amazing!") is True


def test_is_important_no_exclamation():
    assert _is_important("普通のメッセージです") is False


def test_is_important_empty():
    assert _is_important("") is False
