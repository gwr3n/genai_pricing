import os
from types import SimpleNamespace

from genai_pricing import estimate_costs

# ----- PUBLIC UTILITIES -----


def openai_client():
    try:
        # prefer new-style client if available
        from openai import OpenAI  # type: ignore
    except Exception:
        OpenAI = None
    try:
        import openai as openai_mod  # type: ignore
    except Exception:
        openai_mod = None

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY (or OPENAI_KEY) environment variable not set.")

    if OpenAI is not None:
        try:
            return OpenAI(api_key=api_key)
        except Exception:
            # fall back to module-level OpenAI instance if available
            pass

    if openai_mod is not None:
        # older openai library style
        try:
            # set the module-level api key and return module for callers that expect it
            setattr(openai_mod, "api_key", api_key)
            return openai_mod
        except Exception:
            pass

    raise RuntimeError("openai is installed but could not construct a client. Ensure openai package is up to date.")

# ------- SAMPLE USAGE --------
# OpenAI prompt cost estimation
# -----------------------------


def example():
    """Estimate the cost of an OpenAI prompt using genai_pricing."""
    client = openai_client()
    model = "gpt-4.1"
    prompt = "Why is the sky blue?"

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
    )

    answer = resp.choices[0].message.content
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
