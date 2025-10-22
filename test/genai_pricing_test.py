import unittest
from pathlib import Path

import genai_pricing as gp
import os
import sys
import types
import tempfile
from types import SimpleNamespace
from unittest import mock


class TestParsePricing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.md_path = cls.project_root / "data" / "pricing_table.md"
        if not cls.md_path.exists():
            raise unittest.SkipTest(f"Missing pricing table: {cls.md_path}")

    def setUp(self):
        gp.clear_pricing_cache()

    def test_parse_known_rows(self):
        rates = gp._parse_pricing(str(self.md_path))

        # Basic presence
        self.assertIn("gpt-4o", rates)
        self.assertIn("gpt-4o-mini", rates)
        self.assertIn("gpt-4", rates)
        self.assertIn("openai/gpt-realtime-2025-08-28", rates)

        # Check numeric values (header says per 1M tokens)
        self.assertAlmostEqual(rates["gpt-4o"]["prompt_per_1M"], 2.5)
        self.assertAlmostEqual(rates["gpt-4o"]["completion_per_1M"], 10.0)

        self.assertAlmostEqual(rates["gpt-4o-mini"]["prompt_per_1M"], 0.15)
        self.assertAlmostEqual(rates["gpt-4o-mini"]["completion_per_1M"], 0.6)

        self.assertAlmostEqual(rates["gpt-4"]["prompt_per_1M"], 30.0)
        self.assertAlmostEqual(rates["gpt-4"]["completion_per_1M"], 60.0)

        self.assertAlmostEqual(
            rates["openai/gpt-realtime-2025-08-28"]["prompt_per_1M"], 4.0
        )
        self.assertAlmostEqual(
            rates["openai/gpt-realtime-2025-08-28"]["completion_per_1M"], 16.0
        )

    def test_header_not_included_as_row(self):
        rates = gp._parse_pricing(str(self.md_path))
        self.assertNotIn("model name", rates)

    def test_empty_pricing_table(self):
        empty_md_path = self.project_root / "data" / "empty_pricing_table.md"
        rates = gp._parse_pricing(str(empty_md_path))
        self.assertEqual(rates, {})

    # ---- Additional tests to cover all methods ----

    def test_parse_pricing_invalid_path_returns_empty(self):
        rates = gp._parse_pricing(str(self.project_root / "data" / "does_not_exist.md"))
        self.assertEqual(rates, {})

    def test_parse_pricing_inline_and_header_units(self):
        content = """\
| Model | Prompt (per 1K) | Completion |
|:------|:-----------------|:-----------|
| test-model | $0.20 | $1.50 / 1M |
other-model: prompt $0.05 / 1K, completion $0.25 / 1K
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        try:
            rates = gp._parse_pricing(tmp_path)
            # Header says Prompt per 1K => 0.20 per 1K => 200 per 1M
            self.assertAlmostEqual(rates["test-model"]["prompt_per_1M"], 200.0)
            # Completion explicitly per 1M stays 1.5
            self.assertAlmostEqual(rates["test-model"]["completion_per_1M"], 1.5)
            # Inline line: both per 1K => multiply by 1000
            self.assertAlmostEqual(rates["other-model"]["prompt_per_1M"], 50.0)
            self.assertAlmostEqual(rates["other-model"]["completion_per_1M"], 250.0)
        finally:
            os.unlink(tmp_path)

    def test_parse_pricing_from_url_and_cache_clear(self):
        md = """\
| Model | Prompt (per 1K) | Completion (per 1K) |
|:------|:-----------------|:--------------------|
| url-model | $0.10 | $0.20 |
"""
        class FakeResp:
            def __init__(self, text):
                self._text = text.encode("utf-8")
            def read(self):
                return self._text
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False

        calls = {"n": 0}
        def fake_urlopen(req, timeout=10):
            calls["n"] += 1
            return FakeResp(md)

        blob_url = "https://github.com/user/repo/blob/main/pricing_table.md"
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            # First call fetches
            r1 = gp._parse_pricing(blob_url)
            self.assertIn("url-model", r1)
            self.assertEqual(calls["n"], 1)
            # Second call should be cached
            r2 = gp._parse_pricing(blob_url)
            self.assertEqual(calls["n"], 1)
            self.assertEqual(r1, r2)
            # Clear cache forces refetch
            gp.clear_pricing_cache()
            r3 = gp._parse_pricing(blob_url)
            self.assertEqual(calls["n"], 2)
            self.assertEqual(r3["url-model"]["prompt_per_1M"], 100.0)
            self.assertEqual(r3["url-model"]["completion_per_1M"], 200.0)

    def test__approx_token_count(self):
        self.assertEqual(gp._approx_token_count(""), 0)
        self.assertEqual(gp._approx_token_count("a"), 1)
        self.assertEqual(gp._approx_token_count("abcd"), 1)
        self.assertEqual(gp._approx_token_count("abcdefgh"), 2)

    def test__count_openai_tokens_fallback_without_tiktoken(self):
        text = "hello world"
        with mock.patch.dict(sys.modules, {"tiktoken": None}):
            n = gp._count_openai_tokens(text, "any-model")
        # approx: ceil(len/4) = (11+3)//4=3
        self.assertEqual(n, 3)

    def test__count_openai_tokens_with_fake_tiktoken(self):
        # Provide a fake tiktoken to exercise happy path
        class FakeEnc:
            def encode(self, text):
                return list(range(7))  # pretend 7 tokens
        fake = types.ModuleType("tiktoken")
        def encoding_for_model(model):
            return FakeEnc()
        fake.encoding_for_model = encoding_for_model
        with mock.patch.dict(sys.modules, {"tiktoken": fake}):
            n = gp._count_openai_tokens("some text", "gpt-4o")
        self.assertEqual(n, 7)

    def test__count_openai_tokens_with_fallback_encodings(self):
        # encoding_for_model raises, falls back to o200k_base then cl100k_base
        class FakeEnc:
            def encode(self, text):
                return [0, 1, 2, 3]  # 4 tokens
        fake = types.ModuleType("tiktoken")
        def encoding_for_model(model):
            raise RuntimeError("no encoding")
        def get_encoding(name):
            return FakeEnc()
        fake.encoding_for_model = encoding_for_model
        fake.get_encoding = get_encoding
        with mock.patch.dict(sys.modules, {"tiktoken": fake}):
            n = gp._count_openai_tokens("text", "unknown-model")
        self.assertEqual(n, 4)

    def test__usage_dict(self):
        d = gp._usage_dict(5, None)
        self.assertEqual(d, {"prompt_tokens": 5, "completion_tokens": 0})

    def test__extract_openai_usage_from_usage_keys(self):
        resp = {"usage": {"input_tokens": 10, "output_tokens": 20}}
        with mock.patch.object(gp, "_count_openai_tokens", side_effect=AssertionError("should not be called")):
            usage = gp._extract_openai_usage(resp, "in", "out", "gpt-4o")
        self.assertEqual(usage, {"prompt_tokens": 10, "completion_tokens": 20})

    def test__extract_openai_usage_fallback_counts(self):
        # No usage -> falls back to counting function
        with mock.patch.object(gp, "_count_openai_tokens", side_effect=[3, 7]):
            usage = gp._extract_openai_usage({}, "abc", "defghij", "gpt-4o")
        self.assertEqual(usage, {"prompt_tokens": 3, "completion_tokens": 7})

    def test__estimate_costs_with_exact_model(self):
        fake_rates = {
            "gpt-4o": {"prompt_per_1M": 2.0, "completion_per_1M": 8.0}
        }
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates):
            args = SimpleNamespace(model="gpt-4o")
            usage = {"prompt_tokens": 500_000, "completion_tokens": 250_000}
            est = gp._estimate_costs(args, usage)
        self.assertAlmostEqual(est["prompt_cost"], 2.0 * 0.5)
        self.assertAlmostEqual(est["completion_cost"], 8.0 * 0.25)
        self.assertAlmostEqual(est["total_cost"], est["prompt_cost"] + est["completion_cost"])

    def test__estimate_costs_substring_and_last_resort(self):
        fake_rates = {
            "foo": {"prompt_per_1M": 1.0, "completion_per_1M": None},
            "bar": {"prompt_per_1M": None, "completion_per_1M": 4.0},
        }
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates):
            # substring match: "foo-bar" should match "foo"
            args = SimpleNamespace(model="foo-bar")
            usage = {"prompt_tokens": 100_000, "completion_tokens": 100_000}
            est = gp._estimate_costs(args, usage)
            self.assertAlmostEqual(est.get("prompt_cost", 0.0), 0.1)
            # completion rate None -> only prompt cost counted
            self.assertNotIn("completion_cost", est)
            # total is sum (only prompt_cost)
            self.assertAlmostEqual(est["total_cost"], 0.1)

            # No matching key -> last resort: pick first numeric entry in dict order
            args2 = SimpleNamespace(model="no-match")
            est2 = gp._estimate_costs(args2, usage)
            # It should pick "foo" (first numeric prompt_per_1M)
            self.assertAlmostEqual(est2["prompt_cost"], 0.1)

    def test_openai_client_env_missing(self):
        # Ensure imports don't blow up; provide openai module without OpenAI attribute
        mod = types.ModuleType("openai")
        with mock.patch.dict(sys.modules, {"openai": mod}), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                gp.openai_client()

    def test_openai_client_new_style(self):
        class FakeClient:
            def __init__(self, api_key=None):
                self.api_key = api_key
        mod = types.ModuleType("openai")
        mod.OpenAI = FakeClient  # for "from openai import OpenAI"
        with mock.patch.dict(sys.modules, {"openai": mod}), mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-123"}):
            client = gp.openai_client()
            self.assertIsInstance(client, FakeClient)
            self.assertEqual(client.api_key, "sk-123")

    def test_openai_client_fallback_to_modulelevel(self):
        class FailingClient:
            def __init__(self, api_key=None):
                raise RuntimeError("ctor failed")
        # openai module object to return
        mod = types.ModuleType("openai")
        mod.OpenAI = FailingClient
        with mock.patch.dict(sys.modules, {"openai": mod}), mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-xyz"}):
            client_mod = gp.openai_client()
            # Should be the module itself with api_key set
            self.assertIs(client_mod, mod)
            self.assertEqual(getattr(client_mod, "api_key"), "sk-xyz")

    def test_openai_client_failure_when_setattr_fails(self):
        class FailingClient:
            def __init__(self, api_key=None):
                raise RuntimeError("ctor failed")
        class NoSetAttr(types.ModuleType):
            def __setattr__(self, name, value):
                if name == "api_key":
                    raise RuntimeError("no setattr")
                return super().__setattr__(name, value)

        mod = NoSetAttr("openai")
        mod.OpenAI = FailingClient
        with mock.patch.dict(sys.modules, {"openai": mod}), mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-xyz"}):
            with self.assertRaisesRegex(RuntimeError, "could not construct a client"):
                gp.openai_client()

    def test_openai_prompt_cost_uses_usage_and_pricing(self):
        fake_rates = {
            "my-model": {"prompt_per_1M": 3.0, "completion_per_1M": 5.0}
        }
        resp = {"usage": {"prompt_tokens": 200_000, "completion_tokens": 100_000}}
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates):
            est = gp.openai_prompt_cost("my-model", "ignored prompt", "ignored answer", resp)
        self.assertAlmostEqual(est["prompt_cost"], 3.0 * 0.2)
        self.assertAlmostEqual(est["completion_cost"], 5.0 * 0.1)
        self.assertAlmostEqual(est["total_cost"], est["prompt_cost"] + est["completion_cost"])


if __name__ == "__main__":
    unittest.main()
