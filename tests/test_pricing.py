import unittest

from app.pricing import QuoteRequest, calculate_quote


class PricingTests(unittest.TestCase):
    def test_calculate_quote_totals(self):
        req = QuoteRequest(
            width_in=16,
            height_in=20,
            moulding_cost_ft=8,
            mat_cost_sqft=5,
            glazing_cost_sqft=3,
            labor_flat=20,
        )
        result = calculate_quote(req)
        self.assertGreater(result.subtotal, 0)
        self.assertAlmostEqual(result.tax, round(result.subtotal * 0.06, 2))
        self.assertAlmostEqual(result.total, round(result.subtotal + result.tax, 2))

    def test_invalid_dimensions(self):
        with self.assertRaises(ValueError):
            calculate_quote(QuoteRequest(0, 10, 4, 2))

    def test_negative_pricing_inputs(self):
        with self.assertRaises(ValueError):
            calculate_quote(QuoteRequest(8, 10, -1, 2))

    def test_custom_tax_rate(self):
        result = calculate_quote(QuoteRequest(8, 10, 4, 2, tax_rate=0.08))
        self.assertAlmostEqual(result.tax, round(result.subtotal * 0.08, 2))

    def test_mat_border_increases_priced_size(self):
        base = calculate_quote(QuoteRequest(8, 10, 4, 2, mat_border_in=0))
        bordered = calculate_quote(QuoteRequest(8, 10, 4, 2, mat_border_in=3))
        self.assertGreater(bordered.area_sqft, base.area_sqft)
        self.assertGreater(bordered.perimeter_ft, base.perimeter_ft)
        self.assertGreater(bordered.subtotal, base.subtotal)

    def test_extra_line_items_are_included(self):
        result = calculate_quote(
            QuoteRequest(
                8,
                10,
                4,
                2,
                labor_flat=20,
                extra_line_items={"backing": 12.5, "Custom Rush": 8.0},
            )
        )
        self.assertEqual(result.line_items["backing"], 12.5)
        self.assertEqual(result.line_items["Custom Rush"], 8.0)
        self.assertGreater(result.subtotal, 20)


if __name__ == "__main__":
    unittest.main()
