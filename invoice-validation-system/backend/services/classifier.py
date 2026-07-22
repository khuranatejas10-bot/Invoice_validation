import re

# Expanded Keyword mapping
DOCUMENT_KEYWORDS = {
    "Invoice": ["tax invoice", "invoice", "bill", "amount due", "total payable", "gstin"],
    "Purchase Order": ["purchase order", "po number", "po no", "order date", "vendor", "supplier", "purchase"],
    "Bill of Quantity": ["bill of quantity", "bill order quantity", "boq", "abstract qty sheet", "abstract of cost", "measurement abstract", "bulk asset", "abstract qty"],
    "Delivery Challan": ["delivery challan", "challan no", "dispatch", "transport", "vehicle no"],
    "DC Summary": ["delivery challan summary", "challan summary", "dispatch summary", "dc summary"],
    "Work Completion": ["work completion certificate", "wcc", "completion certificate", "certified that"],
    "Approval Email": ["approval email", "approval letter", "sanction", "approved by", "authorized", "subject:", "from:", "to:"],
    "Installation Report": ["installation report", "installation", "installed", "testing commission"],
    "Material Inspection Report": ["material inspection report", "material inspection", "inspection report", "mir", "inspected"],
    "Joint Measurement Report": ["joint measurement report", "measurement report", "jmr", "joint measurement"],
    "Abstract Sheet": ["abstract sheet", "abstract bill", "abstract of payment", "abstract"],
    "Statutory Compliance": ["statutory compliance", "compliance certificate", "pf challan", "esi challan", "provident fund"],
    "Bank Guarantee": ["bank guarantee", "bg", "performance security", "guarantee date"],
    "Proforma Invoice": ["proforma invoice", "proforma", "pi"],
    "SOW Contract": ["sow contract", "scope of work", "agreement", "contract document"],
    "Approval Document": ["approval document", "sanction order", "board approval"]
}

# Strong hints that appear in filenames (often abbreviations)
FILENAME_HINTS = {
    "Invoice": ["inv", "invoice"],
    "Purchase Order": ["po", "purchase_order", "purchaseorder"],
    "Bill of Quantity": ["boq", "qty", "quantity"],
    "Delivery Challan": ["dc", "challan", "delivery_challan"],
    "DC Summary": ["dc_summary", "dc summary"],
    "Work Completion": ["wcc", "completion"],
    "Approval Email": ["email"],
    "Installation Report": ["installation_report", "installation", "ir"],
    "Material Inspection Report": ["material_inspection", "inspection_report", "mir"],
    "Joint Measurement Report": ["joint_measurement", "measurement_report", "jmr"],
    "Abstract Sheet": ["abstract_sheet", "abstract"],
    "Statutory Compliance": ["statutory_compliance", "compliance", "sc"],
    "Bank Guarantee": ["bank_guarantee", "bg"],
    "Proforma Invoice": ["proforma_invoice", "proforma", "pi"],
    "SOW Contract": ["sow_contract", "sow", "contract"],
    "Approval Document": ["approval_document", "approval", "sanction"]
}

def classify_document(text: str, filename: str = "") -> str:
    """Classify the OCR extracted text and filename using a layout-semantic heuristic AI agent."""
    text_lower = text.lower()
    text_normalized = re.sub(r'\s+', ' ', text_lower)
    filename_lower = filename.lower()
    
    # Strip extension for cleaner hint matching
    filename_stem = filename_lower.rsplit('.', 1)[0] if '.' in filename_lower else filename_lower
    # Break filename into parts (words) using non-alphanumeric chars
    filename_parts = set(re.findall(r'[a-z0-9]+', filename_stem))
    
    scores = {}
    for category in DOCUMENT_KEYWORDS.keys():
        scores[category] = 0
        
    # 1. Filename Exact Category Match
    for category in DOCUMENT_KEYWORDS.keys():
        category_slug = category.lower().replace(" ", "_")
        if category_slug in filename_lower or category.lower() in filename_lower:
            scores[category] += 300
            
    # 2. Filename Abbreviation/Hint Match
    for category, hints in FILENAME_HINTS.items():
        for hint in hints:
            if hint in filename_parts:
                scores[category] += 200
            elif hint in filename_stem:
                scores[category] += 100

    # 3. Header Title Check (First 800 characters)
    header_text = text_normalized[:800]
    header_patterns = {
        "Invoice": [r"\btax\s+invoice\b", r"\binvoice\b", r"\bbill\s+to\b"],
        "Purchase Order": [r"\bpurchase\s+order\b", r"\bp\.?\s*o\.?\s+number\b", r"\bp\.?\s*o\.?\s+no\b"],
        "Bill of Quantity": [r"\bbill\s+of\s+quantit(y|ies)\b", r"\bboq\b", r"\babstract\s+of\s+cost\b"],
        "Delivery Challan": [r"\bdelivery\s+challan\b", r"\bchallan\s+no\b"],
        "DC Summary": [r"\bdelivery\s+challan\s+summary\b", r"\bdc\s+summary\b", r"\bchallan\s+summary\b"],
        "Work Completion": [r"\bwork\s+completion\b", r"\bwcc\b", r"\bcompletion\s+certificate\b"],
        "Approval Email": [r"\bfrom:\b.*\bto:\b.*\bsubject:\b", r"\bapproved\b", r"\bsanctioned\b"],
        "Installation Report": [r"\binstallation\s+report\b", r"\binstallation\b"],
        "Material Inspection Report": [r"\bmaterial\s+inspection\b", r"\bmir\b"],
        "Joint Measurement Report": [r"\bjoint\s+measurement\b", r"\bjmr\b"],
        "Abstract Sheet": [r"\babstract\s+sheet\b"],
        "Statutory Compliance": [r"\bstatutory\s+compliance\b", r"\bprovident\s+fund\b", r"\bpf\s+challan\b"],
        "Bank Guarantee": [r"\bbank\s+guarantee\b", r"\bbg\b"],
        "Proforma Invoice": [r"\bproforma\s+invoice\b", r"\bproforma\b"],
        "SOW Contract": [r"\bsow\b", r"\bsow\s+contract\b", r"\bscope\s+of\s+work\b"],
        "Approval Document": [r"\bapproval\s+document\b", r"\bsanction\s+order\b"]
    }
    
    for category, pat_list in header_patterns.items():
        for pat in pat_list:
            if re.search(pat, header_text):
                scores[category] += 400
                break # Only match one header pattern per category

    # 4. Content Keyword Match (Weighted)
    for category, keywords in DOCUMENT_KEYWORDS.items():
        for keyword in keywords:
            occurrences = text_normalized.count(keyword)
            # Higher weight for multi-word keywords
            weight = 30 if len(keyword.split()) > 1 else 15
            scores[category] += occurrences * weight

    # 5. Field Evidence Check (checks for typical form labels)
    field_evidence = {
        "Invoice": [r"invoice\s*no", r"gstin", r"taxable\s*value", r"total\s*amount"],
        "Purchase Order": [r"po\s*no", r"purchase\s*order\s*no", r"order\s*date", r"supplier\s*reference"],
        "Bill of Quantity": [r"boq", r"item\s*description", r"abstract\s*sheet"],
        "Delivery Challan": [r"challan\s*no", r"vehicle\s*no", r"received\s*in\s*good\s*condition"],
        "DC Summary": [r"dc\s*summary", r"challan\s*summary"],
        "Work Completion": [r"completion\s*certificate", r"wcc\s*no", r"satisfactorily\s*completed"],
        "Approval Email": [r"subject\s*:", r"from\s*:", r"to\s*:"],
        "Installation Report": [r"installation\s*date", r"installed\s*by"],
        "Material Inspection Report": [r"inspected\s*by", r"inspection\s*date"],
        "Joint Measurement Report": [r"measurement\s*date", r"joint\s*measurement"],
        "Abstract Sheet": [r"abstract\s*of\s*cost"],
        "Statutory Compliance": [r"pf\s*contribution", r"esi\s*contribution"],
        "Bank Guarantee": [r"bg\s*no", r"bank\s*guarantee\s*amount"],
        "Proforma Invoice": [r"proforma\s*invoice\s*no"],
        "SOW Contract": [r"sow\s*no", r"contract\s*no"],
        "Approval Document": [r"approved\s*by"]
    }
    for category, pat_list in field_evidence.items():
        for pat in pat_list:
            if re.search(pat, text_normalized):
                scores[category] += 100

    best_match = max(scores, key=scores.get)
    if scores[best_match] == 0:
        return "Unknown"
    return best_match

