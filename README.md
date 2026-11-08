# AI-Powered Invoice Data Extraction

Extracts structured data from invoice images using Google Gemini AI and outputs it as JSON.

## Requirements

- Python 3.9+
- A free Google Gemini API key → [Get one here](https://aistudio.google.com/app/apikey)

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API key

```bash
cp .env.example .env
```

Open `.env` and replace `your_gemini_api_key_here` with your actual key:

```
GEMINI_API_KEY=AIza...
```

## Usage

### Basic — print result to terminal

```bash
python main.py --image invoice.jpg
```

### Save output to a JSON file

```bash
python main.py --image invoice.jpg --output result.json
```

### Supported image formats

`jpg`, `jpeg`, `png`, `webp`, `bmp`, `gif`

## Example Output

```json
{
  "extracted_data": {
    "invoice_number": "RT-2024-1052",
    "invoice_date": "14 October 2024",
    "due_date": "13 November 2024",
    "payment_terms": "30 Days",
    "supplier": {
      "name": "Rivertech Supplies Ltd.",
      "address": "45 Industrial Estate Road, Kathmandu 44600, Nepal",
      "phone": "+977 1 4567890",
      "email": "info@rivertech.com.np"
    },
    "bill_to": {
      "name": "Deutschelink GmbH",
      "department": "Project Department",
      "address": "Sanobharyang, Kathmandu 44700, Nepal"
    },
    "items": [
      {
        "line_number": 1,
        "description": "HDPE Pipe 110mm (6m length)",
        "quantity": 50,
        "unit": "pcs",
        "unit_price": 1250.00,
        "total_amount": 62500.00
      },
      {
        "line_number": 2,
        "description": "HDPE Elbow 90° 110mm",
        "quantity": 20,
        "unit": "pcs",
        "unit_price": 450.00,
        "total_amount": 9000.00
      },
      {
        "line_number": 3,
        "description": "HDPE Coupling 110mm",
        "quantity": 30,
        "unit": "pcs",
        "unit_price": 300.00,
        "total_amount": 9000.00
      },
      {
        "line_number": 4,
        "description": "Welding Service",
        "quantity": 10,
        "unit": "hrs",
        "unit_price": 1500.00,
        "total_amount": 15000.00
      },
      {
        "line_number": 5,
        "description": "Delivery Charge",
        "quantity": 1,
        "unit": "lot",
        "unit_price": 5000.00,
        "total_amount": 5000.00
      }
    ],
    "subtotal": 100500.00,
    "tax": {
      "rate_percent": 13,
      "amount": 13065.00,
      "label": "VAT (13%)"
    },
    "total_amount": 113565.00,
    "currency": "NPR",
    "notes": [
      "Please make payment within 30 days.",
      "For any queries, contact info@rivertech.com.np",
      "This is a computer generated invoice and does not require a signature."
    ],
    "extraction_confidence": "high"
  },
  "validation": {
    "items_sum_matches_subtotal": true,
    "subtotal_plus_tax_matches_total": true,
    "missing_fields": [],
    "warnings": []
  }
}
```

## Project Structure

```
invoice-extractor/
├── main.py            # Main extraction script
├── requirements.txt   # Python dependencies
├── .env.example       # API key template
├── .env               # Your actual API key (not committed to git)
├── invoice.jpg        # Sample invoice image
└── README.md          # This file
```

## How It Works

1. **Load image** — PIL opens and validates the invoice image
2. **Send to Gemini** — The image + a detailed prompt is sent to `gemini-1.5-flash`
3. **Parse JSON** — The model returns structured JSON, which is parsed and cleaned
4. **Validate** — Checks that line item totals match the subtotal, and subtotal + tax matches the grand total
5. **Output** — Prints to terminal and optionally saves to a `.json` file

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| API key missing | Clear error with setup instructions |
| Image not found | Error with file path shown |
| Unsupported format | Error listing supported formats |
| Corrupted image | Error with PIL message |
| Invalid JSON from API | Error with raw response snippet |
| Missing fields | Reported in `validation.missing_fields` |
| Totals mismatch | Reported in `validation.warnings` |
