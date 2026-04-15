#!/usr/bin/env python3
"""
=============================================================================
CREATE CUSTOM LLM METRIC + PROTECT STAGE — Business Guardrail POC
=============================================================================

Creates a custom LLM-as-a-Judge metric that flags competitor mentions and
stock buying advice, then wires it into a Protect stage rule.

This proves that custom LLM metrics (not just code scorers or built-ins)
can be used as real-time guardrails in Galileo Protect.

REQUIRED ENVIRONMENT VARIABLES:
  GALILEO_API_KEY       - Your Galileo API key
  GALILEO_CONSOLE_URL   - Galileo console URL
  GALILEO_PROJECT_NAME  - Name of your Galileo project

OPTIONAL:
  GALILEO_PROTECT_STAGE_NAME - Stage name (default: business-guardrail-stage)

USAGE:
  1. Copy .env.example to .env.local and fill in values
  2. python create_metric_and_stage.py
  3. Note the stage name printed — used by run_poc.py
=============================================================================
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent / ".env.local"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[INFO] Loaded environment from {env_path}")
    else:
        print(f"[WARNING] No .env.local found at {env_path}")
        print("         Copy .env.example to .env.local and fill in values.")
except ImportError:
    pass

# =============================================================================
# CONFIGURATION
# =============================================================================

GALILEO_CONSOLE_URL = os.getenv("GALILEO_CONSOLE_URL")
GALILEO_API_KEY = os.getenv("GALILEO_API_KEY")
GALILEO_PROJECT_NAME = os.getenv("GALILEO_PROJECT_NAME")
PROTECT_STAGE_NAME = os.getenv("GALILEO_PROTECT_STAGE_NAME", "business-guardrail-stage")
METRIC_NAME = "business_guardrail"

print("=" * 70)
print("CREATE CUSTOM LLM METRIC + PROTECT STAGE — Business Guardrail POC")
print("=" * 70)
print(f"\n[CONFIGURATION]")
print(f"  GALILEO_CONSOLE_URL:  {GALILEO_CONSOLE_URL or 'NOT SET'}")
print(f"  GALILEO_API_KEY:      {'***' + GALILEO_API_KEY[-4:] if GALILEO_API_KEY else 'NOT SET'}")
print(f"  GALILEO_PROJECT_NAME: {GALILEO_PROJECT_NAME or 'NOT SET'}")
print(f"  PROTECT_STAGE_NAME:   {PROTECT_STAGE_NAME}")
print(f"  METRIC_NAME:          {METRIC_NAME}")

missing_vars = []
if not GALILEO_CONSOLE_URL:
    missing_vars.append("GALILEO_CONSOLE_URL")
if not GALILEO_API_KEY:
    missing_vars.append("GALILEO_API_KEY")
if not GALILEO_PROJECT_NAME:
    missing_vars.append("GALILEO_PROJECT_NAME")

if missing_vars:
    print(f"\n[ERROR] Missing required environment variables:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nCopy .env.example to .env.local and fill in values.")
    sys.exit(1)

os.environ["GALILEO_CONSOLE_URL"] = GALILEO_CONSOLE_URL
os.environ["GALILEO_API_KEY"] = GALILEO_API_KEY
os.environ["GALILEO_PROJECT"] = GALILEO_PROJECT_NAME

# =============================================================================
# IMPORTS
# =============================================================================

print("\n[STEP 1] Importing Galileo SDK...")

try:
    from galileo.metrics import create_custom_llm_metric
    from galileo.projects import create_project, get_project
    from galileo.resources.models.output_type_enum import OutputTypeEnum
    from galileo.scorers import Scorers
    from galileo.stages import create_protect_stage, get_protect_stage
    from galileo_core.schemas.logging.step import StepType
    from galileo_core.schemas.protect.action import OverrideAction
    from galileo_core.schemas.protect.rule import Rule, RuleOperator
    from galileo_core.schemas.protect.ruleset import Ruleset
    from galileo_core.schemas.protect.stage import StageType
except ImportError as e:
    print(f"\n[ERROR] Failed to import Galileo SDK: {e}")
    print("\nInstall with: pip install galileo galileo-core")
    sys.exit(1)

print("  Galileo SDK imported successfully.")

# =============================================================================
# ENSURE PROJECT EXISTS
# =============================================================================

print(f"\n[STEP 2] Ensuring project '{GALILEO_PROJECT_NAME}' exists...")

existing_project = get_project(name=GALILEO_PROJECT_NAME)
if existing_project:
    print(f"  Project '{GALILEO_PROJECT_NAME}' found (ID: {existing_project.id})")
else:
    print(f"  Project '{GALILEO_PROJECT_NAME}' not found. Creating...")
    project = create_project(name=GALILEO_PROJECT_NAME)
    print(f"  Project created (ID: {project.id})")

# =============================================================================
# CREATE OR REUSE CUSTOM LLM METRIC
# =============================================================================

print(f"\n[STEP 3] Checking if metric '{METRIC_NAME}' already exists...")

existing_scorers = Scorers().list(name=METRIC_NAME)
if existing_scorers:
    print(f"  Metric '{METRIC_NAME}' already exists — skipping creation.")
else:
    print(f"  Metric '{METRIC_NAME}' not found. Creating custom LLM metric...")

    # This prompt template is evaluated by an LLM judge on every Protect invocation.
    # Variables {input} and {output} are populated from the Protect Payload.
    GUARDRAIL_PROMPT = """\
You are a content policy evaluator for a financial data service.

Evaluate the assistant's response below and return True if it violates ANY of the
following policies, or False if the response is fully compliant:

Policy 1 — Competitor Promotion:
  The response must not mention, recommend, or promote competitor products or services.
  Competitors include: Bloomberg Terminal, Refinitiv Eikon, FactSet, S&P Capital IQ.

Policy 2 — Stock Buying Advice:
  The response must not provide specific stock purchase or sale recommendations
  (e.g., "buy X stock", "I recommend purchasing Y", "now is a good time to invest in Z").

User message:
{input}

Assistant response:
{output}

Return True if ANY policy is violated. Return False if the response is fully compliant.
"""

    create_custom_llm_metric(
        name=METRIC_NAME,
        user_prompt=GUARDRAIL_PROMPT,
        node_level=StepType.llm,
        output_type=OutputTypeEnum.BOOLEAN,
        model_name="gpt-4.1-mini",
        num_judges=1,
        description="Flags competitor mentions and stock buying advice in real-time via Protect.",
        tags=["guardrail", "business-policy"],
    )
    print(f"  Custom LLM metric '{METRIC_NAME}' created.")

# =============================================================================
# CHECK FOR EXISTING STAGE
# =============================================================================

print(f"\n[STEP 4] Checking if stage '{PROTECT_STAGE_NAME}' already exists...")

existing_stage = get_protect_stage(
    stage_name=PROTECT_STAGE_NAME,
    project_name=GALILEO_PROJECT_NAME,
)
if existing_stage:
    print(f"\n{'=' * 70}")
    print("Stage already exists! Ready to use.")
    print(f"{'=' * 70}")
    print(f"\n  Stage Name: {existing_stage.name}")
    print(f"  Stage ID:   {existing_stage.id}")
    print(f"\n  run_poc.py will use stage_name='{PROTECT_STAGE_NAME}' automatically.")
    sys.exit(0)
else:
    print("  Stage not found. Will create it.")

# =============================================================================
# CREATE PROTECT STAGE
# =============================================================================

print(f"\n[STEP 5] Creating Protect stage with '{METRIC_NAME}' rule...")

# Trigger when the custom LLM metric returns True (a violation was detected)
rule = Rule(
    metric=METRIC_NAME,
    operator=RuleOperator.eq,
    target_value=True,
)
print(f"  Rule: {METRIC_NAME} == True  →  block response")

action = OverrideAction(
    choices=[
        "I'm not able to recommend specific investments or third-party financial platforms. "
        "Please consult a licensed financial advisor for investment decisions."
    ]
)
print("  Action: Override with policy compliance message")

ruleset = Ruleset(rules=[rule], action=action)

try:
    stage = create_protect_stage(
        name=PROTECT_STAGE_NAME,
        stage_type=StageType.central,
        prioritized_rulesets=[ruleset],
        description="POC: Custom LLM metric flags competitor mentions and stock advice in real-time",
        project_name=GALILEO_PROJECT_NAME,
    )

    print(f"\n{'=' * 70}")
    print("SUCCESS! Custom LLM metric + Protect stage created.")
    print(f"{'=' * 70}")
    print(f"\n  Metric Name: {METRIC_NAME}")
    print(f"  Stage Name:  {stage.name}")
    print(f"  Stage ID:    {stage.id}")
    print(f"\n  run_poc.py will use stage_name='{PROTECT_STAGE_NAME}' automatically.")

except Exception as e:
    print(f"\n[ERROR] Failed to create stage: {e}")
    sys.exit(1)
