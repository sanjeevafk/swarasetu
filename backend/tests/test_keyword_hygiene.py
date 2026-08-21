"""Automated script hygiene and keyword purity tests."""

import importlib.util
import re
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

for _mod in ("httpx", "app.config", "sqlalchemy", "sqlalchemy.ext.asyncio"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_spec = importlib.util.spec_from_file_location(
    "sarvam_client", REPO_ROOT / "backend/app/services/sarvam_client.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

KEYWORD_CHEST_INDRAWING = _mod.KEYWORD_CHEST_INDRAWING
KEYWORD_CHEST_PAIN = _mod.KEYWORD_CHEST_PAIN
KEYWORD_CONVULSIONS = _mod.KEYWORD_CONVULSIONS
KEYWORD_DIARRHOEA = _mod.KEYWORD_DIARRHOEA
KEYWORD_FEVER = _mod.KEYWORD_FEVER
KEYWORD_NECK_STIFFNESS = _mod.KEYWORD_NECK_STIFFNESS
KEYWORD_RESPIRATORY_COUGH = _mod.KEYWORD_RESPIRATORY_COUGH
KEYWORD_RESPIRATORY_DISTRESS = _mod.KEYWORD_RESPIRATORY_DISTRESS
KEYWORD_UNCONSCIOUS = _mod.KEYWORD_UNCONSCIOUS
KEYWORD_VOMITING_BLOOD = _mod.KEYWORD_VOMITING_BLOOD
SarvamClient = _mod.SarvamClient

ALL_KEYWORD_LISTS = [
    ("CONVULSIONS", KEYWORD_CONVULSIONS),
    ("UNCONSCIOUS", KEYWORD_UNCONSCIOUS),
    ("CHEST_PAIN", KEYWORD_CHEST_PAIN),
    ("VOMITING_BLOOD", KEYWORD_VOMITING_BLOOD),
    ("FEVER", KEYWORD_FEVER),
    ("NECK_STIFFNESS", KEYWORD_NECK_STIFFNESS),
    ("RESPIRATORY_COUGH", KEYWORD_RESPIRATORY_COUGH),
    ("RESPIRATORY_DISTRESS", KEYWORD_RESPIRATORY_DISTRESS),
    ("CHEST_INDRAWING", KEYWORD_CHEST_INDRAWING),
    ("DIARRHOEA", KEYWORD_DIARRHOEA),
]

SCRIPTS = {
    "deva": r"[\u0900-\u097F]",
    "taml": r"[\u0B80-\u0BFF]",
    "beng": r"[\u0980-\u09FF]",
}


class TestKeywordHygiene(unittest.TestCase):
    def test_single_script_purity_across_all_keywords(self):
        """Ensure no keyword contains mixed Indic scripts (e.g. Devanagari + Tamil)."""
        defects = []
        for name, klist in ALL_KEYWORD_LISTS:
            for kw in klist:
                if len(kw.strip()) < 2:
                    continue
                hits = [sname for sname, pat in SCRIPTS.items() if re.search(pat, kw)]
                if len(hits) > 1:
                    defects.append(f"{name}: {hits} -> {kw!r}")
        self.assertEqual(defects, [], f"Found mixed-script defects: {defects}")

    def test_no_empty_keywords(self):
        for name, klist in ALL_KEYWORD_LISTS:
            for kw in klist:
                self.assertTrue(kw.strip(), f"Empty keyword in {name}")

    def test_tamil_fever_detected(self):
        """Regression test for DEF-01: Tamil fever keyword extraction."""
        client = SarvamClient(api_key=None)
        payload = client.extract_symptoms_rule_fallback(
            "என் குழந்தைக்கு இரண்டு நாட்களாக காய்ச்சல் உள்ளது", "ta"
        )
        self.assertTrue(payload.has_fever, "Tamil fever keyword 'காய்ச்சல்' failed to extract")


if __name__ == "__main__":
    unittest.main()
