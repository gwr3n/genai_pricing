from genai_pricing import estimate_costs

# ------- SAMPLE USAGE --------
# Usage-based cost estimation
# -----------------------------


def example():
    """Estimate model cost from a token usage dictionary."""
    model = "gpt-4.1"
    usage = {"prompt_tokens": 21_549, "completion_tokens": 7_091}
    estimate = estimate_costs(model, usage)

    print("Cost (USD):", estimate["total_cost"])
    print("Details:", estimate)


# ----- RUN EXAMPLE -----

if __name__ == "__main__":
    example()
