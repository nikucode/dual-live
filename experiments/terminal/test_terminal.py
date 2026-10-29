import unittest
from array import array

from terminal import RATE, Recipe, parse_pattern, render_pattern, synthesize_kick


class TerminalAudioTests(unittest.TestCase):
    def test_pattern_rejects_invalid_steps(self):
        self.assertEqual(parse_pattern("x . . . x . . . x . . . x . x ."), "x...x...x...x.x.")
        for value in ("x...", "x" * 15 + "?", "x" * 17):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_pattern(value)

    def test_synthesized_kick_has_requested_duration_and_safe_level(self):
        voice = synthesize_kick(Recipe(tail=320))
        self.assertEqual(len(voice), round(0.320 * RATE))
        self.assertGreater(max(abs(sample) for sample in voice), 0.05)
        self.assertLess(max(abs(sample) for sample in voice), 0.38)
        self.assertLess(abs(voice[-1]), 0.001)

    def test_render_respects_silent_pattern(self):
        silent = render_pattern(Recipe(pattern="." * 16), bars=1)
        sounding = render_pattern(Recipe(pattern="x" + "." * 15), bars=1)
        self.assertEqual(len(silent), len(sounding))
        self.assertEqual(set(silent), {0})
        samples = array("h")
        samples.frombytes(sounding)
        self.assertTrue(any(sample != 0 for sample in samples[:4000]))
        self.assertTrue(all(sample == 0 for sample in samples[40000:]))


if __name__ == "__main__":
    unittest.main()
