import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import genai_pricing as gp


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

        self.assertAlmostEqual(rates["openai/gpt-realtime-2025-08-28"]["prompt_per_1M"], 4.0)
        self.assertAlmostEqual(rates["openai/gpt-realtime-2025-08-28"]["completion_per_1M"], 16.0)

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

    def test_parse_markdown_pricing_skips_comments_and_non_numeric_rows(self):
        content = """\
# comment
| Model | Prompt | Completion |
|:------|:-------|:-----------|
| text-only | unavailable | unavailable |
bad-inline: prompt unavailable, completion unavailable
"""
        self.assertEqual(gp._parse_markdown_pricing(content), {})

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

    def test_resolve_pricing_source_prefers_current_working_directory_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot = Path(tmp_dir) / gp.LOCAL_PRICING_FILENAME
            snapshot.write_text("{}", encoding="utf8")
            with mock.patch("genai_pricing.Path.cwd", return_value=Path(tmp_dir)):
                self.assertEqual(gp._resolve_pricing_source(), str(snapshot))

    def test_resolve_pricing_source_prefers_repo_root_snapshot(self):
        module_path = self.project_root / "pkg" / "subpkg" / "genai_pricing.py"
        snapshot = self.project_root / gp.LOCAL_PRICING_FILENAME
        snapshot.write_text("{}", encoding="utf8")
        try:
            with mock.patch("genai_pricing.Path.cwd", return_value=Path("/tmp/no-pricing-here")):
                with mock.patch.object(gp, "__file__", str(module_path)):
                    self.assertEqual(gp._resolve_pricing_source(), str(snapshot))
        finally:
            snapshot.unlink()

    def test_resolve_pricing_source_prefers_module_directory_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            module_path = Path(tmp_dir) / "genai_pricing.py"
            snapshot = Path(tmp_dir) / gp.LOCAL_PRICING_FILENAME
            snapshot.write_text("{}", encoding="utf8")
            with mock.patch("genai_pricing.Path.cwd", return_value=Path("/tmp/no-pricing-here")):
                with mock.patch.object(gp, "__file__", str(module_path)):
                    self.assertEqual(Path(gp._resolve_pricing_source()).resolve(), snapshot.resolve())

    def test_read_pricing_text_rejects_unsupported_url_scheme(self):
        with self.assertRaisesRegex(ValueError, "Unsupported pricing URL scheme"):
            gp._read_pricing_text("ftp://example.com/prices.json")

    def test_parse_pricing_unsupported_extension_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("not a supported pricing source")
            tmp_path = f.name
        try:
            self.assertEqual(gp._parse_pricing(tmp_path), {})
        finally:
            os.unlink(tmp_path)

    def test_parse_litellm_json_pricing(self):
        content = json.dumps(
            {
                "sample_spec": {"input_cost_per_token": 99},
                "ignored-string": "not a spec",
                "ignored-bool": {"input_cost_per_token": True, "output_cost_per_token": False},
                "json-model": {"input_cost_per_token": 0.000001, "output_cost_per_token": 0.000002},
                "input-only": {"input_cost_per_token": 0.000003},
            }
        )
        rates = gp._parse_litellm_json_pricing(content, "prices.json")

        self.assertNotIn("sample_spec", rates)
        self.assertNotIn("ignored-string", rates)
        self.assertNotIn("ignored-bool", rates)
        self.assertAlmostEqual(rates["json-model"]["prompt_per_1M"], 1.0)
        self.assertAlmostEqual(rates["json-model"]["completion_per_1M"], 2.0)
        self.assertAlmostEqual(rates["input-only"]["prompt_per_1M"], 3.0)
        self.assertIsNone(rates["input-only"]["completion_per_1M"])

    def test_parse_litellm_json_pricing_invalid_shapes_return_empty(self):
        self.assertEqual(gp._parse_litellm_json_pricing("not-json", "bad.json"), {})
        self.assertEqual(gp._parse_litellm_json_pricing("[]", "list.json"), {})

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

    def test__count_openai_tokens_with_second_fallback_encoding(self):
        class FakeEnc:
            def encode(self, text):
                return [0, 1]

        fake = types.ModuleType("tiktoken")
        calls = []

        def encoding_for_model(model):
            raise RuntimeError("no model encoding")

        def get_encoding(name):
            calls.append(name)
            if name == "o200k_base":
                raise RuntimeError("no o200k")
            return FakeEnc()

        fake.encoding_for_model = encoding_for_model
        fake.get_encoding = get_encoding
        with mock.patch.dict(sys.modules, {"tiktoken": fake}):
            n = gp._count_openai_tokens("text", "unknown-model")
        self.assertEqual(n, 2)
        self.assertEqual(calls, ["o200k_base", "cl100k_base"])

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

    def test__extract_openai_usage_from_attribute_usage(self):
        resp = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=11, completion_tokens=13))
        with mock.patch.object(gp, "_count_openai_tokens", side_effect=AssertionError("should not be called")):
            usage = gp._extract_openai_usage(resp, "in", "out", "gpt-4o")
        self.assertEqual(usage, {"prompt_tokens": 11, "completion_tokens": 13})

    def test__extract_openai_usage_fallback_after_usage_access_error(self):
        class BadResp:
            @property
            def usage(self):
                raise RuntimeError("bad usage")

        with mock.patch.object(gp, "_count_openai_tokens", side_effect=[2, 4]):
            usage = gp._extract_openai_usage(BadResp(), "abc", "defghij", "gpt-4o")
        self.assertEqual(usage, {"prompt_tokens": 2, "completion_tokens": 4})

    def test__extract_gemini_usage_from_dict_and_attributes(self):
        dict_resp = {"usage_metadata": {"prompt_token_count": 12, "candidates_token_count": 34}}
        dict_expected = {"prompt_tokens": 12, "completion_tokens": 34}
        self.assertEqual(gp._extract_gemini_usage(dict_resp, "in", "out"), dict_expected)

        attr_resp = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=56, candidates_token_count=78))
        attr_expected = {"prompt_tokens": 56, "completion_tokens": 78}
        self.assertEqual(gp._extract_gemini_usage(attr_resp, "in", "out"), attr_expected)

    def test__extract_gemini_usage_fallback_counts(self):
        usage = gp._extract_gemini_usage({}, "abcd", "abcdefghi")
        self.assertEqual(usage, {"prompt_tokens": 1, "completion_tokens": 3})

    def test_estimate_costs_with_exact_model(self):
        fake_rates = {"gpt-4o": {"prompt_per_1M": 2.0, "completion_per_1M": 8.0}}
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates) as parse_pricing:
            usage = {"prompt_tokens": 500_000, "completion_tokens": 250_000}
            est = gp.estimate_costs("gpt-4o", usage)
        parse_pricing.assert_called_once_with(gp.PRICING_URL)
        self.assertAlmostEqual(est["prompt_cost"], 2.0 * 0.5)
        self.assertAlmostEqual(est["completion_cost"], 8.0 * 0.25)
        self.assertAlmostEqual(est["total_cost"], est["prompt_cost"] + est["completion_cost"])

    def test_estimate_costs_accepts_legacy_args_object(self):
        fake_rates = {"legacy-model": {"prompt_per_1M": 1.0, "completion_per_1M": 2.0}}
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates):
            usage = {"prompt_tokens": 100_000, "completion_tokens": 100_000}
            est = gp.estimate_costs(SimpleNamespace(model="legacy-model"), usage)

        self.assertAlmostEqual(est["prompt_cost"], 0.1)
        self.assertAlmostEqual(est["completion_cost"], 0.2)
        self.assertAlmostEqual(est["total_cost"], 0.3)

    def test_estimate_costs_uses_explicit_pricing_source(self):
        fake_rates = {"source-model": {"prompt_per_1M": 10.0, "completion_per_1M": 20.0}}
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates) as parse_pricing:
            usage = {"prompt_tokens": 10_000, "completion_tokens": 20_000}
            est = gp.estimate_costs("source-model", usage, pricing_source="explicit.json")

        parse_pricing.assert_called_once_with("explicit.json")
        self.assertAlmostEqual(est["prompt_cost"], 0.1)
        self.assertAlmostEqual(est["completion_cost"], 0.4)
        self.assertAlmostEqual(est["total_cost"], 0.5)

    def test_estimate_costs_substring_and_unmatched_model(self):
        fake_rates = {
            "foo": {"prompt_per_1M": 1.0, "completion_per_1M": None},
            "bar": {"prompt_per_1M": None, "completion_per_1M": 4.0},
        }
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates):
            # substring match: "foo-bar" should match "foo"
            usage = {"prompt_tokens": 100_000, "completion_tokens": 100_000}
            est = gp.estimate_costs("foo-bar", usage)
            self.assertAlmostEqual(est.get("prompt_cost", 0.0), 0.1)
            # completion rate None -> only prompt cost counted
            self.assertNotIn("completion_cost", est)
            # total is sum (only prompt_cost)
            self.assertAlmostEqual(est["total_cost"], 0.1)

            # No matching key -> zero rates
            est2 = gp.estimate_costs("no-match", usage)
            # no rates -> no costs
            self.assertAlmostEqual(est2["total_cost"], 0.0)

    def test_extract_openai_usage_feeds_estimate_costs(self):
        fake_rates = {"my-model": {"prompt_per_1M": 3.0, "completion_per_1M": 5.0}}
        resp = {"usage": {"prompt_tokens": 200_000, "completion_tokens": 100_000}}
        usage = gp._extract_openai_usage(resp, "ignored prompt", "ignored answer", "my-model")
        with mock.patch.object(gp, "_parse_pricing", return_value=fake_rates):
            est = gp.estimate_costs("my-model", usage)
        self.assertAlmostEqual(est["prompt_cost"], 3.0 * 0.2)
        self.assertAlmostEqual(est["completion_cost"], 5.0 * 0.1)
        self.assertAlmostEqual(est["total_cost"], est["prompt_cost"] + est["completion_cost"])


if __name__ == "__main__":
    unittest.main()
