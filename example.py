import os
from types import SimpleNamespace

from openai import OpenAI

from genai_pricing import estimate_costs

# ------- SAMPLE USAGE --------
# OpenAI prompt cost estimation
# -----------------------------


def example():
    """Estimate the cost of an OpenAI prompt using genai_pricing."""
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    model = "gpt-5.6-sol"
    prompt = "Why is the sky blue?"

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=50,
    )

    usage = {
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
    }
    args = SimpleNamespace(model=model)
    estimate = estimate_costs(args, usage)  # <- use this line in your project

    print("Cost (USD):", estimate["total_cost"])


# ----- RUN EXAMPLE -----

if __name__ == "__main__":
    example()
