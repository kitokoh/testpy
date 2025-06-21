import PyPDF2
import re
from typing import Optional, Dict, List, Any
from datetime import datetime

# --- Date Parsing ---
# Consolidated date patterns
# Order matters: more specific patterns should come first.
# Handles YYYY-MM-DD, DD-MM-YYYY, MM-DD-YYYY, YYYY/MM/DD, DD/MM/YYYY, MM/DD/YYYY
# DD.MM.YYYY, MM.DD.YYYY, YYYY.MM.DD
# DD Mon YYYY, Mon DD YYYY, YYYY Mon DD (e.g., 23 Oct 2023, Oct 23 2023)
# DD Month YYYY, Month DD YYYY, YYYY Month DD (e.g., 23 October 2023)
DATE_PATTERNS = [
    # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
    (re.compile(r"\b(\d{4})[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b"), "%Y-%m-%d", ["year", "month", "day"]),
    # DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    (re.compile(r"\b(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])[-/.](\d{4})\b"), "%d-%m-%Y", ["day", "month", "year"]),
    # MM-DD-YYYY, MM/DD/YYYY, MM.DD.YYYY
    (re.compile(r"\b(0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])[-/.](\d{4})\b"), "%m-%d-%Y", ["month", "day", "year"]),
    # DD Mon YYYY (e.g., 23 Oct 2023, 23-Oct-2023)
    (re.compile(r"\b(0?[1-9]|[12]\d|3[01])[- ]?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ]?(\d{4})\b", re.IGNORECASE), "%d-%b-%Y", ["day", "month_abbr", "year"]),
    # Mon DD YYYY (e.g., Oct 23 2023, Oct-23-2023)
    (re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ]?(0?[1-9]|[12]\d|3[01])[- ]?(\d{4})\b", re.IGNORECASE), "%b-%d-%Y", ["month_abbr", "day", "year"]),
    # YYYY Mon DD
    (re.compile(r"\b(\d{4})[- ]?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[- ]?(0?[1-9]|[12]\d|3[01])\b", re.IGNORECASE), "%Y-%b-%d", ["year", "month_abbr", "day"]),
    # DD Month YYYY (e.g., 23 October 2023)
    (re.compile(r"\b(0?[1-9]|[12]\d|3[01]) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})\b", re.IGNORECASE), "%d %B %Y", ["day", "month_full", "year"]),
    # Month DD, YYYY (e.g., October 23, 2023)
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) (0?[1-9]|[12]\d|3[01]),? (\d{4})\b", re.IGNORECASE), "%B %d %Y", ["month_full", "day", "year"]),
]

MONTH_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
    'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'
}

def _normalize_date_match(match_groups: tuple, group_names: list) -> str:
    """Helper to reconstruct a date string in YYYY-MM-DD from matched groups."""
    parts = dict(zip(group_names, match_groups))
    year = parts.get("year")

    month_str = parts.get("month") or parts.get("month_abbr") or parts.get("month_full")
    if month_str:
        month = MONTH_MAP.get(month_str.lower(), month_str) # Convert name to number
    else: # Should not happen if patterns are correct
        return ""

    day = parts.get("day")

    if not all([year, month, day]): return ""

    return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"


def find_dates(text: str) -> List[str]:
    """Finds dates in various common formats and returns them as 'YYYY-MM-DD' strings."""
    found_dates = set()
    for pattern, _, group_names in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                # Reconstruct a parseable string if needed, or use strptime directly if pattern matches format string
                # For simplicity, let's assume direct strptime can work if groups are ordered correctly for the format string.
                # A more robust way: normalize parts then format.

                # Normalized approach:
                date_str_standardized = _normalize_date_match(match.groups(), group_names)
                if date_str_standardized:
                    # Validate if it's a real date (e.g. not Feb 30)
                    datetime.strptime(date_str_standardized, "%Y-%m-%d")
                    found_dates.add(date_str_standardized)
            except ValueError:
                # Not a valid date (e.g., Feb 30) or parsing issue
                continue
    return sorted(list(found_dates))


# --- Amount Parsing ---
# Regex to find amounts, possibly with currency symbols or codes.
# This is a simplified version. Currency context might be needed.
# Looks for numbers with optional decimal part, possibly preceded/followed by common currency symbols/codes.
AMOUNT_PATTERN = re.compile(
    r"(?:[\$€£¥]|USD|EUR|GBP|JPY|XAF|FCFA)?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?:[\$€£¥]|USD|EUR|GBP|JPY|XAF|FCFA|CFA)?"
)
# Simpler version focusing on the number, common for invoices where currency is elsewhere:
AMOUNT_PATTERN_SIMPLE = re.compile(r"\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})\b|\b\d+(?:\.\d{2})\b")
# More specific for "Total", "Montant Total", "Net Amount" type lines
TOTAL_KEYWORDS = ["total", "net amount", "montant total", "payable", "due amount", "balance due"]
AMOUNT_LINE_PATTERN = re.compile(
    r"^(.*(?:{}).*?)(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\b".format("|".join(TOTAL_KEYWORDS)),
    re.IGNORECASE | re.MULTILINE
)


def find_amounts(text: str) -> List[float]:
    """Finds monetary amounts in text. Returns list of floats."""
    amounts = []
    # First, try to find amounts on lines with "total" keywords
    for match in AMOUNT_LINE_PATTERN.finditer(text):
        amount_str = match.group(2).replace(',', '').replace(' ', '')
        try:
            amounts.append(float(amount_str))
        except ValueError:
            continue

    # If no "total" amounts found, or to supplement, use the general pattern
    if not amounts:
        for match in AMOUNT_PATTERN_SIMPLE.finditer(text):
            amount_str = match.group(0).replace(',', '').replace(' ', '')
            try:
                amounts.append(float(amount_str))
            except ValueError:
                continue

    # Remove duplicates and sort (largest first is common for "total")
    return sorted(list(set(amounts)), reverse=True)


# --- Vendor Name Parsing (Very Basic Heuristic) ---
# Looks for lines with "Invoice from", "Bill from", or common company suffixes near the top.
# This is highly unreliable and needs significant improvement or a proper NER model.
VENDOR_INDICATORS = ["invoice from:", "bill from:", "sold by:", "issued by:"] # Add more as needed
COMPANY_SUFFIXES = ["Ltd", "Inc", "LLC", "Corp", "Limited", "Incorporated", "S.A.", "SARL", "GmbH"]

def find_vendor_names(text: str) -> List[str]:
    """Attempts to find potential vendor names. Highly heuristic."""
    potential_vendors = []
    lines = text.splitlines()

    for i, line in enumerate(lines[:20]): # Check first 20 lines
        cleaned_line = line.strip()
        # Check for indicators
        for indicator in VENDOR_INDICATORS:
            if indicator.lower() in cleaned_line.lower():
                vendor_name = cleaned_line.lower().replace(indicator.lower(), "").strip().title()
                if vendor_name and len(vendor_name) > 2: # Basic sanity check
                    potential_vendors.append(vendor_name)

        # Check for company suffixes
        for suffix in COMPANY_SUFFIXES:
            if re.search(r'\b' + re.escape(suffix) + r'\b\.?', cleaned_line, re.IGNORECASE):
                # Try to capture the text before the suffix on the same line
                parts = re.split(r'\b' + re.escape(suffix) + r'\b\.?', cleaned_line, flags=re.IGNORECASE)
                if parts[0].strip():
                    # Heuristic: assume the part before the suffix is the company name
                    company_name_candidate = parts[0].strip()
                    # Avoid just "Tel:", "Fax:", etc. common on letterheads
                    if not any(kw in company_name_candidate.lower() for kw in ["tel:", "fax:", "email:", "vat:", "phone:"]):
                         if company_name_candidate and len(company_name_candidate) > 2:
                            potential_vendors.append(company_name_candidate.title())

    # Simple heuristic: if a line has 2-5 words and is all caps (common for company names)
    # This is very broad and might catch many false positives.
    for line in lines[:15]: # Check top lines
        line = line.strip()
        if re.fullmatch(r"[A-Z][A-Z\s&'-]{3,50}[A-Z.]", line): # All caps, 2-5 words-ish
            if not any(kw.lower() in line.lower() for kw in TOTAL_KEYWORDS + ["date", "invoice", "page", "vat no", "tax id"]):
                 potential_vendors.append(line.title())


    # Filter out duplicates and very short names
    unique_vendors = sorted(list(set(v for v in potential_vendors if len(v) > 3)), key=len)
    return unique_vendors[:5] # Return top 5 candidates by length/occurrence or other heuristic

def parse_invoice_text(text: str) -> Dict[str, Any]:
    """
    Parses raw text extracted from an invoice to find key information.

    Args:
        text: The raw text content of the invoice.

    Returns:
        A dictionary containing identified fields like 'detected_dates',
        'detected_amounts', 'potential_vendors', and the 'raw_text' itself.
    """
    if not text:
        return {
            "detected_dates": [],
            "detected_amounts": [],
            "potential_vendors": [],
            "raw_text": ""
        }

    dates = find_dates(text)
    amounts = find_amounts(text)
    vendors = find_vendor_names(text) # This is the most heuristic part

    # Try to pick a primary candidate (e.g., latest date, largest amount)
    # This is a simple heuristic; more sophisticated logic would be needed for high accuracy.
    primary_date = dates[-1] if dates else None # Assume latest date is often the invoice date
    primary_amount = amounts[0] if amounts else None # Assume largest amount is the total
    primary_vendor = vendors[0] if vendors else None # Simplistic pick

    return {
        "primary_date": primary_date,
        "primary_amount": primary_amount,
        "primary_vendor": primary_vendor,
        "detected_dates": dates,
        "detected_amounts": amounts,
        "potential_vendors": vendors,
        "raw_text": text # Include the full raw text for reference or re-parsing
    }


def extract_text_from_pdf(pdf_file_path: str) -> Optional[str]:
    """
    Extracts all text content from a given PDF file.

    Args:
        pdf_file_path: The local path to the PDF file.

    Returns:
        A string containing all extracted text, or None if extraction fails or the file is not found.
    """
    try:
        with open(pdf_file_path, 'rb') as pdf_file_obj:
            pdf_reader = PyPDF2.PdfReader(pdf_file_obj)
            text_content = []
            for page_num in range(len(pdf_reader.pages)):
                page_obj = pdf_reader.pages[page_num]
                text_content.append(page_obj.extract_text())

            full_text = "\n".join(text_content).strip()
            return full_text if full_text else None # Return None if no text was extracted
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_file_path}")
        # Consider logging this error more formally in a real application
        return None
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_file_path}: {e}")
        # Consider logging this error
        return None

if __name__ == '__main__':
    # This is a placeholder for a test.
    # To run this test, you would need a sample PDF file.
    # For example, create a dummy PDF named 'sample.pdf' in the same directory.

    # Create a dummy PDF file for testing (requires reportlab or similar, or use an existing PDF)
    # For simplicity, this example assumes a PDF 'sample.pdf' exists.
    # You would typically have a test resources folder.

    # Example usage:
    # Create a dummy pdf file named 'test_sample.pdf' in the root directory for this example.
    # (Assuming you have a way to create one or have one handy)
    # For instance, if you have `afd.pdf` in the root from the initial `ls` output:

    # Determine project root to find afd.pdf relative to this utils script
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sample_pdf_path = os.path.join(project_root, "afd.pdf") # Using afd.pdf from project root as a test

    if os.path.exists(sample_pdf_path):
        print(f"Attempting to extract text from: {sample_pdf_path}")
        extracted_text = extract_text_from_pdf(sample_pdf_path)
        if extracted_text:
            print("\n--- Extracted Text (First 500 chars) ---")
            print(extracted_text[:500])
            print("\n--------------------------------------")
            print(f"Total characters extracted: {len(extracted_text)}")
        else:
            print("No text could be extracted or file was empty/corrupted.")
    else:
        print(f"Test PDF file not found at {sample_pdf_path}. Skipping extraction test.")

    # Example with a non-existent file
    print("\nAttempting to extract text from a non-existent file:")
    non_existent_text = extract_text_from_pdf("non_existent_sample.pdf")
    if non_existent_text is None:
        print("Correctly handled non-existent file (returned None).")
    else:
        print(f"Incorrectly handled non-existent file (returned: {non_existent_text[:100]}...)")
