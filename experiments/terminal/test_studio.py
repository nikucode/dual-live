import unittest
from array import array

from dataclasses import replace

from studio import EXAMPLE, RATE, format_session, parse_pattern, parse_session, render, synthesize, sync_source


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

    def test_substeps_accents_and_pitch_keep_sixteen_base_steps(self):
        steps = parse_pattern("[xX.x{+7}]" + "." * 15)
        self.assertEqual(len(steps), 16)
        self.assertEqual([hit.offset for hit in steps[0].hits], [0, 0.25, 0.75])
        self.assertEqual([hit.transpose for hit in steps[0].hits], [0, 0, 7])
        self.assertGreater(steps[0].hits[1].velocity, steps[0].hits[0].velocity)
        for bad in ("[x]" + "." * 15, "[xxxxxxxxx]" + "." * 15, "x{+25}" + "." * 15):
            with self.subTest(pattern=bad), self.assertRaises(ValueError):
                parse_pattern(bad)

    def test_substeps_render_at_distinct_times(self):
        source = "bpm 180\nvolume 100\nsound click sine 100 20 0\ntrack click [xx]" + "." * 15 + "\n"
        samples = array("h")
        samples.frombytes(render(parse_session(source), bars=1))
        half_step = round(RATE * 60 / 180 / 8)
        self.assertTrue(any(samples[50:500]))
        self.assertTrue(all(sample == 0 for sample in samples[1200:half_step]))
        self.assertTrue(any(samples[half_step + 50:half_step + 500]))

    def test_pitch_change_and_density_limit(self):
        session = parse_session(EXAMPLE)
        sound = session.tracks[0].sound
        base = synthesize(replace(sound, sweep=0), 0)
        octave = synthesize(replace(sound, sweep=0), 12)
        def crossings(values):
            return sum(a <= 0 < b for a, b in zip(values[:2205], values[1:2206]))
        self.assertGreater(crossings(octave), crossings(base) * 1.7)
        dense = "sound click sine 100 20 0\ntrack click " + "[xxxxxxxx]" * 16 + "\n"
        with self.assertRaisesRegex(ValueError, "Máximo 64 golpes"):
            parse_session(dense)


if __name__ == "__main__":
    unittest.main()
