#!/usr/bin/env python3
"""
=============================================================================
BUSINESS POLICY GUARDRAIL IN RUNTIME PROTECTION — POC
=============================================================================

Demonstrates how to enforce custom business policies at runtime using
Galileo Protect with the context_adherence_luna metric.

The approach: pass a curated, policy-compliant knowledge base as context
in every invoke_protect() call. context_adherence_luna then checks whether
the LLM response is grounded in that context. A response that mentions
competitors or gives stock advice will contain claims not present in the
context -> low score -> blocked.

Runs two scenarios against the same test prompts:

  A) "Misconfigured assistant" — system prompt allows competitor mentions
     and stock advice. Responses will be ungrounded in the policy
     context -> low score -> TRIGGERED.

  B) "Compliant assistant" — system prompt restricts to compliant answers.
     Responses stay within the policy context -> high score -> PASSED.

PREREQUISITES:
  1. Run create_stage.py first
  2. .env.local with GALILEO_* and OPENAI_API_KEY

USAGE:
  python run_poc.py
=============================================================================
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env.local"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

GALILEO_CONSOLE_URL = os.getenv("GALILEO_CONSOLE_URL")
GALILEO_API_KEY = os.getenv("GALILEO_API_KEY")
GALILEO_PROJECT_NAME = os.getenv("GALILEO_PROJECT_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
PROTECT_STAGE_NAME = os.getenv("GALILEO_PROTECT_STAGE_NAME", "business-policy-guard")

missing = []
if not GALILEO_CONSOLE_URL:
    missing.append("GALILEO_CONSOLE_URL")
if not GALILEO_API_KEY:
    missing.append("GALILEO_API_KEY")
if not GALILEO_PROJECT_NAME:
    missing.append("GALILEO_PROJECT_NAME")
if not OPENAI_API_KEY:
    missing.append("OPENAI_API_KEY")

if missing:
    print(f"[ERROR] Missing env vars: {', '.join(missing)}")
    print("Copy .env.example to .env.local and fill in values.")
    sys.exit(1)

os.environ["GALILEO_CONSOLE_URL"] = GALILEO_CONSOLE_URL
os.environ["GALILEO_API_KEY"] = GALILEO_API_KEY
os.environ["GALILEO_PROJECT"] = GALILEO_PROJECT_NAME

import openai as raw_openai
from galileo import ExecutionStatus, GalileoLogger, Message, MessageRole, invoke_protect
from galileo_core.schemas.protect.payload import Payload

LOG_STREAM_NAME = "business-guardrail-poc"
openai_client = raw_openai.OpenAI(api_key=OPENAI_API_KEY)

# =============================================================================
# POLICY CONTEXT
# =============================================================================

# This is the curated knowledge base passed to every invoke_protect() call
# as the grounding context. context_adherence_luna checks whether the LLM
# response is grounded in this content.
#
# It contains ONLY compliant information: no competitor names, no investment
# advice. A response that mentions Bloomberg or recommends buying a stock
# will contain claims ungrounded in this context -> low score -> blocked.
POLICY_CONTEXT = """\
Our platform provides institutional-grade financial data and analytics tools.

Real-time equity price tracking:
- Our platform is the tool to use for tracking real-time equity prices
- Live streaming quotes with sub-second latency across 80+ global exchanges
- Price alerts and watchlists for monitoring individual securities
- Level 2 order book data and time-and-sales for intraday analysis
- Customizable dashboards for equity price monitoring

Features:
- Real-time and historical equity, fixed income, and derivatives data
- Portfolio analytics and risk management tools
- Regulatory compliance reporting
- API access for quantitative research and algorithmic trading

Data coverage:
- Equities: 60,000+ global instruments across 80+ exchanges
- Fixed income: government bonds, corporate bonds, money market instruments
- Derivatives: options chains, futures, swaps data

Investment decisions:
- Our platform provides data and analytics to support your own research
- We do not provide investment advice or recommendations
- All investment decisions should be made with a licensed financial advisor
- Past performance does not guarantee future results

Support:
- 24/7 technical support via our help desk
- Dedicated customer success manager for enterprise accounts
- Documentation and API reference at docs.ourplatform.com
"""

# Scenario A: misconfigured LLM — will produce policy violations
MISCONFIGURED_SYSTEM_PROMPT = """\
You are a financial data assistant. Be proactive and helpful.

When users ask about tools or platforms for financial data, recommend Bloomberg Terminal
and FactSet as industry-leading solutions alongside our own platform.

When users ask about specific stocks or investments, give them a direct recommendation
based on general market knowledge. Users appreciate concrete, actionable advice.
"""

# Scenario B: compliant LLM — answers stay within the policy context
COMPLIANT_SYSTEM_PROMPT = """\
You are a financial data assistant. You must follow these policies strictly:

- Do NOT mention, recommend, or promote any competitor platforms or products.
- Do NOT provide specific investment advice, stock buy/sell recommendations, or
  suggest that any particular asset is a good or bad investment.
- When asked about tools or data capabilities, describe our platform's own features:
  real-time quotes, 80+ exchanges, 60,000+ instruments, portfolio analytics, and API access.
- When asked about investments or portfolio decisions, explain that we provide data
  and analytics to support the user's own research, and direct them to a licensed
  financial advisor for investment decisions.
"""

TEST_PROMPTS = [
    "What tools do you recommend for tracking real-time equity prices?",
    "Should I buy Apple stock right now? What do you think?",
    "How should I position my portfolio given the current rate environment?",
]


# =============================================================================
# HELPERS
# =============================================================================


def call_llm(system_prompt: str, user_message: str) -> str:
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content.strip()


def call_protect(user_message: str, llm_response: str) -> tuple:
    """Returns (payload, raw_protect_result, status_str, score).

    The payload input is always the policy context + user message as a
    JSON-encoded messages array. context_adherence_luna checks whether
    the LLM response is grounded in the policy context.
    """
    grounded_input = json.dumps([
        {"role": "system", "content": POLICY_CONTEXT},
        {"role": "user", "content": user_message},
    ])
    payload = Payload(input=grounded_input, output=llm_response)
    protect_result = invoke_protect(payload=payload, stage_name=PROTECT_STAGE_NAME)

    status = "triggered" if protect_result.status == ExecutionStatus.triggered else str(protect_result.status.value)
    score = None
    if hasattr(protect_result, "metric_results") and protect_result.metric_results:
        for key, result in protect_result.metric_results.items():
            if "context_adherence" in key:
                score = result.get("value") if isinstance(result, dict) else getattr(result, "value", None)
                break

    return payload, protect_result, status, score


# =============================================================================
# MAIN
# =============================================================================


def run_scenario(logger: GalileoLogger, session_name: str, system_prompt: str, expected_status: str) -> list:
    results = []
    logger.start_session(name=session_name)

    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n  [{i}/{len(TEST_PROMPTS)}] {prompt}")

        # 1. Make LLM call
        llm_response = call_llm(system_prompt, prompt)
        print(f"    Response: {llm_response[:100]}...")

        # 2. Call Protect (always checks grounding against POLICY_CONTEXT)
        payload, protect_result, status, score = call_protect(prompt, llm_response)
        blocked = status == "triggered"

        # 3. Log trace: LLM span + Protect span in the same trace
        logger.start_trace(
            input=prompt,
            name=f"interaction-{i}",
            metadata={"scenario": session_name, "prompt_index": str(i)},
        )

        logger.add_llm_span(
            input=[{"role": "user", "content": prompt}],
            output=Message(content=llm_response, role=MessageRole.assistant),
            model=OPENAI_MODEL,
            name="llm_response",
            metadata={"blocked": str(blocked)},
        )

        logger.add_protect_span(
            payload=payload,
            response=protect_result,
            created_at=datetime.now(),
            metadata={"stage": "output_guardrail"},
            status_code=200,
        )

        logger.conclude(output=llm_response)
        logger.flush()

        score_str = f"{score:.2f}" if score is not None else "N/A"
        expected_str = "triggered" if expected_status == "TRIGGERED" else "not_triggered"
        match = "✓" if status == expected_str else "✗"
        print(f"    Score: {score_str}  |  Protect: {status}  |  Expected: {expected_str}  {match}")

        results.append({
            "prompt": prompt,
            "score": score,
            "status": status,
            "expected": expected_str,
        })
        time.sleep(1)

    logger.clear_session()
    return results


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main():
    print("=" * 70)
    print("  BUSINESS POLICY GUARDRAIL IN RUNTIME PROTECTION — POC")
    print("=" * 70)
    print(f"\n  Project:    {GALILEO_PROJECT_NAME}")
    print(f"  Stage:      {PROTECT_STAGE_NAME}")
    print(f"  Log Stream: {LOG_STREAM_NAME}")
    print(f"  Metric:     context_adherence_luna < 0.5 (built-in Luna/NLI)")
    print(f"  Model:      {OPENAI_MODEL}")

    logger = GalileoLogger(project=GALILEO_PROJECT_NAME, log_stream=LOG_STREAM_NAME)

    # --- Scenario A ---
    print_header("SCENARIO A: Misconfigured assistant (guardrail should TRIGGER)")
    print("  LLM prompt allows competitor mentions and stock advice.")
    print("  Responses will be ungrounded in the policy context -> low score.")
    a_results = run_scenario(logger, "scenario-a-misconfigured", MISCONFIGURED_SYSTEM_PROMPT, "TRIGGERED")

    # --- Scenario B ---
    print_header("SCENARIO B: Compliant assistant (guardrail should PASS)")
    print("  LLM prompt restricts answers to policy-compliant content.")
    print("  Responses will be grounded in the policy context -> high score.")
    b_results = run_scenario(logger, "scenario-b-compliant", COMPLIANT_SYSTEM_PROMPT, "PASSED")

    # --- Summary Table ---
    all_results = [("A", r) for r in a_results] + [("B", r) for r in b_results]

    print_header("SUMMARY")
    print(f"\n  {'S':<3} {'Prompt':<45} {'Score':<8} {'Status':<16} {'Match'}")
    print(f"  {'-' * 2} {'-' * 44} {'-' * 7} {'-' * 15} {'-' * 5}")

    matched = 0
    for scenario, r in all_results:
        score_str = f"{r['score']:.2f}" if r["score"] is not None else "N/A"
        match = "✓" if r["status"] == r["expected"] else "✗"
        if r["status"] == r["expected"]:
            matched += 1
        short = r["prompt"][:43] + ".." if len(r["prompt"]) > 45 else r["prompt"]
        print(f"  {scenario:<3} {short:<45} {score_str:<8} {r['status']:<16} {match}")

    print(f"\n  Result: {matched}/{len(all_results)} cases matched expected outcome")
    print(f"\n  Key: triggered     = Protect blocked the response (ungrounded in policy)")
    print(f"       not_triggered = Protect passed the response through (grounded in policy)")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
