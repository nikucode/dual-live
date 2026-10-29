import unittest
from array import array

from dataclasses import replace

from studio import EXAMPLE, RATE, format_session, parse_session, render, synthesize, sync_source


class StudioTests(unittest.TestCase):
    def test_example_parses_and_roundtrips(self):
        session = parse_session(EXAMPLE)
        self.assertEqual(session.bpm, 180)
        self.assertEqual(len(session.tracks), 4)
        self.assertEqual(parse_session(format_session(session)), session)

    def test_errors_report_line_without_losing_valid_session(self):
        with self.assertRaisesRegex(ValueError, "Línea 3"):
            parse_session("bpm 180\nvolume 85\ntrack kick x...\n")
        with self.assertRaisesRegex(ValueError, "no tiene una definición"):
            parse_session("track kick x...x...x...x...\n")

    def test_render_has_music_and_obeys_volume_and_bpm(self):
        session = parse_session(EXAMPLE)
        data = render(session, bars=1)
        self.assertEqual(len(data), 2 * round(RATE * 60 / 180 * 4))
        samples = array("h")
        samples.frombytes(data)
        self.assertGreater(max(abs(sample) for sample in samples), 1000)
        silent = parse_session(EXAMPLE.replace("volume 85", "volume 0"))
        self.assertEqual(set(render(silent, bars=1)), {0})

    def test_each_wave_generates_audio(self):
        session = parse_session(EXAMPLE)
        for track in session.tracks:
            with self.subTest(sound=track.sound.name):
                voice = synthesize(track.sound)
                self.assertGreater(max(abs(value) for value in voice), 0.1)
                self.assertLessEqual(max(abs(value) for value in voice), 0.72)

    def test_sound_controls_remain_linked_to_track_and_source(self):
        session = parse_session(EXAMPLE)
        kick = replace(session.tracks[0].sound, wave="square", hz=57, level=70)
        tracks = (replace(session.tracks[0], sound=kick), *session.tracks[1:])
        changed = replace(session, tracks=tracks)
        source = sync_source(EXAMPLE, changed)
        self.assertIn("# dual.live / sesión inicial", source)
        self.assertIn("sound kick square 57 320 55 70", source)
        self.assertEqual(parse_session(source), changed)
        full = synthesize(replace(kick, level=100))
        quiet = synthesize(replace(kick, level=50))
        self.assertAlmostEqual(max(abs(v) for v in quiet) * 2, max(abs(v) for v in full), places=5)


if __name__ == "__main__":
    unittest.main()
