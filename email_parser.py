import os
import json
import html2text
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from jsonschema import validate, ValidationError
from typing import Dict, List, Optional, Union
import os.path
from deepdiff import DeepDiff
import csv
from datetime import datetime
from collections import defaultdict

# Load environment variables
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY in .env file")

client = genai.Client(api_key=GOOGLE_API_KEY)

# JSON Schema for validation
SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {"type": "string"},
        "created_date": {"type": "string"},
        "order_source_name": {"type": "string"},
        "order_source_name_merchant": {"type": "string"},
        "billing_address": {"type": "string"},
        "tracking_number": {"type": "string"},
        "carrier_reference_raw": {"type": "string"},
        "to_address": {"type": "string"},
        "expected_delivery_from": {"type": "string"},
        "expected_delivery_to": {"type": "string"},
        "shipment_value": {"type": "string"},
        "order_total_tax": {"type": "string"},
        "total_shipping_cost": {"type": "string"},
        "order_total_price": {"type": "string"},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "product_name": {"type": "string"},
                    "product_description": {"type": "string"},
                    "quantity": {"type": "string"},
                    "product_cost": {"type": "string"},
                    "product_discount": {"type": "string"},
                    "product_price": {"type": "string"},
                    "subtotal_cost": {"type": "string"},
                    "tax_amount": {"type": "string"},
                    "misc_cost": {"type": "string"},
                    "discount_amount": {"type": "string"},
                    "total_price": {"type": "string"}
                }
            }
        }
    }
}

def clean_html(html_content: str) -> str:
    """
    Clean HTML content by removing scripts, styles, and converting to plain text
    while preserving important structure.
    """
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Convert HTML to text while preserving some structure
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    
    text = h.handle(str(soup))
    
    return text

def create_prompt(email_content: str) -> str:
    return f"""You are a highly accurate JSON extractor designed to process email content related to credits, refunds, or returns. Your primary objective is to extract relevant information and present it in a well-structured JSON format. Follow the detailed instructions below meticulously.

Step 1: Identify Email Type First, analyze the email content to determine if it pertains to a credit, refund, or return. Look for the following keywords:

"Credit Notification"
"Refund Confirmation"
"Return Processed"
"Money Back"
"Credit Issued"
"Refund Issued"
If the email is identified as a credit/refund/return type, just return basic information (order_id, created_date, order_source_name, order_source_name_merchant), do not extract any other information like price, tax, shipping, etc. 
However, keep structure out json output with empty values. Pass next step.

Step 2: Extract Required Information 
You are required to extract the following fields only, ignoring any price-related fields or monetary amounts, as the focus is on tracking goods/products rather than financial transactions:

Basic Information:

order_id: The unique identifier for the order (e.g., "FO123456789").
created_date: The date when the order was placed in MM/DD/YYYY format (e.g., "12/01/2024").
order_source_name: The name of the website or platform (e.g., "abc.com").
order_source_name_merchant: The specific merchant or seller name or company name or brand name 
billing_address: Complete billing address including street, city, state, and ZIP, formatted as "Name, Street, City, State, Zip". (e.g., "Jane Smith, 123 Main Street, San Francisco, CA 94105")
tracking_number: Shipping tracking number if available.
carrier_reference_raw: The shipping method name or carrier name or shipping provider name (e.g., "Express" from "Express Shipping" ).
to_address: Complete shipping address including street, city, state, and ZIP, formatted as "Name, Street, City, State, Zip". (e.g., "Jane Smith, 123 Main Street, San Francisco, CA 94105")
expected_delivery_from: Earlier date of expected delivery window.
expected_delivery_to: Later date of expected delivery window.
shipment_value: Total cost of item or all items before discount and tax. Formula: shipment_value = order_total_price - total_shipping_cost - order_total_tax. (e.g., "$16" from "$18" - "$1" - "$1)
order_total_tax: Total tax amount for the entire order, including currency symbol.
total_shipping_cost: Total shipping charges, including currency symbol.
order_total_price: Final total including items and tax, including currency symbol.
Line Items Array: For each product in the order, extract the following fields:

product_id: SKU or unique identifier.
product_name: Full product name.
product_description: Size, color, and additional details, formatted as "Size | Color | Additional Details".
quantity: Number of items ordered.
product_cost: Original crossed-out price.
product_discount: Discount amount per unit if available; otherwise, use an empty string.
product_price: Price for this line item before tax/shipping. In case only one line item, it should equal subtotal_cost.
subtotal_cost: Total cost for this line item before tax/shipping. 
tax_amount: Tax applied on line item. In case only one line item, it should equal order_total_tax 
misc_cost: Any additional charges for this item; if none, use an empty string.
discount_amount: Total discount applied to this line item; if none, use an empty string.
total_price: Final total for this line item including tax . This is price after discount but before tax but after shipping, and handling. Formula: total_price = subtotal_cost + tax_amount.
Step 3: JSON Formatting Rules

Ensure that the output contains ONLY valid JSON, with no additional text or explanations.
Use the specified field names exactly as outlined.
If a field is not found, return an empty string "".
For dates, maintain the format MM/DD/YYYY.
For addresses, ensure all components (street, city, state, zip) are included.
Do not use markdown formatting or code blocks.
The response must start with {{ and end with }}.
Price should be in format "$" followed by a number.
Example JSON Structure:
{{
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
        {{
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
        }}
    ]
}}

Email Content to Process:
{email_content}"""

def validate_json_output(json_str: str) -> Dict:
    """
    Validate JSON output against schema and return parsed JSON if valid.
    """
    try:
        # Remove any markdown formatting if present
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1]
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
        json_str = json_str.strip().strip("`")
        
        # Parse JSON
        data = json.loads(json_str)
        validate(instance=data, schema=SCHEMA)
        return data
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format. Response was:\n{json_str}")
        print(f"Error details: {str(e)}")
        raise
    except ValidationError as e:
        print(f"JSON validation failed. Response was:\n{json_str}")
        print(f"Error details: {str(e)}")
        raise

def process_email(file_path: str) -> Dict:
    """
    Process a single email file and return extracted information.
    """
    print(f"\nProcessing {file_path}...")
    
    # Read HTML file
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Clean HTML content
    clean_content = clean_html(html_content)
    print("clean_content=", clean_content)
    
    # Create prompt and get response from Gemini
    prompt = create_prompt(clean_content)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
        config={
            "temperature": 0.0,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
            "stop_sequences": ["{{", "}}"],
            "safety_settings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
        }
    )
    
    # Print response for debugging
    print(f"Raw response from Gemini API:\n{response.text}\n")
    
    # Validate and return JSON
    try:
        result = validate_json_output(response.text)
        
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        
        # Save individual JSON file
        output_filename = os.path.join('output', os.path.basename(file_path).replace('.html', '.json'))
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"Saved results to {output_filename}")
        
        return result
    except Exception as e:
        print(f"Error details for {file_path}: {str(e)}")
        raise

def compare_field_values(expected: Dict, actual: Dict, path: str = "", field_stats: Dict = None) -> Dict:
    """
    Compare field values and track statistics for each field.
    Returns a dictionary of field statistics.
    """
    if field_stats is None:
        field_stats = defaultdict(lambda: {'correct': 0, 'incorrect': 0, 'missing': 0})
    
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in expected:
            current_path = f"{path}.{key}" if path else key
            if key in actual:
                if isinstance(expected[key], (dict, list)):
                    compare_field_values(expected[key], actual[key], current_path, field_stats)
                else:
                    if expected[key] == actual[key]:
                        field_stats[current_path]['correct'] += 1
                    else:
                        field_stats[current_path]['incorrect'] += 1
            else:
                field_stats[current_path]['missing'] += 1
                
        # Check for extra fields in actual
        for key in actual:
            if key not in expected:
                current_path = f"{path}.{key}" if path else key
                field_stats[current_path]['incorrect'] += 1
                
    elif isinstance(expected, list) and isinstance(actual, list):
        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            current_path = f"{path}[{i}]"
            compare_field_values(exp_item, act_item, current_path, field_stats)
            
        # Count missing or extra list items
        if len(expected) != len(actual):
            field_stats[path]['incorrect'] += abs(len(expected) - len(actual))
            
    return field_stats

def calculate_file_accuracy(expected: Dict, actual: Dict) -> float:
    """
    Calculate the general accuracy score for a single file by comparing all fields.
    Returns a percentage accuracy score.
    """
    total_fields = 0
    correct_fields = 0
    
    def compare_values(exp, act):
        nonlocal total_fields, correct_fields
        if isinstance(exp, dict):
            for key in exp:
                total_fields += 1
                if key in act and exp[key] == act[key]:
                    correct_fields += 1
                if key in act and isinstance(exp[key], (dict, list)):
                    compare_values(exp[key], act[key])
        elif isinstance(exp, list):
            for i, item in enumerate(exp):
                if i < len(act):
                    compare_values(item, act[i])
    
    compare_values(expected, actual)
    return (correct_fields / total_fields * 100) if total_fields > 0 else 0

def compare_json_files(expected_dir: str, output_dir: str) -> Dict:
    """
    Compare JSON files in the expected output directory with files in the output directory.
    Returns a dictionary with comparison results and saves to CSV.
    """
    print("\n=== Comparing JSON files ===")
    
    # Initialize results dictionary
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_expected': 0,
        'total_output': 0,
        'files_matching': 0,
        'files_with_differences': 0,
        'missing_files': 0,
        'extra_files': 0
    }
    
    if not os.path.exists(expected_dir):
        print(f"Error: Expected output directory '{expected_dir}' does not exist")
        return results
        
    if not os.path.exists(output_dir):
        print(f"Error: Output directory '{output_dir}' does not exist")
        return results

    expected_files = {f for f in os.listdir(expected_dir) if f.endswith('.json')}
    output_files = {f for f in os.listdir(output_dir) if f.endswith('.json')}
    
    results['total_expected'] = len(expected_files)
    results['total_output'] = len(output_files)
    
    # Check for missing or extra files
    missing_files = expected_files - output_files
    extra_files = output_files - expected_files
    matching_files = expected_files & output_files
    
    results['missing_files'] = len(missing_files)
    results['extra_files'] = len(extra_files)
    
    # Create accuracy report CSV file
    accuracy_csv = 'file_accuracy.csv'
    csv_exists = os.path.exists(accuracy_csv)
    
    with open(accuracy_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow(['Timestamp', 'Filename', 'Accuracy %', 'Status'])
    
    # Compare contents of matching files
    print("\nComparing file contents:")
    total_accuracy = 0
    processed_files = 0
    
    for filename in sorted(matching_files):
        with open(os.path.join(expected_dir, filename), 'r') as f1, \
             open(os.path.join(output_dir, filename), 'r') as f2:
            expected_data = json.load(f1)
            actual_data = json.load(f2)
            
            # Calculate general accuracy for this file
            accuracy = calculate_file_accuracy(expected_data, actual_data)
            total_accuracy += accuracy
            processed_files += 1
            
            # Compare full JSON contents
            diff = DeepDiff(expected_data, actual_data, ignore_order=True)
            status = "Exact Match" if not diff else "Has Differences"
            
            # Save accuracy to CSV
            with open(accuracy_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    results['timestamp'],
                    filename,
                    f"{accuracy:.1f}",
                    status
                ])
            
            if diff:
                results['files_with_differences'] += 1
                print(f"\n❌ {filename} - Accuracy: {accuracy:.1f}% - Has differences:")
                print(diff.pretty())
            else:
                results['files_matching'] += 1
                print(f"✅ {filename} - Accuracy: {accuracy:.1f}% - Exact match")
    
    # Calculate and print average accuracy
    if processed_files > 0:
        average_accuracy = total_accuracy / processed_files
        print(f"\n=== Overall Results ===")
        print(f"Average accuracy across all files: {average_accuracy:.1f}%")
        print(f"Total files processed: {processed_files}")
        print(f"Files with exact matches: {results['files_matching']}")
        print(f"Files with differences: {results['files_with_differences']}")
        print(f"Missing files: {results['missing_files']}")
        print(f"Extra files: {results['extra_files']}")
        print(f"\nDetailed accuracy report saved to: {accuracy_csv}")
    
    return results

def main():
    # Directory containing HTML files
    html_dir = 'HTML'
    
    # Process all emails
    print("Starting email processing...")
    results = []
    
    for filename in sorted(os.listdir(html_dir)):
        if filename.endswith('.html'):
            file_path = os.path.join(html_dir, filename)
            try:
                result = process_email(file_path)
                results.append({
                    'filename': filename,
                    'data': result
                })
                print(f"Successfully processed {filename}")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
    
    print("\nProcessed files:")
    for result in results:
        print(f"- {result['filename']}")
        
    # Compare results with expected output
    compare_json_files('Expected Output', 'output')

if __name__ == "__main__":
    main() 