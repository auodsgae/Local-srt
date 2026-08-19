from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from local_srt.captions import SimpleAlignmentItem, build_natural_captions


def transcript_to_subtitles_for_tests(
    items: list[tuple[str, float, float]],
    offset: float = 0.0,
    transcript_text: str | None = None,
    **caption_options,
):
    align = [SimpleAlignmentItem(text=t, start_time=s, end_time=e) for t, s, e in items]
    return build_natural_captions(
        align,
        transcript_text=transcript_text,
        offset_seconds=offset,
        script="preserve",
        **caption_options,
    )


class CaptionTests(unittest.TestCase):
    def test_english_words_keep_spaces(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("This", 0.00, 0.10),
                ("is", 0.10, 0.20),
                ("a", 0.20, 0.30),
                ("test", 0.30, 0.40),
                (".", 0.40, 0.45),
            ]
        )
        self.assertEqual(subtitles[0].text, "This is a test")

    def test_english_punctuation_and_contractions_are_detokenized(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("I", 0.00, 0.10),
                ("do", 0.10, 0.20),
                ("n't", 0.20, 0.30),
                ("know", 0.30, 0.40),
                (",", 0.40, 0.45),
                ("maybe", 0.45, 0.55),
                (".", 0.55, 0.60),
            ]
        )
        self.assertEqual(subtitles[0].text, "I don't know maybe")

    def test_word_start_markers_become_spaces(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u2581This", 0.00, 0.10),
                ("\u2581works", 0.10, 0.20),
                (".", 0.20, 0.30),
            ]
        )
        self.assertEqual(subtitles[0].text, "This works")

    def test_mixed_chinese_english_spacing(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u6211", 0.00, 0.10),
                ("\u7528", 0.10, 0.20),
                ("local", 0.20, 0.30),
                ("SRT", 0.30, 0.40),
                ("\u5de5", 0.40, 0.50),
                ("\u5177", 0.50, 0.60),
                ("export", 0.60, 0.70),
                ("file", 0.70, 0.80),
            ]
        )
        self.assertEqual(subtitles[0].text, "\u6211\u7528 local SRT \u5de5\u5177 export file")

    def test_separate_english_alignment_words_keep_their_space(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("some", 0.00, 0.10),
                ("thing", 0.10, 0.20),
                ("else", 0.20, 0.30),
                (".", 0.30, 0.40),
            ]
        )
        self.assertEqual(subtitles[0].text, "some thing else")

    def test_transcript_restores_english_punctuation_and_spaces(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("This", 0.00, 0.10),
                ("is", 0.10, 0.20),
                ("correctly", 0.20, 0.35),
                ("spaced", 0.35, 0.50),
                ("Next", 0.70, 0.80),
                ("sentence", 0.80, 1.00),
            ],
            transcript_text="This is correctly spaced. Next sentence!",
        )
        self.assertEqual(
            [item.text for item in subtitles],
            ["This is correctly spaced", "Next sentence"],
        )
        self.assertAlmostEqual(subtitles[0].end, 0.50)
        self.assertAlmostEqual(subtitles[1].start, 0.70)

    def test_transcript_restores_punctuation_inside_an_english_word(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("stateoftheart", 0.00, 0.30),
                ("isnt", 0.30, 0.50),
                ("bad", 0.50, 0.70),
            ],
            transcript_text="state-of-the-art isn\u2019t bad.",
        )
        self.assertEqual([item.text for item in subtitles], ["state-of-the-art isn\u2019t bad"])

    def test_internal_period_does_not_end_an_english_sentence(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("Contact", 0.00, 0.20),
                ("testexamplecom", 0.20, 0.50),
                ("today", 0.50, 0.70),
            ],
            transcript_text="Contact test@example.com today.",
        )
        self.assertEqual(
            [item.text for item in subtitles],
            ["Contact test examplecom today"],
        )

    def test_transcript_restores_chinese_sentence_boundaries(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u4f60", 0.00, 0.10),
                ("\u597d", 0.10, 0.25),
                ("\u4e0b", 0.50, 0.60),
                ("\u4e00", 0.60, 0.70),
                ("\u53e5", 0.70, 0.85),
            ],
            transcript_text="\u4f60\u597d\u3002\u4e0b\u4e00\u53e5\uff01",
        )
        self.assertEqual(
            [item.text for item in subtitles],
            ["\u4f60\u597d", "\u4e0b\u4e00\u53e5"],
        )
        self.assertAlmostEqual(subtitles[0].end, 0.25)
        self.assertAlmostEqual(subtitles[1].start, 0.50)

    def test_word_start_marker_does_not_put_space_before_punctuation(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("Hello", 0.00, 0.20),
                ("\u2581,", 0.20, 0.20),
                ("\u2581world", 0.30, 0.50),
                ("!", 0.50, 0.50),
            ]
        )
        self.assertEqual(subtitles[0].text, "Hello world")

    def test_punctuation_does_not_count_as_an_english_word(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("one", 0.00, 0.10),
                (",", 0.10, 0.10),
                ("two", 0.20, 0.30),
                (",", 0.30, 0.30),
                ("three", 0.40, 0.50),
                (".", 0.50, 0.50),
            ],
            max_words=3,
        )
        self.assertEqual([item.text for item in subtitles], ["one two three"])

    def test_mandarin_boundary_avoids_common_word_split(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u6211", 0.00, 0.10),
                ("\u5011", 0.10, 0.20),
                ("\u53bb", 0.20, 0.30),
            ],
            max_zh_chars=1,
        )
        self.assertEqual([item.text for item in subtitles], ["\u6211\u5011", "\u53bb"])

    def test_sentence_punctuation_is_removed_but_still_splits(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u4f60", 0.10, 0.20),
                ("\u597d", 0.20, 0.35),
                ("\u3002", 0.35, 0.36),
                ("Next", 2.00, 2.50),
            ]
        )
        self.assertEqual(len(subtitles), 2)
        self.assertEqual(subtitles[0].text, "\u4f60\u597d")
        self.assertAlmostEqual(subtitles[0].end, 0.36)
        self.assertAlmostEqual(subtitles[1].start, 2.00)

    def test_caption_never_starts_with_punctuation(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\uff0c", 0.00, 0.00),
                ("\u4f46", 0.00, 0.10),
                ("\u662f", 0.10, 0.20),
                ("\u9019", 0.20, 0.30),
                ("\u662f", 0.30, 0.40),
                ("\u4e0b", 0.40, 0.50),
                ("\u4e00", 0.50, 0.60),
                ("\u53e5", 0.60, 0.70),
                ("\u3002", 0.70, 0.70),
            ]
        )
        self.assertEqual([item.text for item in subtitles], ["\u4f46\u662f\u9019\u662f\u4e0b\u4e00\u53e5"])
        self.assertTrue(all(item.text[0].isalnum() for item in subtitles))

    def test_kingshot_opening_rebalances_at_comma_without_changing_time_blocks(self):
        characters = (
            "\u73a9\u624b\u904a\u6700\u6015\u5ee3\u544a\u5f48\u51fa\u4f86"
            "\u4f46\u9019\u6b3e\u904a\u6232\u8ddf\u6211\u8aaa\u4e0d\u7528\u6015"
        )
        starts = [
            0.00, 0.16, 0.40, 0.56, 0.64, 0.80, 1.04, 1.12, 1.28, 1.44,
            1.76, 1.84, 1.92, 2.08, 2.08, 2.24, 2.24, 2.32, 2.40, 2.56,
            2.64,
        ]
        ends = [
            0.16, 0.40, 0.56, 0.64, 0.80, 1.04, 1.12, 1.28, 1.44, 1.60,
            1.84, 1.92, 2.08, 2.08, 2.24, 2.24, 2.32, 2.40, 2.56, 2.64,
            2.80,
        ]
        items = list(zip(characters, starts, ends))
        subtitles = transcript_to_subtitles_for_tests(
            items,
            transcript_text=(
                "\u73a9\u624b\u904a\u6700\u6015\u5ee3\u544a\u5f48\u51fa\u4f86\uff0c"
                "\u4f46\u9019\u6b3e\u904a\u6232\u8ddf\u6211\u8aaa\u4e0d\u7528\u6015\u3002"
            ),
        )
        self.assertEqual(
            [(item.start, item.end, item.text) for item in subtitles],
            [
                (0.00, 2.08, "\u73a9\u624b\u904a\u6700\u6015\u5ee3\u544a\u5f48\u51fa\u4f86"),
                (2.08, 2.80, "\u4f46\u9019\u6b3e\u904a\u6232\u8ddf\u6211\u8aaa\u4e0d\u7528\u6015"),
            ],
        )

    def test_mandarin_splits_near_fifteen_characters_without_breaking_common_words(self):
        phrase = "\u6211\u5011\u4eca\u5929\u4e00\u8d77\u53bb\u53f0\u5317\u8eca\u7ad9\u9644\u8fd1\u5403\u665a\u9910"
        subtitles = transcript_to_subtitles_for_tests(
            [(char, index * 0.1, index * 0.1 + 0.08) for index, char in enumerate(phrase)]
        )
        texts = [item.text for item in subtitles]
        self.assertEqual("".join(texts), phrase)
        self.assertTrue(all(len(text) <= 15 for text in texts))
        self.assertNotIn("\u6211", texts)
        self.assertNotIn("\u5011", texts)
        self.assertNotIn("\u4eca", texts)
        self.assertNotIn("\u5929", texts)

    def test_pause_can_split_mandarin_without_punctuation(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u6211", 0.00, 0.10),
                ("\u5011", 0.10, 0.20),
                ("\u5148", 0.20, 0.30),
                ("\u4f11", 0.30, 0.40),
                ("\u606f", 0.40, 0.50),
                ("\u4e0b", 1.10, 1.20),
                ("\u4e00", 1.20, 1.30),
                ("\u6bb5", 1.30, 1.40),
            ]
        )
        self.assertEqual([item.text for item in subtitles], ["\u6211\u5011\u5148\u4f11\u606f", "\u4e0b\u4e00\u6bb5"])

    def test_one_second_silence_always_splits_and_ends_at_last_word(self):
        subtitles = transcript_to_subtitles_for_tests(
            [
                ("\u6211", 0.00, 0.10),
                ("\u5011", 0.10, 0.20),
                ("\u53bb", 1.20, 1.30),
                ("\u53f0", 1.30, 1.40),
                ("\u5317", 1.40, 1.50),
            ]
        )
        self.assertEqual([item.text for item in subtitles], ["\u6211\u5011", "\u53bb\u53f0\u5317"])
        self.assertAlmostEqual(subtitles[0].end, 0.20)
        self.assertAlmostEqual(subtitles[1].start, 1.20)

    def test_offsets_are_independent_per_chunk(self):
        subtitles = transcript_to_subtitles_for_tests([("Hello", 0.5, 1.0)], offset=270.0)
        self.assertAlmostEqual(subtitles[0].start, 270.5)
        self.assertAlmostEqual(subtitles[0].end, 271.0)


if __name__ == "__main__":
    unittest.main()
