"""
Credit Context Scorer Experiment

Demonstrates how to use the custom "credit_context_scorer" with dataset metadata.
The scorer evaluates if LLM responses are appropriate for the customer's credit tier.

Usage:
    python -m agent_context_demo.yellow_metric_experiment
"""

import os
from dotenv import load_dotenv
load_dotenv()

from galileo.datasets import create_dataset, get_dataset
from galileo.experiments import run_experiment
from galileo.prompts import create_prompt, get_prompt
from galileo.resources.models.prompt_run_settings import PromptRunSettings
from galileo.schema.message import Message
from galileo_core.schemas.logging.llm import MessageRole


def create_test_dataset(
    project: str = "agent-context-demo",
    dataset_name: str = "credit-context-test-dataset"
):
    """
    Create a test dataset with customer metadata.

    Each row contains customer information that the yellow_metric
    can access for evaluation purposes.
    """
    print("\n" + "=" * 60)
    print("Creating Credit Context Scorer Test Dataset")
    print("=" * 60)

    dataset_content = [
        {
            "input": "What are the best practices for improving credit scores?",
            "output": "To improve your credit score, pay bills on time, reduce debt, and avoid opening too many new accounts.",
            "metadata": {
                "customer": "Abe Mornal",
                "credit_score": "680",
                "request_type": "credit_advice",
            }
        },
        {
            "input": "Explain the difference between secured and unsecured loans.",
            "output": "Secured loans require collateral while unsecured loans do not.",
            "metadata": {
                "customer": "Jane Smith",
                "credit_score": "750",
                "request_type": "loan_info",
            }
        },
        {
            "input": "What factors affect mortgage approval?",
            "output": "Mortgage approval depends on credit score, income, debt-to-income ratio, and down payment.",
            "metadata": {
                "customer": "Bob Johnson",
                "credit_score": "620",
                "request_type": "mortgage_info",
            }
        },
        {
            "input": "How can I reduce my monthly debt payments?",
            "output": "Consider debt consolidation, refinancing, or negotiating with creditors.",
            "metadata": {
                "customer": "Alice Williams",
                "credit_score": "710",
                "request_type": "debt_management",
            }
        },
    ]

    print(f"\nDataset '{dataset_name}' with {len(dataset_content)} test cases:")
    for i, row in enumerate(dataset_content, 1):
        meta = row['metadata']
        print(f"  {i}. Customer: {meta['customer']}, Credit Score: {meta['credit_score']}")

    # Try to get existing dataset, or create new one
    try:
        dataset = get_dataset(name=dataset_name, project_name=project)
        print(f"\nUsing existing dataset: {dataset.name}")
    except Exception:
        print(f"\nCreating new dataset...")
        dataset = create_dataset(
            name=dataset_name,
            content=dataset_content,
            project_name=project
        )
        print(f"Dataset created: {dataset.name}")

    return dataset


def run_yellow_metric_experiment(
    project: str = "agent-context-demo",
    dataset_name: str = "credit-context-test-dataset",
    experiment_name: str = "credit-context-evaluation"
):
    """
    Run an experiment using the custom yellow_metric.

    Uses prompt_template approach (same as experiment_dataset.py) which
    leverages Galileo's LLM integration instead of requiring a local OpenAI key.

    The yellow_metric scorer accesses metadata from LlmSpan objects:
    - step_object.metadata.get("credit_score")
    - step_object.metadata.get("customer")
    """
    print("\n" + "-" * 60)
    print("Running Credit Context Scorer Experiment")
    print("-" * 60)

    # Get or create the dataset
    try:
        dataset = get_dataset(name=dataset_name, project_name=project)
        print(f"Using existing dataset: {dataset_name}")
    except Exception:
        print(f"Dataset not found, creating new one...")
        dataset = create_test_dataset(project=project, dataset_name=dataset_name)

    print(f"\nRunning experiment: {experiment_name}")
    print("Using custom metric: credit_context_scorer")
    print("The metric will access dataset metadata (customer, credit_score)")

    # Get or create prompt template
    # Include customer context so LLM can give tier-appropriate advice
    prompt = get_prompt(name="credit-context-prompt-v2")
    if prompt is None:
        print("Creating new prompt template with customer context...")
        prompt = create_prompt(
            name="credit-context-prompt-v2",
            template=[
                Message(
                    role=MessageRole.system,
                    content="""You are a helpful financial advisor assistant.

Customer Context:
- Name: {{metadata.customer}}
- Credit Score: {{metadata.credit_score}}

Tailor your advice based on the customer's credit profile:
- 750+: Excellent credit - mention premium options, best rates
- 670-749: Good credit - mention competitive options they qualify for
- 580-669: Fair credit - focus on improvement strategies, secured options
- Below 580: Poor credit - emphasize rebuilding steps, secured cards

Be helpful and appropriate for their situation."""
                ),
                Message(role=MessageRole.user, content="{{input}}")
            ]
        )
    else:
        print("Using existing prompt template")

    # Run experiment with prompt_template (uses Galileo's LLM integration)
    try:
        results = run_experiment(
            experiment_name=experiment_name,
            project=project,
            dataset=dataset,
            prompt_template=prompt,
            prompt_settings=PromptRunSettings(model_alias="GPT-4o"),
            metrics=["credit_context_scorer"],
        )
    except Exception as e:
        error_msg = str(getattr(e, 'response_text', str(e)))
        if "not available in any of your integrations" in error_msg:
            print("\n" + "!" * 60)
            print("ERROR: No LLM integration configured in Galileo")
            print("!" * 60)
            print("\nTo use prompt_template:")
            print("1. Go to Galileo Console > Settings > Integrations")
            print("2. Add your OpenAI or other LLM provider API key")
            print("3. Re-run this experiment")
            return None
        raise

    print(f"\nExperiment complete!")

    # Print experiment link
    console_url = os.getenv("GALILEO_CONSOLE_URL", "https://console.galileo.ai")

    if results and isinstance(results, dict):
        if 'link' in results:
            print(f"View experiment at: {results['link']}")
        elif 'id' in results:
            project_id = results.get('project_id', project)
            experiment_id = results['id']
            print(f"View experiment at: {console_url}/project/{project_id}/experiments/{experiment_id}")
        else:
            print(f"View experiments at: {console_url}/project/{project}/experiments")
    else:
        print(f"View experiments at: {console_url}/project/{project}/experiments")

    return results


if __name__ == "__main__":
    # Create the test dataset
    dataset = create_test_dataset()

    # Run the experiment with yellow_metric
    print("\n" + "=" * 60)
    print("Starting Credit Context Scorer Experiment")
    print("=" * 60)
    results = run_yellow_metric_experiment()

    if results:
        print("\n" + "=" * 60)
        print("Experiment Results")
        print("=" * 60)
        print(f"Results type: {type(results)}")
        if hasattr(results, '__dict__'):
            for key, value in vars(results).items():
                print(f"  {key}: {value}")
