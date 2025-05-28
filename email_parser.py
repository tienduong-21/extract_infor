#!/usr/bin/env python3
"""
Email Parser
-----------
A script to parse email content and extract structured information using Google's Gemini AI model.
"""

import os
import json
import html2text
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai
from jsonschema import validate, ValidationError
from typing import Dict
import csv
from datetime import datetime

# Configuration
# ----------------------------------------------------------------------------
def load_configuration():
    """Load environment variables and configure API client."""
    load_dotenv()
    
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY in .env file")
    
    return genai.Client(api_key=api_key)

# JSON Schema Definition
# ----------------------------------------------------------------------------
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

# HTML Processing
# ----------------------------------------------------------------------------
def clean_html(html_content: str) -> str:
    """Clean HTML content by removing scripts, styles, and converting to plain text."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script in soup(["script", "style"]):
        script.decompose()
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    
    return h.handle(str(soup))

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
    """Validate JSON output against schema and return parsed JSON if valid."""
    try:
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1]
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
        json_str = json_str.strip().strip("`")
        
        data = json.loads(json_str)
        validate(instance=data, schema=SCHEMA)
        return data
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {str(e)}")
        raise
    except ValidationError as e:
        print(f"JSON validation failed: {str(e)}")
        raise

def process_email(file_path: str) -> Dict:
    """Process a single email file and return extracted information."""
    print(f"\nProcessing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    clean_content = clean_html(html_content)
    
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
    
    try:
        result = validate_json_output(response.text)
        output_filename = os.path.join('output', os.path.basename(file_path).replace('.html', '.json'))
        os.makedirs('output', exist_ok=True)
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"Saved results to {output_filename}")
        
        return result
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        raise

def calculate_accuracy(expected: Dict, actual: Dict) -> float:
    """Calculate accuracy score for a single file."""
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

def create_evaluation_prompt(extracted_json: str, expected_json: str) -> str:
    """Create a prompt for LLM to evaluate extraction accuracy."""
    return f"""You are an expert system for evaluating JSON data extraction accuracy. Compare the extracted JSON with the expected JSON and provide a detailed analysis.

Rules:
1. Your response must be valid JSON
2. Always include all required fields in your response
3. Use exact field names as specified
4. Provide specific details for any issues found

Compare these JSONs and analyze their accuracy:

Extracted JSON:
{extracted_json}

Expected JSON:
{expected_json}

Evaluate the following aspects:
1. Field presence and accuracy
2. Format correctness (dates, addresses, prices)
3. Data completeness
4. Edge case handling

Respond with this exact JSON structure:
{{
    "accuracy_score": <number between 0-100>,
    "field_analysis": {{
        "correct_fields": ["field1", "field2"],
        "incorrect_fields": ["field: reason for error"],
        "missing_fields": ["field1", "field2"]
    }},
    "quality_issues": ["specific issue description"],
    "edge_case_handling": ["specific edge case description"],
    "improvement_suggestions": ["specific suggestion"]
}}"""

def evaluate_with_llm(extracted_data: Dict, expected_data: Dict) -> Dict:
    """
    Use LLM to evaluate extraction accuracy and provide detailed analysis.
    Returns a standardized evaluation result.
    """
    try:
        # Convert dictionaries to formatted JSON strings
        extracted_json = json.dumps(extracted_data, indent=2)
        expected_json = json.dumps(expected_data, indent=2)
        
        # Create evaluation prompt
        prompt = create_evaluation_prompt(extracted_json, expected_json)
        
        # Get LLM analysis
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config={
                "temperature": 0.0,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024
            }
        )
        
        # Clean and parse LLM response
        response_text = response.text
        
        # Remove any markdown formatting if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1]
        
        response_text = response_text.strip()
        
        # Parse JSON response
        try:
            evaluation = json.loads(response_text)
            
            # Validate required fields are present
            required_fields = {
                "accuracy_score",
                "field_analysis",
                "quality_issues",
                "edge_case_handling",
                "improvement_suggestions"
            }
            
            if not all(field in evaluation for field in required_fields):
                raise ValueError("Missing required fields in LLM response")
            
            if not isinstance(evaluation["accuracy_score"], (int, float)):
                raise ValueError("Invalid accuracy score format")
            
            return evaluation
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response: {str(e)}")
            print(f"Raw response: {response_text}")
            raise
            
    except Exception as e:
        print(f"Error in LLM evaluation: {str(e)}")
        # Return a standardized error result
        return {
            "accuracy_score": 0,
            "field_analysis": {
                "correct_fields": [],
                "incorrect_fields": [f"Evaluation error: {str(e)}"],
                "missing_fields": []
            },
            "quality_issues": ["Evaluation failed"],
            "edge_case_handling": ["Could not evaluate edge cases"],
            "improvement_suggestions": ["Retry evaluation"]
        }

def compare_results(expected_dir: str, output_dir: str) -> None:
    """Compare output files with expected results using LLM evaluation."""
    if not all(os.path.exists(d) for d in [expected_dir, output_dir]):
        print("Error: Required directories not found")
        return

    expected_files = {f for f in os.listdir(expected_dir) if f.endswith('.json')}
    output_files = {f for f in os.listdir(output_dir) if f.endswith('.json')}
    matching_files = expected_files & output_files

    evaluation_results = []
    
    # Initialize CSV file
    accuracy_csv = 'file_accuracy.csv'
    csv_exists = os.path.exists(accuracy_csv)
    
    with open(accuracy_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow(['Timestamp', 'Filename', 'Accuracy %', 'Status', 'Issues', 'Suggestions'])
    
    for filename in sorted(matching_files):
        print(f"\nEvaluating {filename}")
        try:
            with open(os.path.join(expected_dir, filename), 'r') as f1, \
                 open(os.path.join(output_dir, filename), 'r') as f2:
                expected_data = json.load(f1)
                actual_data = json.load(f2)
                
                # Get LLM evaluation
                evaluation = evaluate_with_llm(actual_data, expected_data)
                evaluation_results.append({
                    'filename': filename,
                    'evaluation': evaluation
                })
                
                # Print evaluation summary
                print(f"Accuracy Score: {evaluation['accuracy_score']}%")
                
                # Prepare issues and suggestions for CSV
                issues = '; '.join(evaluation['field_analysis']['incorrect_fields']) if evaluation['field_analysis']['incorrect_fields'] else ''
                suggestions = '; '.join(evaluation['improvement_suggestions']) if evaluation['improvement_suggestions'] else ''
                
                # Save to CSV
                with open(accuracy_csv, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        filename,
                        f"{evaluation['accuracy_score']:.1f}",
                        "Pass" if evaluation['accuracy_score'] >= 90 else "Fail",
                        issues,
                        suggestions
                    ])
                
                # Print detailed feedback
                if evaluation['field_analysis']['incorrect_fields']:
                    print("\nIssues found:")
                    for field in evaluation['field_analysis']['incorrect_fields']:
                        print(f"- {field}")
                
                if evaluation['quality_issues']:
                    print("\nQuality issues:")
                    for issue in evaluation['quality_issues']:
                        print(f"- {issue}")
                
                if evaluation['improvement_suggestions']:
                    print("\nSuggestions:")
                    for suggestion in evaluation['improvement_suggestions']:
                        print(f"- {suggestion}")
                        
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            # Log error in CSV
            with open(accuracy_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    filename,
                    "0.0",
                    "Error",
                    str(e),
                    "Check file and retry"
                ])
            
            evaluation_results.append({
                'filename': filename,
                'evaluation': {
                    "accuracy_score": 0,
                    "field_analysis": {
                        "correct_fields": [],
                        "incorrect_fields": [f"Processing error: {str(e)}"],
                        "missing_fields": []
                    },
                    "quality_issues": ["File processing failed"],
                    "edge_case_handling": [],
                    "improvement_suggestions": ["Check file format and content"]
                }
            })
    
    # Save detailed evaluation report
    try:
        report_file = 'evaluation_report.json'
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'results': evaluation_results
            }, f, indent=2)
        
        # Calculate overall statistics
        valid_results = [r for r in evaluation_results if r['evaluation']['accuracy_score'] > 0]
        if valid_results:
            total_accuracy = sum(r['evaluation']['accuracy_score'] for r in valid_results)
            avg_accuracy = total_accuracy / len(valid_results)
            
            print(f"\n=== Overall Results ===")
            print(f"Files processed: {len(evaluation_results)}")
            print(f"Successfully evaluated: {len(valid_results)}")
            print(f"Average accuracy: {avg_accuracy:.1f}%")
            print(f"Detailed report saved to: {report_file}")
            print(f"Accuracy log saved to: {accuracy_csv}")
        else:
            print("\nNo valid evaluation results obtained")
            
    except Exception as e:
        print(f"Error saving evaluation report: {str(e)}")

def main():
    """Main execution function."""
    html_dir = 'HTML'
    results = []
    
    print("Starting email processing...")
    
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
    
    compare_results('Expected Output', 'output')

if __name__ == "__main__":
    client = load_configuration()
    main() 