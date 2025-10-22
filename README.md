# genai_pricing

Estimate GenAI prompt costs from a unified, auto-updated pricing table. This repo provides a tiny helper around OpenAI responses plus a parser for a curated model pricing table.

- Parses the pricing table at [`genai_pricing.PRICING_URL`](genai_pricing.py) or a local file
- Computes token usage (OpenAI usage when available, falls back to approximate/tiktoken)
- Returns per-prompt cost breakdown for prompt and completion tokens
- Works with the included table at [data/pricing_table.md](data/pricing_table.md)

## Installation

- Python 3.8+
- Packages:
  - openai
  - tiktoken

```sh
pip install openai tiktoken
```

Set your OpenAI API key:

```sh
export OPENAI_API_KEY=YOUR_KEY
```

## Quick start

The included example shows how to run a Chat Completions request and get a cost estimate using [`genai_pricing.openai_client`](genai_pricing.py) and [`genai_pricing.openai_prompt_cost`](genai_pricing.py). See [example.py](example.py).

```python
# Minimal example
from genai_pricing import openai_client, openai_prompt_cost

client = openai_client()
model = "gpt-4.1"
prompt = "Why is the sky blue?"

resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=50,
)

answer = resp.choices[0].message.content
estimate = openai_prompt_cost(model, prompt, answer, resp)

print("Cost (USD):", estimate["total_cost"])
print("Details:", estimate)
```

Run the example:

```sh
python example.py
```

## How cost is computed

Prices are looked up by model name in the pricing table, then applied to token counts:

$$
C = \frac{t_\text{in}}{10^6}\, p_\text{in} + \frac{t_\text{out}}{10^6}\, p_\text{out}
$$

- $t_\text{in}$: prompt tokens
- $t_\text{out}$: completion tokens
- $p_\text{in}$: USD per 1M input tokens
- $p_\text{out}$: USD per 1M output tokens

If the OpenAI response includes usage, that is used. Otherwise, the library uses tiktoken when possible, with a lightweight fallback heuristic.

## Pricing table

By default, prices are pulled from [`genai_pricing.PRICING_URL`](genai_pricing.py), which normalizes GitHub blob URLs to raw content and fetches with a short timeout. A local table is also included at [data/pricing_table.md](data/pricing_table.md) for offline/reference use.

To pin a specific table, point [`genai_pricing.PRICING_URL`](genai_pricing.py) to a raw URL or a local file path.

## Testing

The project uses Python’s built-in unittest.

- Run all tests (discovery):
```sh
python -m unittest discover -s test -p "*_test.py" -v
```

## API surface

- [`genai_pricing.openai_client`](genai_pricing.py)
  - Returns a preconfigured OpenAI client (uses OPENAI_API_KEY)
- [`genai_pricing.openai_prompt_cost`](genai_pricing.py)
  - Computes a dict with prompt/completion tokens, per-side costs, and total_cost

Key constant:

- [`genai_pricing.PRICING_URL`](genai_pricing.py) — remote table to fetch by default

## License

MIT © 2025 Roberto Rossi

## Acknowledgements

Pricing data sourced from the AgentOps tokencost table and mirrored (22 Oct 2025) locally at [data/pricing_table.md](data/pricing_table.md) for testing purposes.