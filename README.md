# Galileo SDK Demos & POCs

A collection of demos and proof-of-concept projects showing how to use Galileo's SDK, metrics, and platform features. These originated from real customer engagements and are shared here to help anyone getting started with Galileo.

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your credentials:

```
GALILEO_API_KEY=your-api-key
GALILEO_CONSOLE_URL=https://console.galileo.ai
```

## Demos

### Custom Metrics

| Demo | Description |
|------|-------------|
| | Evaluate pre-written LLM outputs for gender bias using Galileo's custom metrics |
| | Custom metric scorer with credit/financial context |
| | Enforce custom business policies as real-time guardrails in Galileo Protect |
| | Detect medical/clinical advice in LLM responses using a code-based custom metric |
| | Classify conversations by theme (sleep, relationships) using custom metrics |
| | Run Galileo metrics on individual items when an LLM generates multiple outputs per call |

### Tracing & Instrumentation

| Demo | Description |
|------|-------------|
| | Three approaches to pass agent context for custom metrics (automatic capture, explicit metadata, dataset metadata) |
| | Agent invocation patterns with Galileo experiments |
| | Attach custom span attributes (`brand_id`, association properties) as metadata in Galileo |
| | Group follow-up questions as multiple traces within one session |
| | Apply span-level filters to metrics programmatically via the SDK |
| | Why `context_adherence_luna` scores differ between Protect and Log Stream |

### Experiments & Evaluation

| Demo | Description |
|------|-------------|
| | Evaluate pre-existing LLM outputs using Galileo Experiments with local LLM-as-judge metrics |
| | Offline evaluation experiment with chunked synthetic data |
| | Offline metric scoring for survey data |
| | Export metric scores with explanations and reasoning from the Traces Search API |

### Bug Reproductions

| Demo | Description |
|------|-------------|
| | Async event loop conflict reproduction |
| | Event loop issue reproduction with broken/fixed examples |
| | Missing greenlet dependency reproduction |
| | LLM span outputs appearing as flat JSON strings instead of expandable JSON |
| | OTLP-ingested spans getting server ingestion time instead of actual span timestamps |
| | JSON cleaning/parsing bug reproduction |
| | Intermittent "Failed to create template" error from Playground experiments |
