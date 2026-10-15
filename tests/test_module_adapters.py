import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from module_adapters import normalize_module_payload


class ModuleAdapterTests(unittest.TestCase):
    def test_speech_module_time_is_normalized(self):
        result = normalize_module_payload(
            "speech",
            {
                "transcript": "Hello world.",
                "speaking_time": 18.5,
                "words_per_minute": 120,
                "pause_count": 1,
                "filler_word_count": 0,
            },
        )
        self.assertEqual(result["speaking_time_seconds"], 18.5)
        self.assertEqual(result["transcript"], "Hello world.")

    def test_computer_vision_nested_summary_is_normalized_and_preserved(self):
        result = normalize_module_payload(
            "computer_vision",
            {
                "eye_contact": {
                    "eye_contact_pct": 63.1,
                    "face_detected_pct": 98.5,
                },
                "posture": {
                    "avg_posture_score": 69.3,
                    "visible_pct": 100,
                },
                "gestures": {
                    "fidgeting_pct": 0.3,
                    "face_touch_pct": 2.1,
                },
                "confidence": {"avg_confidence": 72.5},
            },
        )
        self.assertEqual(result["eye_contact"], 63.1)
        self.assertEqual(result["face_visibility"], 98.5)
        self.assertEqual(result["posture_score"], 69.3)
        self.assertEqual(result["movement_score"], 98.65)
        self.assertEqual(
            result["cv_module_report"]["eye_contact"]["eye_contact_pct"],
            63.1,
        )

    def test_nlp_native_score_and_suggestions_are_mapped(self):
        result = normalize_module_payload(
            "nlp",
            {
                "content_score": 81,
                "suggestions": ["Add an example."],
                "details": {"clarity_score": 80},
            },
        )
        self.assertEqual(result["content_score"], 81)
        self.assertEqual(result["content_suggestions"], ["Add an example."])
        self.assertIn("details", result)


if __name__ == "__main__":
    unittest.main()
