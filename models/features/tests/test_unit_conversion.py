import unittest

from models.features.unit_conversion import convert_quantity, normalize_unit


class NormalizeUnitTest(unittest.TestCase):
    def test_lowercases_and_strips(self):
        self.assertEqual(normalize_unit("  Cup  "), "cup")

    def test_collapses_punctuation_to_a_single_space(self):
        self.assertEqual(normalize_unit("Fl-Oz"), "fl oz")
        self.assertEqual(normalize_unit("All-Purpose Flour"), "all purpose flour")


class ConvertQuantitySameUnitTest(unittest.TestCase):
    def test_identical_units_pass_through_unchanged(self):
        self.assertEqual(convert_quantity(2.0, "cup", "cup"), 2.0)

    def test_identical_but_differently_cased_units_pass_through(self):
        self.assertEqual(convert_quantity(3.0, "Cup", "cup"), 3.0)

    def test_unrecognized_but_identical_units_still_pass_through(self):
        self.assertEqual(convert_quantity(1.0, "smidge", "smidge"), 1.0)


class ConvertQuantitySameDimensionTest(unittest.TestCase):
    def test_volume_to_volume(self):
        self.assertAlmostEqual(convert_quantity(1.0, "cup", "ml"), 236.588, places=3)

    def test_mass_to_mass(self):
        self.assertEqual(convert_quantity(1.0, "kg", "g"), 1000.0)

    def test_count_to_count_different_spellings(self):
        self.assertEqual(convert_quantity(3.0, "each", "count"), 3.0)


class ConvertQuantityCrossDimensionTest(unittest.TestCase):
    def test_volume_to_mass_with_known_density(self):
        result = convert_quantity(2.0, "cup", "g", ingredient_name="flour")
        self.assertAlmostEqual(result, 2 * 236.588 * 0.507, places=3)

    def test_mass_to_volume_with_known_density(self):
        result = convert_quantity(239.9, "g", "cup", ingredient_name="flour")
        self.assertAlmostEqual(result, 239.9 / 0.507 / 236.588, places=3)

    def test_returns_none_without_an_ingredient_name(self):
        self.assertIsNone(convert_quantity(2.0, "cup", "g"))

    def test_returns_none_for_an_ingredient_with_no_known_density(self):
        self.assertIsNone(convert_quantity(2.0, "cup", "g", ingredient_name="paprika"))

    def test_count_cannot_bridge_to_mass_even_with_a_density(self):
        self.assertIsNone(convert_quantity(2.0, "each", "g", ingredient_name="flour"))


class ConvertQuantityUnrecognizedUnitTest(unittest.TestCase):
    def test_returns_none_for_unrecognized_from_unit(self):
        self.assertIsNone(convert_quantity(1.0, "smidge", "g"))

    def test_returns_none_for_unrecognized_to_unit(self):
        self.assertIsNone(convert_quantity(1.0, "g", "smidge"))


if __name__ == "__main__":
    unittest.main()
