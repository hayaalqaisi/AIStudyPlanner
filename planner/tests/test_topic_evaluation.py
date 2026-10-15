from django.test import SimpleTestCase

from planner.utils.topic_evaluation import (
    evaluate_topic_titles,
    evaluate_topic_titles_fuzzy,
)


class TopicEvaluationTests(SimpleTestCase):
    def test_exact_matching_normalizes_case_and_whitespace(self):
        result = evaluate_topic_titles(
            ["SQL queries", "Database normalization"],
            ["  SQL   QUERIES ", "database normalization"],
        )

        self.assertEqual(result["true_positives"], 2)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["f1"], 1.0)

    def test_exact_matching_penalizes_duplicate_predictions(self):
        result = evaluate_topic_titles(
            ["SQL queries"],
            ["SQL queries", "SQL QUERIES"],
        )

        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1.0)

    def test_fuzzy_matching_accepts_minor_wording_difference(self):
        result = evaluate_topic_titles_fuzzy(
            ["Database normalization"],
            ["Database normalisation"],
        )

        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["f1"], 1.0)
        self.assertEqual(result["threshold"], 0.85)
        self.assertGreaterEqual(
            result["matches"][0]["similarity"],
            0.85,
        )

    def test_exact_and_fuzzy_scores_remain_distinct(self):
        expected = ["Database normalization"]
        predicted = ["Database normalisation"]

        exact = evaluate_topic_titles(expected, predicted)
        fuzzy = evaluate_topic_titles_fuzzy(expected, predicted)

        self.assertEqual(exact["true_positives"], 0)
        self.assertEqual(fuzzy["true_positives"], 1)

    def test_fuzzy_matching_penalizes_duplicate_predictions(self):
        result = evaluate_topic_titles_fuzzy(
            ["Database normalization"],
            [
                "Database normalisation",
                "DATABASE NORMALISATION",
            ],
        )

        self.assertEqual(result["predicted_count"], 2)
        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["precision"], 0.5)

    def test_one_prediction_cannot_match_multiple_references(self):
        result = evaluate_topic_titles_fuzzy(
            ["Database normalization", "Database normalisation"],
            ["Database normalization"],
        )

        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_negatives"], 1)
        self.assertEqual(len(result["matches"]), 1)

    def test_matching_can_reassign_an_earlier_match(self):
        # "ab" can match either reference at this threshold.
        # "ac" can match only "ab", so "ab" must move to "abc".
        result = evaluate_topic_titles_fuzzy(
            ["ab", "abc"],
            ["ab", "ac"],
            threshold=0.5,
        )

        self.assertEqual(result["true_positives"], 2)
        self.assertEqual(result["false_negatives"], 0)

    def test_empty_predictions_produce_zero_scores(self):
        for evaluator in (
            evaluate_topic_titles,
            evaluate_topic_titles_fuzzy,
        ):
            with self.subTest(evaluator=evaluator.__name__):
                result = evaluator(["SQL queries"], [])

                self.assertEqual(result["true_positives"], 0)
                self.assertEqual(result["false_negatives"], 1)
                self.assertEqual(result["precision"], 0.0)
                self.assertEqual(result["recall"], 0.0)
                self.assertEqual(result["f1"], 0.0)

    def test_invalid_thresholds_are_rejected(self):
        for threshold in (0, -0.1, 1.1, True, "0.85", float("nan")):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    evaluate_topic_titles_fuzzy(
                        ["SQL queries"],
                        ["SQL queries"],
                        threshold=threshold,
                    )

    def test_duplicate_references_are_rejected(self):
        for evaluator in (
            evaluate_topic_titles,
            evaluate_topic_titles_fuzzy,
        ):
            with self.subTest(evaluator=evaluator.__name__):
                with self.assertRaises(ValueError):
                    evaluator(
                        ["SQL queries", "SQL QUERIES"],
                        ["SQL queries"],
                    )

    def test_invalid_titles_are_rejected(self):
        for titles in ([""], ["   "], [None], "SQL queries"):
            with self.subTest(titles=titles):
                with self.assertRaises(ValueError):
                    evaluate_topic_titles_fuzzy(
                        ["SQL queries"],
                        titles,
                    )