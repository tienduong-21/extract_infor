# Email Information Extractor

This project extracts structured information from email content and converts it into JSON format. It's particularly useful for processing order confirmations, shipping notifications, and other transactional emails.

## Features

- Extracts order details including:
  - Order ID and dates
  - Billing and shipping addresses
  - Product information
  - Pricing and tax details
  - Shipping information
- Handles different types of emails (orders, refunds, credits)
- Outputs structured JSON data
- Validates extracted data against a schema

## Requirements

- Python 3.7+
- Required packages (install via pip):
  - beautifulsoup4
  - html2text
  - python-dotenv
  - google-generativeai
  - jsonschema
  - deepdiff

## Installation

1. Clone the repository:
```bash
git clone https://github.com/tienduong-21/extract_infor.git
cd extract_infor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file and add your Google API key:
```
GOOGLE_API_KEY=your_api_key_here
```

## Usage

1. Place your HTML email files in the `HTML` directory
2. Run the script:
```bash
python email_parser.py
```
3. Extracted JSON files will be saved in the `output` directory

## Output Format

The script generates JSON files with the following structure:
```json
{
    "order_id": "",
    "created_date": "",
    "order_source_name": "",
    "order_source_name_merchant": "",
    "billing_address": "",
    "tracking_number": "",
    "carrier_reference_raw": "",
    "to_address": "",
    "expected_delivery_from": "",
    "expected_delivery_to": "",
    "shipment_value": "",
    "order_total_tax": "",
    "total_shipping_cost": "",
    "order_total_price": "",
    "line_items": [
        {
            "product_id": "",
            "product_name": "",
            "product_description": "",
            "quantity": "",
            "product_cost": "",
            "product_discount": "",
            "product_price": "",
            "subtotal_cost": "",
            "tax_amount": "",
            "misc_cost": "",
            "discount_amount": "",
            "total_price": ""
        }
    ]
}
```

## License

MIT License 