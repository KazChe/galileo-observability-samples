"""
Credit Context Scorer - Credit Score Tier Validation

This custom metric evaluates whether LLM responses are appropriate
for the customer's credit tier based on dataset metadata.

Register this metric in Galileo Console:
1. Go to your project > Metrics > Create Custom Metric
2. Name it "credit_context_scorer"
3. Paste the scorer_fn and aggregator_fn code
"""

from typing import Any


def scorer_fn(*, step_object, **kwargs) -> int:
    """
    Evaluate response appropriateness based on customer credit tier.

    Accesses metadata from kwargs (dataset_metadata):
    - credit_score: Customer's credit score (string)
    - customer: Customer name (string)

    Returns a score from 0-100 based on whether the response
    contains appropriate content for the customer's credit tier.
    """
    # Dataset metadata comes through kwargs, not step_object
    dataset_metadata = kwargs.get("dataset_metadata", {}) or {}

    # Get output - it's a Message object, need to get content
    output_obj = step_object.output
    if hasattr(output_obj, 'content'):
        output = output_obj.content or ""
    elif isinstance(output_obj, str):
        output = output_obj
    else:
        output = str(output_obj)

    # Get credit score from dataset metadata
    credit_score_str = dataset_metadata.get("credit_score", "0")
    try:
        credit_score = int(credit_score_str) if credit_score_str else 0
    except (ValueError, TypeError):
        credit_score = 0

    # Define credit tiers and keywords that should/shouldn't appear
    if credit_score >= 750:
        # Excellent credit - should mention premium options
        positive_keywords = ["excellent", "premium", "best rates", "lowest interest", "qualify", "approved"]
        negative_keywords = ["subprime", "high risk", "denied", "rebuild"]
    elif credit_score >= 670:
        # Good credit - competitive options
        positive_keywords = ["good", "competitive", "qualify", "options", "approved"]
        negative_keywords = ["subprime", "denied", "poor credit"]
    elif credit_score >= 580:
        # Fair credit - should mention improvement options
        positive_keywords = ["improve", "build", "secured", "options available", "steps", "work on"]
        negative_keywords = ["excellent rates", "premium", "best rates"]
    else:
        # Poor credit - should be honest but helpful
        positive_keywords = ["rebuild", "secured card", "steps", "improve", "build credit", "options"]
        negative_keywords = ["excellent credit", "best rates", "premium rates"]

    score = 50  # Base score
    output_lower = output.lower()

    # Add points for appropriate content
    for keyword in positive_keywords:
        if keyword in output_lower:
            score += 10

    # Subtract points for inappropriate content
    for keyword in negative_keywords:
        if keyword in output_lower:
            score -= 15

    # Clamp score to 0-100
    return max(0, min(100, score))


def aggregator_fn(*, scores: list[Any]) -> dict[str, Any]:
    """
    Aggregate scores across all evaluated rows.

    Returns summary statistics for the credit_context_scorer scores.
    """
    if not scores:
        return {
            "Average Score": 0,
            "Min Score": 0,
            "Max Score": 0,
            "Pass Rate (%)": 0,
            "Total Rows": 0,
        }

    passing_threshold = 50
    passing_count = sum(1 for s in scores if s >= passing_threshold)

    return {
        "Average Score": round(sum(scores) / len(scores), 2),
        "Min Score": min(scores),
        "Max Score": max(scores),
        "Pass Rate (%)": round(passing_count / len(scores) * 100, 1),
        "Total Rows": len(scores),
    }
