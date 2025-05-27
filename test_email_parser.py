import unittest
import json
import os
from email_parser import validate_json_output, clean_html, SCHEMA
from bs4 import BeautifulSoup

class TestEmailParser(unittest.TestCase):
    def setUp(self):
        # Load test data if it exists
        self.test_data = None
        if os.path.exists('extracted_data.json'):
            with open('extracted_data.json', 'r') as f:
                self.test_data = json.load(f)

    def test_schema_validation(self):
        """Test that the output follows the required schema"""
        if not self.test_data:
            self.skipTest("No test data available")
        
        for result in self.test_data:
            try:
                validate_json_output(json.dumps(result['data']))
            except Exception as e:
                self.fail(f"Schema validation failed for {result['filename']}: {str(e)}")

    def test_required_fields(self):
        """Test that all required fields are present"""
        if not self.test_data:
            self.skipTest("No test data available")
        
        required_fields = [
            "order_id", "created_date", "order_source_name",
            "order_source_name_merchant", "tracking_number",
            "carrier_reference_raw", "expected_delivery_from",
            "expected_delivery_to"
        ]
        
        for result in self.test_data:
            data = result['data']
            for field in required_fields:
                self.assertIn(field, data, f"Missing field {field} in {result['filename']}")

    def test_date_format(self):
        """Test that dates follow MM/DD/YYYY format"""
        if not self.test_data:
            self.skipTest("No test data available")
        
        import re
        date_pattern = r'^\d{2}/\d{2}/\d{4}$'
        
        for result in self.test_data:
            data = result['data']
            date_fields = ['created_date', 'expected_delivery_from', 'expected_delivery_to']
            
            for field in date_fields:
                if data.get(field):
                    self.assertTrue(
                        re.match(date_pattern, data[field]),
                        f"Invalid date format in {field}: {data[field]}"
                    )

    def test_price_format(self):
        """Test that price fields include currency symbols"""
        if not self.test_data:
            self.skipTest("No test data available")
        
        price_fields = [
            'shipment_value', 'order_total_tax', 'total_shipping_cost',
            'order_total_price'
        ]
        
        for result in self.test_data:
            data = result['data']
            for field in price_fields:
                if data.get(field):
                    self.assertTrue(
                        any(symbol in data[field] for symbol in ['$', '€', '£']),
                        f"Missing currency symbol in {field}: {data[field]}"
                    )

    def test_line_items(self):
        """Test that line items are properly structured"""
        if not self.test_data:
            self.skipTest("No test data available")
        
        for result in self.test_data:
            data = result['data']
            self.assertIn('line_items', data)
            self.assertIsInstance(data['line_items'], list)
            
            for item in data['line_items']:
                required_item_fields = [
                    'product_id', 'product_name', 'quantity',
                    'product_cost', 'total_price'
                ]
                for field in required_item_fields:
                    self.assertIn(field, item, f"Missing field {field} in line item")

    def test_html_cleaning(self):
        """Test that HTML cleaning removes unwanted elements"""
        test_html = """
        <html>
            <head>
                <style>body { color: red; }</style>
                <script>alert('test');</script>
            </head>
            <body>
                <div>Test content</div>
                <img src="test.jpg" alt="test">
            </body>
        </html>
        """
        cleaned = clean_html(test_html)
        self.assertNotIn('style', cleaned.lower())
        self.assertNotIn('script', cleaned.lower())
        self.assertIn('test content', cleaned.lower())

if __name__ == '__main__':
    unittest.main() 