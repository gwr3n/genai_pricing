# genai_pricing

Core package badges:

![Codecov (with branch)](https://img.shields.io/codecov/c/gh/gwr3n/genai_pricing/main)
 ![Python package](https://img.shields.io/github/actions/workflow/status/gwr3n/genai_pricing/.github%2Fworkflows%2Fpython-package.yml) ![Lint and type-check](https://img.shields.io/github/actions/workflow/status/gwr3n/genai_pricing/.github%2Fworkflows%2Flint-type.yml?branch=main&label=lint%20%2B%20type-check) [![Python versions](https://img.shields.io/pypi/pyversions/genai_pricing)](https://pypi.org/project/genai_pricing/) [![License](https://img.shields.io/github/license/gwr3n/genai_pricing)](LICENSE) [![Downloads](https://static.pepy.tech/badge/genai_pricing)](https://pepy.tech/project/genai_pricing) [![Release](https://img.shields.io/github/v/release/gwr3n/genai_pricing)](https://github.com/gwr3n/genai_pricing/releases)

Quality and tooling:

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000?logo=python)](https://github.com/psf/black) [![Ruff](https://img.shields.io/badge/lint-ruff-1f79ff?logo=python)](https://github.com/astral-sh/ruff) [![mypy](https://img.shields.io/badge/type--checked-mypy-blue?logo=python)](https://github.com/python/mypy)

Project/community:

[![Issues](https://img.shields.io/github/issues/gwr3n/genai_pricing)](https://github.com/gwr3n/genai_pricing/issues) [![PRs](https://img.shields.io/github/issues-pr/gwr3n/genai_pricing)](https://github.com/gwr3n/genai_pricing/pulls) [![Stars](https://img.shields.io/github/stars/gwr3n/genai_pricing?style=social)](https://github.com/gwr3n/genai_pricing/stargazers)

Docs:

[![Docs](https://img.shields.io/badge/docs-site-blue)](https://github.com/gwr3n/genai_pricing)

Estimate GenAI prompt costs from a unified, auto-updated pricing table. This repo provides a tiny helper around OpenAI responses plus a parser for a curated model pricing table.

- Parses the pricing table at [`genai_pricing.PRICING_URL`](genai_pricing.py) or a local file
- Computes token usage (OpenAI usage when available, falls back to approximate/tiktoken)
- Returns per-prompt cost breakdown for prompt and completion tokens

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
estimate = openai_prompt_cost(model, prompt, answer, resp) # <- use this line in your project

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
C = \frac{t_\text{in}}{10^6}\. p_\text{in} + \frac{t_\text{out}}{10^6}\. p_\text{out}
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