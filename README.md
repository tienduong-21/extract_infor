# Email Parser Documentation

## Overview
This Python script is designed to parse email content related to orders, credits, refunds, or returns. It extracts structured information into a JSON format using Google's Gemini AI model for processing.

## Prerequisites
- Python 3.x
- Google API Key (set in `.env` file)
- Required Python packages (listed in requirements.txt)

## Project Structure
```
.
├── email_parser.py    # Main script
├── .env              # Environment variables
├── HTML/             # Directory containing input HTML files
├── output/           # Directory for JSON output files
└── Expected Output/  # Directory for expected JSON results
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file and add your Google API key:
```
GOOGLE_API_KEY=your_api_key_here
```

## Code Structure

### 1. Configuration and Setup
- Loads environment variables
- Configures Google Gemini API client
- Defines JSON schema for validation

### 2. Core Functions

#### `clean_html(html_content: str) -> str`
- Removes scripts and styles from HTML
- Converts HTML to plain text while preserving structure
- Uses BeautifulSoup and html2text for processing

#### `create_prompt(email_content: str) -> str`
- Creates a detailed prompt for the Gemini AI model
- Includes instructions for:
  - Email type identification
  - Information extraction
  - JSON formatting rules

#### `validate_json_output(json_str: str) -> Dict`
- Validates JSON against predefined schema
- Handles markdown formatting removal
- Returns parsed JSON if valid

#### `process_email(file_path: str) -> Dict`
- Processes a single email file
- Steps:
  1. Reads HTML content
  2. Cleans HTML
  3. Creates AI prompt
  4. Gets response from Gemini
  5. Validates output
  6. Saves result to JSON file

### 3. Comparison and Analysis Functions

#### `compare_field_values(expected: Dict, actual: Dict, path: str = "", field_stats: Dict = None) -> Dict`
- Compares field values between expected and actual results
- Tracks statistics for each field:
  - Correct matches
  - Incorrect matches
  - Missing fields

#### `calculate_file_accuracy(expected: Dict, actual: Dict) -> float`
- Calculates accuracy score for a single file
- Compares all fields recursively
- Returns percentage accuracy

#### `compare_json_files(expected_dir: str, output_dir: str) -> Dict`
- Compares output files with expected results
- Generates accuracy reports
- Creates CSV file with comparison results

## JSON Schema Structure

### Basic Information Fields
- `order_id`: Unique order identifier
- `created_date`: Order date (MM/DD/YYYY format)
- `order_source_name`: Website/platform name
- `order_source_name_merchant`: Merchant/seller name
- `billing_address`: Complete billing address
- `tracking_number`: Shipping tracking number
- `carrier_reference_raw`: Shipping method
- `to_address`: Complete shipping address
- `expected_delivery_from`: Delivery window start
- `expected_delivery_to`: Delivery window end
- `shipment_value`: Total item cost before discount
- `order_total_tax`: Total tax amount
- `total_shipping_cost`: Shipping charges
- `order_total_price`: Final total

### Line Items Array Fields
- `product_id`: SKU/unique identifier
- `product_name`: Full product name
- `product_description`: Size, color, additional details
- `quantity`: Number of items
- `product_cost`: Original price
- `product_discount`: Discount per unit
- `product_price`: Net price after discount
- `subtotal_cost`: Total cost before tax/shipping
- `tax_amount`: Tax applied
- `misc_cost`: Additional charges
- `discount_amount`: Total discount
- `total_price`: Final total with tax

## Usage

1. Place HTML email files in the `HTML` directory
2. Run the script:
```bash
python email_parser.py
```
3. Check results in:
   - `output/` directory for JSON files
   - `file_accuracy.csv` for accuracy report

## Output Format
The script generates:
1. Individual JSON files for each processed email
2. Accuracy report in CSV format
3. Console output with processing details

## Error Handling
- JSON validation errors
- File processing errors
- API response handling
- Missing directory handling

## Best Practices
1. Keep HTML files in designated directory
2. Maintain consistent file naming
3. Regular accuracy checks
4. Monitor API usage
5. Backup important data

## Troubleshooting
- Check API key configuration
- Verify file permissions
- Monitor error logs
- Validate input HTML format 