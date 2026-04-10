# Credit Context Scorer Demo

This demo shows how to evaluate whether LLM responses are appropriate for a customer's credit tier using a code-based custom metric with dataset metadata.

## Prerequisites

- Python 3.9+
- Galileo SDK (`galileo>=1.0.0`)
- A Galileo account with API access
- Galileo project created in the console

## Installation

1. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GALILEO_API_KEY
   ```

## Setup: Register the Custom Metric

Before running the experiment, register the code-based metric in Galileo Console:

1. Go to **Galileo Console** > Your Project > **Metrics** > **Create Custom Metric**
2. Select **Code-based** metric type
3. Set the name to: `credit_context_scorer`
4. Set "Apply to" to **Trace**
5. Paste the `scorer_fn` code from `credit_context_scorer.py`:

```python
def scorer_fn(*, step_object, **kwargs) -> int:
    """Evaluate response appropriateness based on customer credit tier."""
    dataset_metadata = kwargs.get("dataset_metadata", {}) or {}

    output_obj = step_object.output
    if hasattr(output_obj, 'content'):
        output = output_obj.content or ""
    elif isinstance(output_obj, str):
        output = output_obj
    else:
        output = str(output_obj)

    credit_score_str = dataset_metadata.get("credit_score", "0")
    try:
        credit_score = int(credit_score_str) if credit_score_str else 0
    except (ValueError, TypeError):
        credit_score = 0

    # Credit tier keyword matching
    if credit_score >= 750:
        positive_keywords = ["excellent", "premium", "best rates", "lowest interest", "qualify", "approved"]
        negative_keywords = ["subprime", "high risk", "denied", "rebuild"]
    elif credit_score >= 670:
        positive_keywords = ["good", "competitive", "qualify", "options", "approved"]
        negative_keywords = ["subprime", "denied", "poor credit"]
    elif credit_score >= 580:
        positive_keywords = ["improve", "build", "secured", "options available", "steps", "work on"]
        negative_keywords = ["excellent rates", "premium", "best rates"]
    else:
        positive_keywords = ["rebuild", "secured card", "steps", "improve", "build credit", "options"]
        negative_keywords = ["excellent credit", "best rates", "premium rates"]

    score = 50
    output_lower = output.lower()
    for keyword in positive_keywords:
        if keyword in output_lower:
            score += 10
    for keyword in negative_keywords:
        if keyword in output_lower:
            score -= 15

    return max(0, min(100, score))
```

6. Paste the `aggregator_fn` code:

```python
def aggregator_fn(*, scores: list) -> dict:
    """Aggregate credit context scores."""
    if not scores:
        return {"Average Score": 0, "Min Score": 0, "Max Score": 0, "Pass Rate (%)": 0, "Total Rows": 0}

    passing_count = sum(1 for s in scores if s >= 50)
    return {
        "Average Score": round(sum(scores) / len(scores), 2),
        "Min Score": min(scores),
        "Max Score": max(scores),
        "Pass Rate (%)": round(passing_count / len(scores) * 100, 1),
        "Total Rows": len(scores),
    }
```

7. Click **Save** to register the metric

## Running the Experiment

```bash
python credit_context_experiment.py
```

This will:
1. Create a test dataset with 4 customers at different credit tiers
2. Create a prompt template that includes customer context (name, credit score)
3. Run the experiment using `credit_context_scorer` to evaluate tier-appropriateness
4. Print a link to view results in Galileo Console

## How It Works

### Dataset Structure

Each row includes customer metadata that the scorer uses for evaluation:

```python
{
    "input": "What are the best practices for improving credit scores?",
    "output": "To improve your credit score, pay bills on time...",
    "metadata": {
        "customer": "Abe Mornal",
        "credit_score": "680",
        "request_type": "credit_advice",
    }
}
```

### Credit Tiers

| Tier | Score Range | Expected Response Content |
|------|------------|--------------------------|
| Excellent | 750+ | Premium options, best rates |
| Good | 670-749 | Competitive options, qualification info |
| Fair | 580-669 | Improvement strategies, secured options |
| Poor | Below 580 | Rebuilding steps, secured cards |

### Prompt Template

The prompt template injects customer context so the LLM tailors advice by tier:

```
Customer Context:
- Name: {{metadata.customer}}
- Credit Score: {{metadata.credit_score}}

Tailor your advice based on the customer's credit profile...
```

The scorer then validates that the LLM's response matches the expected content for that tier.

## Files

| File | Description |
|------|-------------|
| `credit_context_scorer.py` | Code-based metric with credit tier keyword matching |
| `credit_context_experiment.py` | Experiment runner with dataset and prompt template creation |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

## Key Concepts

### Why Code-Based Metrics?

- Code-based metrics can evaluate **any span type**, including traces
- They can access `dataset_metadata` via `kwargs` for context-aware scoring
- No LLM call needed for the metric itself -- scoring is deterministic via keyword matching

### Metadata Access

The scorer accesses customer metadata through `kwargs`:

```python
dataset_metadata = kwargs.get("dataset_metadata", {}) or {}
credit_score = dataset_metadata.get("credit_score", "0")
```

> **Note**: `dataset_metadata` via `kwargs` is not officially documented. If it doesn't work in your environment, embed metadata in the input field instead (see the gender-bias demo for this approach).

## Troubleshooting

### "Metric not found" error
Ensure you registered `credit_context_scorer` in Galileo Console before running.

### "No LLM integration configured" error
This experiment uses `prompt_template` which requires a configured LLM provider:
1. Go to Galileo Console > Settings > Integrations
2. Add your OpenAI or other LLM provider API key

### All scores are 50
The base score is 50. If no positive or negative keywords are found, the score stays at 50. Check that the LLM is generating responses with tier-appropriate language.
