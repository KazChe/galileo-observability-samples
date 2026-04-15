#!/usr/bin/env python3
"""
=============================================================================
CREATE GALILEO PROTECT STAGE — Business Policy Guardrail POC
=============================================================================

Creates a Protect stage that uses the built-in context_adherence_luna metric
to enforce business policy at runtime.

The rule fires when context_adherence_luna < 0.5, meaning the response
contains claims not grounded in the compliant context provided in the
Protect payload.

REQUIRED ENVIRONMENT VARIABLES:
  GALILEO_API_KEY       - Your Galileo API key
  GALILEO_CONSOLE_URL   - Galileo console URL
  GALILEO_PROJECT_NAME  - Name of your Galileo project

OPTIONAL:
  GALILEO_PROTECT_STAGE_NAME - Stage name (default: business-policy-guard)

USAGE:
  1. Copy .env.example to .env.local and fill in values
  2. python create_stage.py
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
PROTECT_STAGE_NAME = os.getenv("GALILEO_PROTECT_STAGE_NAME", "business-policy-guard")

print("=" * 70)
print("CREATE GALILEO PROTECT STAGE — Business Policy Guardrail POC")
print("=" * 70)
print(f"\n[CONFIGURATION]")
print(f"  GALILEO_CONSOLE_URL:  {GALILEO_CONSOLE_URL or 'NOT SET'}")
print(f"  GALILEO_API_KEY:      {'***' + GALILEO_API_KEY[-4:] if GALILEO_API_KEY else 'NOT SET'}")
print(f"  GALILEO_PROJECT_NAME: {GALILEO_PROJECT_NAME or 'NOT SET'}")
print(f"  PROTECT_STAGE_NAME:   {PROTECT_STAGE_NAME}")

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
    from galileo import GalileoMetrics
    from galileo.projects import create_project, get_project
    from galileo.stages import create_protect_stage, get_protect_stage
    from galileo_core.schemas.protect.action import OverrideAction
    from galileo_core.schemas.protect.rule import Rule, RuleOperator
    from galileo_core.schemas.protect.ruleset import Ruleset
    from galileo_core.schemas.protect.stage import StageType
except ImportError as e:
    print(f"\n[ERROR] Failed to import Galileo SDK: {e}")
    print("\nInstall with: pip install -r requirements.txt")
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
# CHECK FOR EXISTING STAGE
# =============================================================================

print(f"\n[STEP 3] Checking if stage '{PROTECT_STAGE_NAME}' already exists...")

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

print(f"\n[STEP 4] Creating Protect stage with context_adherence_luna rule...")

# Trigger when context_adherence_luna < 0.5:
# the response makes claims not grounded in the compliant context passed
# in the Protect payload.
rule = Rule(
    metric=GalileoMetrics.context_adherence_luna,
    operator=RuleOperator.lt,
    target_value=0.5,
)
print(f"  Rule: context_adherence_luna < 0.5  →  block response")

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
        description="POC: context_adherence_luna < 0.5 blocks responses ungrounded in the policy context",
        project_name=GALILEO_PROJECT_NAME,
    )

    print(f"\n{'=' * 70}")
    print("SUCCESS! Protect stage created.")
    print(f"{'=' * 70}")
    print(f"\n  Stage Name: {stage.name}")
    print(f"  Stage ID:   {stage.id}")
    print(f"\n  run_poc.py will use stage_name='{PROTECT_STAGE_NAME}' automatically.")

except Exception as e:
    print(f"\n[ERROR] Failed to create stage: {e}")
    sys.exit(1)
