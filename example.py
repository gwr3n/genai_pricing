from genai_pricing import openai_client, openai_prompt_cost

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
    estimate = openai_prompt_cost(model, prompt, answer, resp)  # <- use this line in your project

    print("Cost (USD):", estimate["total_cost"])


# ----- RUN EXAMPLE -----

if __name__ == "__main__":
    example()
