# genai_pricing

Core package badges:

![Codecov (with branch)](https://img.shields.io/codecov/c/gh/gwr3n/genai_pricing/main)
 ![Python package](https://img.shields.io/github/actions/workflow/status/gwr3n/genai_pricing/.github%2Fworkflows%2Fpython-package.yml) ![Lint and type-check](https://img.shields.io/github/actions/workflow/status/gwr3n/genai_pricing/.github%2Fworkflows%2Flint-type.yml?branch=main&label=lint%20%2B%20type-check) [![License](https://img.shields.io/github/license/gwr3n/genai_pricing)](LICENSE) [![Release](https://img.shields.io/github/v/release/gwr3n/genai_pricing)](https://github.com/gwr3n/genai_pricing/releases)
 [PYPI](https://pypi.org/project/genai-pricing/) 
 [![Downloads](https://pepy.tech/badge/genai-pricing)](https://pepy.tech/project/genai-pricing) 

Quality and tooling:

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000?logo=python)](https://github.com/psf/black) [![Ruff](https://img.shields.io/badge/lint-ruff-1f79ff?logo=python)](https://github.com/astral-sh/ruff) [![mypy](https://img.shields.io/badge/type--checked-mypy-blue?logo=python)](https://github.com/python/mypy)

Project/community:

[![Issues](https://img.shields.io/github/issues/gwr3n/genai_pricing)](https://github.com/gwr3n/genai_pricing/issues) [![PRs](https://img.shields.io/github/issues-pr/gwr3n/genai_pricing)](https://github.com/gwr3n/genai_pricing/pulls) [![Stars](https://img.shields.io/github/stars/gwr3n/genai_pricing?style=social)](https://github.com/gwr3n/genai_pricing/stargazers)

Docs:

[![Docs](https://img.shields.io/badge/docs-site-blue)](https://github.com/gwr3n/genai_pricing)

Estimate GenAI prompt costs from a unified, auto-updated pricing table. This repo provides a small usage-based cost estimator plus parsers for LiteLLM JSON and markdown pricing tables.

- Parses the pricing table at [`genai_pricing.PRICING_URL`](genai_pricing.py) or a local file
- Computes costs from a usage dictionary with `prompt_tokens` and `completion_tokens`
- Includes internal helpers for OpenAI/Gemini-style usage extraction and fallback token counting

## Installation

- Python 3.8+
- Packages:
  - tiktoken

```sh
pip install tiktoken
```

## Quick start

The included example shows how to estimate cost from a model name and token usage dictionary using [`genai_pricing.estimate_costs`](genai_pricing.py). See [example.py](example.py).

```python
# Minimal example
from genai_pricing import estimate_costs

model = "gpt-4.1"
usage = {"prompt_tokens": 21_549, "completion_tokens": 7_091}
estimate = estimate_costs(model, usage)

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

Provide token counts from your model provider when available. Internal helpers can extract OpenAI- and Gemini-style usage metadata and fall back to tiktoken or a lightweight heuristic when needed.

## Pricing table

By default, prices are read from [`genai_pricing.PRICING_URL`](genai_pricing.py), the remote LiteLLM JSON source.

To pin a specific table, pass `pricing_source` as a raw URL or local file path. For a local LiteLLM snapshot, use a path ending in `model_prices_and_context_window_backup.json`.

## Testing

The project uses Python’s built-in unittest.

- Run all tests (discovery):
```sh
python -m unittest discover -s test -p "*_test.py" -v
```

## API surface

- [`genai_pricing.estimate_costs`](genai_pricing.py)
  - Computes a dict with prompt/completion costs and `total_cost` from a model name, a usage dictionary, and an optional `pricing_source`
- [`genai_pricing.clear_pricing_cache`](genai_pricing.py)
  - Clears cached pricing data so the configured source is fetched or read again

Key constant:

- [`genai_pricing.PRICING_URL`](genai_pricing.py) — remote table to fetch by default

## License

MIT © 2025 Roberto Rossi

## Acknowledgements

Pricing data sourced from the AgentOps tokencost table and mirrored (22 Oct 2025) locally at [data/pricing_table.md](data/pricing_table.md) for testing purposes.