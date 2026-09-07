import unittest

from recommender.ingredient_matching import ingredients_match, normalize_ingredient_name


class NormalizeIngredientNameTest(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(normalize_ingredient_name("Tomato"), "tomato")

    def test_singularizes_simple_plural(self):
        self.assertEqual(normalize_ingredient_name("carrots"), "carrot")

    def test_singularizes_es_plural(self):
        self.assertEqual(normalize_ingredient_name("tomatoes"), "tomato")

    def test_singularizes_ies_plural(self):
        self.assertEqual(normalize_ingredient_name("berries"), "berry")

    def test_preserves_words_ending_in_double_s(self):
        self.assertEqual(normalize_ingredient_name("swiss cheese"), "swiss cheese")

    def test_strips_punctuation(self):
        self.assertEqual(normalize_ingredient_name("salt, to taste"), "salt to taste")

    def test_multi_word_name(self):
        self.assertEqual(normalize_ingredient_name("Roma Tomatoes"), "roma tomato")

    def test_empty_string(self):
        self.assertEqual(normalize_ingredient_name(""), "")


class IngredientsMatchTest(unittest.TestCase):
    def test_exact_match(self):
        self.assertTrue(ingredients_match("Salt", "salt"))

    def test_plural_vs_singular_matches(self):
        self.assertTrue(ingredients_match("tomato", "tomatoes"))
        self.assertTrue(ingredients_match("tomatoes", "tomato"))

    def test_have_is_substring_phrase_of_need(self):
        self.assertTrue(ingredients_match("tomato", "roma tomatoes"))

    def test_need_is_substring_phrase_of_have(self):
        self.assertTrue(ingredients_match("roma tomatoes", "tomato"))

    def test_word_boundary_prevents_false_positive(self):
        # "egg" must not match "eggplant" -- naive substring matching would
        # incorrectly say yes here.
        self.assertFalse(ingredients_match("egg", "eggplant"))
        self.assertFalse(ingredients_match("eggplant", "egg"))

    def test_unrelated_ingredients_do_not_match(self):
        self.assertFalse(ingredients_match("chicken breast", "olive oil"))

    def test_case_insensitive(self):
        self.assertTrue(ingredients_match("GARLIC", "garlic cloves"))

    def test_empty_names_never_match(self):
        self.assertFalse(ingredients_match("", "salt"))
        self.assertFalse(ingredients_match("salt", ""))
        self.assertFalse(ingredients_match("", ""))


if __name__ == "__main__":
    unittest.main()
