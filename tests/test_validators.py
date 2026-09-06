import unittest

from src.validators import (
    CANONICAL_GOVERNMENT_WARNING,
    LabelExtraction,
    compare_alcohol_content,
    compare_net_contents,
    compare_producer,
    compare_text_values,
    evaluate_government_warning,
)


class ValidatorTests(unittest.TestCase):
    def test_case_and_punctuation_brand_match(self):
        self.assertEqual(compare_text_values("STONE'S THROW", "Stone's Throw"), "MATCH")

    def test_text_with_different_word_boundaries_does_not_false_match(self):
        self.assertEqual(compare_text_values("Sun Ridge", "Sunridge"), "MISMATCH")

    def test_abv_semantic_match(self):
        self.assertEqual(compare_alcohol_content("14.5%", "14.5% ALC. BY VOL."), "MATCH")

    def test_abv_mismatch(self):
        self.assertEqual(compare_alcohol_content("13.5%", "14.5%"), "MISMATCH")

    def test_net_contents_semantic_match(self):
        self.assertEqual(compare_net_contents("0.75 L", "750 mL"), "MATCH")

    def test_net_contents_without_space_match(self):
        self.assertEqual(compare_net_contents("750mL", "0.75 L"), "MATCH")

    def test_centiliter_conversion(self):
        self.assertEqual(compare_net_contents("75 cL", "750 mL"), "MATCH")


    def test_producer_with_location_matches(self):
        self.assertEqual(
            compare_producer(
                "Sunridge Vineyards",
                "Bottled by Sunridge Vineyards, Napa, California",
            ),
            "MATCH",
        )

    def test_different_producer_does_not_match(self):
        self.assertEqual(
            compare_producer(
                "Sunridge Vineyards",
                "Bottled by Mountain Ridge Cellars, Napa, California",
            ),
            "MISMATCH",
        )

    def test_california_not_country(self):
        result = LabelExtraction(country_of_origin="California")
        self.assertIsNone(result.country_of_origin)

    def test_warning_exact_and_format_pass(self):
        result = LabelExtraction(
            government_warning=CANONICAL_GOVERNMENT_WARNING,
            government_warning_present=True,
            warning_header_all_caps=True,
            warning_header_bold=True,
            warning_body_not_bold=True,
            warning_continuous_paragraph=True,
            warning_separate_from_other_info=True,
            warning_readable=True,
        )
        self.assertEqual(evaluate_government_warning(result)["status"], "MATCH")

    def test_warning_wrong_case_fails_exactness(self):
        result = LabelExtraction(
            government_warning=CANONICAL_GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", "Government Warning"),
            government_warning_present=True,
            warning_header_all_caps=False,
            warning_header_bold=True,
            warning_body_not_bold=True,
            warning_continuous_paragraph=True,
            warning_separate_from_other_info=True,
            warning_readable=True,
        )
        self.assertEqual(evaluate_government_warning(result)["status"], "MISMATCH")

    def test_uncertain_visual_format_requires_review(self):
        result = LabelExtraction(
            government_warning=CANONICAL_GOVERNMENT_WARNING,
            government_warning_present=True,
            warning_header_all_caps=True,
            warning_header_bold=None,
            warning_body_not_bold=True,
            warning_continuous_paragraph=True,
            warning_separate_from_other_info=True,
            warning_readable=True,
        )
        self.assertEqual(evaluate_government_warning(result)["status"], "NEEDS REVIEW")


if __name__ == "__main__":
    unittest.main()
