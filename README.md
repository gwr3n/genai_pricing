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

- Parses a local LiteLLM pricing snapshot when present, otherwise falls back to [`genai_pricing.PRICING_URL`](genai_pricing.py)
- Computes costs from prompt, completion, cache-creation, and cache-read token usage
- Includes internal helpers for OpenAI/Gemini-style usage extraction and fallback token counting

## Installation

- Python 3.8+
- Packages:
  - tiktoken

```sh
pip install tiktoken
```

## Quick start

The included example shows how to estimate cost from an args-like object and token usage dictionary using [`genai_pricing.estimate_costs`](genai_pricing.py). See [example.py](example.py).

```python
# Minimal example
import os
from openai import OpenAI
from types import SimpleNamespace

from genai_pricing import estimate_costs

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

answer = resp.choices[0].message.content
usage = {
    "prompt_tokens": resp.usage.prompt_tokens,
    "completion_tokens": resp.usage.completion_tokens,
  "cache_read_input_tokens": resp.usage.prompt_tokens_details.cached_tokens,
}
args = SimpleNamespace(model=model)
estimate = estimate_costs(args, usage)  # <- use this line in your project

print("Cost (USD):", estimate["total_cost"])
```

Run the example:

```sh
python example.py
```

## How cost is computed

Prices are looked up by model name in the pricing table, then applied to token counts. `prompt_tokens` is the provider-reported total input count; cache creation and cache read counts are subsets charged in place of regular input:

$$
C = \frac{(t_\text{in} - t_\text{create} - t_\text{read})p_\text{in} + t_\text{create}p_\text{create} + t_\text{read}p_\text{read} + t_\text{out}p_\text{out}}{10^6}
$$

- $t_\text{in}$: prompt tokens
- $t_\text{create}$: `cache_creation_input_tokens`, when reported
- $t_\text{read}$: `cache_read_input_tokens`, when reported
- $t_\text{out}$: completion tokens
- $p$: the corresponding USD price per 1M tokens

The result includes `prompt_cost`, `cache_creation_cost`, `cache_read_cost`, and `completion_cost` when applicable, plus `total_cost`. If a model has no cache-specific rate, cached tokens fall back to its regular input rate.

Provide token counts from your model provider when available. Internal helpers can extract OpenAI- and Gemini-style usage metadata and fall back to tiktoken or a lightweight heuristic when needed.

## Pricing table

By default, prices are resolved in this order:

1. `model_prices_and_context_window_backup.json` in the current working directory
2. `model_prices_and_context_window_backup.json` near the package/repository location
3. [`genai_pricing.PRICING_URL`](genai_pricing.py), the remote LiteLLM JSON source

The parsed pricing table is cached. Call `clear_pricing_cache()` after changing the local snapshot or when you want the remote source fetched again.

## Testing

The project uses Python’s built-in unittest.

- Run all tests (discovery):
```sh
python -m unittest discover -s test -p "*_test.py" -v
```

## API surface

- [`genai_pricing.estimate_costs`](genai_pricing.py)
  - Computes a dict with prompt/completion costs and `total_cost` from an object with a `.model` attribute and a usage dictionary
- [`genai_pricing.clear_pricing_cache`](genai_pricing.py)
  - Clears cached pricing data so the configured source is fetched or read again

Key constant:

- [`genai_pricing.PRICING_URL`](genai_pricing.py) — remote table to fetch by default

## License

MIT © 2025 Roberto Rossi

## Acknowledgements

Pricing data sourced from the AgentOps tokencost table and mirrored (22 Oct 2025) locally at [data/pricing_table.md](data/pricing_table.md) for testing purposes.