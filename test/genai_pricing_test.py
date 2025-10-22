import unittest
from pathlib import Path

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

        self.assertAlmostEqual(
            rates["openai/gpt-realtime-2025-08-28"]["prompt_per_1M"], 4.0
        )
        self.assertAlmostEqual(
            rates["openai/gpt-realtime-2025-08-28"]["completion_per_1M"], 16.0
        )

    def test_header_not_included_as_row(self):
        rates = gp._parse_pricing(str(self.md_path))
        self.assertNotIn("model name", rates)


if __name__ == "__main__":
    unittest.main()