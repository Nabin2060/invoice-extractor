"""
AI-Powered Invoice Data Extraction
Uses Google Gemini API to extract structured data from invoice images.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# Load environment variables from .env file
load_dotenv()

# gemeni setu
def get_gemini_client() -> genai.GenerativeModel:
    """Initialize and return the Gemini generative model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found.")
        print("  1. Copy .env.example → .env")
        print("  2. Add your API key (free at https://aistudio.google.com/app/apikey)")
        sys.exit(1)

    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-3.8-flash")


#  Image loading

def load_image(image_path: str) -> Image.Image:
    """Load and validate the invoice image."""
    path = Path(image_path)
    if not path.exists():
        print(f"ERROR: Image file not found: {image_path}")
        sys.exit(1)

    supported = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    if path.suffix.lower() not in supported:
        print(f"ERROR: Unsupported image format '{path.suffix}'. Use: {supported}")
        sys.exit(1)

    try:
        img = Image.open(path)
        img.verify()          # check for corruption
        img = Image.open(path)  # reopen after verify
        return img
    except Exception as e:
        print(f"ERROR: Could not open image: {e}")
        sys.exit(1)


#  Extraction prompt

EXTRACTION_PROMPT = """
You are an expert invoice data extraction AI.

Carefully analyze the invoice image and extract the following information.
Return ONLY a valid JSON object — no markdown, no code fences, no extra text.

Required JSON structure:
{
  "invoice_number": "string or null",
  "invoice_date": "string or null",
  "due_date": "string or null",
  "payment_terms": "string or null",
  "supplier": {
    "name": "string or null",
    "address": "string or null",
    "phone": "string or null",
    "email": "string or null"
  },
  "bill_to": {
    "name": "string or null",
    "department": "string or null",
    "address": "string or null"
  },
  "items": [
    {
      "line_number": number or null,
      "description": "string",
      "quantity": number or null,
      "unit": "string or null",
      "unit_price": number or null,
      "total_amount": number or null
    }
  ],
  "subtotal": number or null,
  "tax": {
    "rate_percent": number or null,
    "amount": number or null,
    "label": "string or null"
  },
  "total_amount": number or null,
  "currency": "string or null",
  "notes": ["string"],
  "extraction_confidence": "high | medium | low"
}

Rules:
- Use null for any field you cannot find or read clearly.
- All monetary values must be numbers (not strings).
- notes should be a list of strings (one entry per note line).
- extraction_confidence: "high" if you can read almost everything clearly,
  "medium" if some fields are unclear, "low" if the image is hard to read.
"""


#  AI extraction

def extract_invoice_data(model: genai.GenerativeModel, image: Image.Image) -> dict:
    """Send the image to Gemini and parse the JSON response."""
    try:
        response = model.generate_content([EXTRACTION_PROMPT, image])
        raw_text = response.text.strip()

        # Strip markdown code fences if the model includes them anyway
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            raw_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        return json.loads(raw_text)

    except json.JSONDecodeError as e:
        print(f"ERROR: Gemini returned invalid JSON: {e}")
        print("Raw response:\n", response.text[:500])
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Gemini API call failed: {e}")
        sys.exit(1)


# --------------------------------------------------------------------------- #
#  Validation
# --------------------------------------------------------------------------- #

def validate_invoice(data: dict) -> dict:
    """
    Basic validation checks:
    - Items sum matches subtotal
    - Subtotal + tax matches total
    Returns a validation report dict.
    """
    report = {
        "items_sum_matches_subtotal": None,
        "subtotal_plus_tax_matches_total": None,
        "missing_fields": [],
        "warnings": [],
    }

    # Check for important missing fields
    important = ["invoice_number", "invoice_date", "total_amount"]
    for field in important:
        if data.get(field) is None:
            report["missing_fields"].append(field)

    # Items sum vs subtotal
    items = data.get("items", [])
    if items:
        computed_sum = sum(
            item.get("total_amount") or 0
            for item in items
        )
        subtotal = data.get("subtotal")
        if subtotal is not None:
            diff = abs(computed_sum - subtotal)
            report["items_sum_matches_subtotal"] = diff < 1.0  # allow 1-unit rounding
            if diff >= 1.0:
                report["warnings"].append(
                    f"Items sum ({computed_sum:.2f}) ≠ subtotal ({subtotal:.2f}), diff={diff:.2f}"
                )
        else:
            report["warnings"].append("Subtotal not found — cannot verify items sum.")
    else:
        report["warnings"].append("No line items found.")

    # Subtotal + tax vs total
    subtotal = data.get("subtotal")
    tax_amount = (data.get("tax") or {}).get("amount")
    total = data.get("total_amount")

    if subtotal is not None and tax_amount is not None and total is not None:
        expected_total = subtotal + tax_amount
        diff = abs(expected_total - total)
        report["subtotal_plus_tax_matches_total"] = diff < 1.0
        if diff >= 1.0:
            report["warnings"].append(
                f"Subtotal+Tax ({expected_total:.2f}) ≠ total ({total:.2f}), diff={diff:.2f}"
            )
    else:
        report["warnings"].append(
            "Cannot verify total: subtotal, tax amount, or total is missing."
        )

    return report


# --------------------------------------------------------------------------- #
#  CLI entry point
# --------------------------------------------------------------------------- #

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured data from an invoice image using Gemini AI."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to the invoice image (jpg, png, webp, etc.)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the JSON output (e.g. result.json)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print the JSON output (default: True)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"📄 Loading image: {args.image}")
    image = load_image(args.image)

    print("🤖 Sending to Gemini for extraction...")
    model = get_gemini_client()
    extracted = extract_invoice_data(model, image)

    print("✅ Validating extracted data...")
    validation = validate_invoice(extracted)

    # Build final output
    result = {
        "extracted_data": extracted,
        "validation": validation,
    }

    indent = 2 if args.pretty else None
    json_output = json.dumps(result, indent=indent, ensure_ascii=False)

    # Print to console
    print("\n" + "=" * 60)
    print("EXTRACTION RESULT")
    print("=" * 60)
    print(json_output)

    # Optionally save to file
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_output, encoding="utf-8")
        print(f"\n💾 Result saved to: {args.output}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    data = extracted
    print(f"  Invoice No  : {data.get('invoice_number', 'N/A')}")
    print(f"  Date        : {data.get('invoice_date', 'N/A')}")
    print(f"  Supplier    : {(data.get('supplier') or {}).get('name', 'N/A')}")
    print(f"  Total       : {data.get('currency', '')} {data.get('total_amount', 'N/A')}")
    print(f"  Confidence  : {data.get('extraction_confidence', 'N/A')}")
    print(f"  Validation  : {'✅ PASS' if not validation['warnings'] else '⚠️  ' + str(len(validation['warnings'])) + ' warning(s)'}")
    if validation["warnings"]:
        for w in validation["warnings"]:
            print(f"    - {w}")
    if validation["missing_fields"]:
        print(f"  Missing     : {', '.join(validation['missing_fields'])}")


if __name__ == "__main__":
    main()
