import csv
import os
import re
from typing import List, Dict, Any, Tuple

CSV_PATH = os.getenv(
    "RULE_CATALOGUE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "02_Corrected_Validation_Rule_Catalogue.csv")
)
if not os.path.exists(CSV_PATH):
    # Fallback to parent docs directory if running locally in workspace
    CSV_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "02_Corrected_Validation_Rule_Catalogue.csv"
    )

def get_rule_subcategories() -> List[str]:
    """Helper to extract unique invoice subcategories from CSV."""
    if not os.path.exists(CSV_PATH):
        return []
    subcats = set()
    try:
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sub = row.get("invoice_subcategory")
                if sub:
                    subcats.add(sub.strip())
    except Exception as e:
        print(f"Error reading subcategories: {e}")
    return sorted(list(subcats))

def tokenize(text: str) -> set:
    """Helper to tokenize and lowercase text."""
    return set(re.findall(r'[a-z0-9]+', text.lower()))

def calculate_jaccard_similarity(set1: set, set2: set) -> float:
    """Jaccard similarity coefficient between two token sets."""
    if not set1 or not set2:
        return 0.0
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union)

def classify_subcategory_ai(text: str) -> str:
    """
    AI-based classifier: Matches document text to CSV subcategories using Jaccard token overlap.
    If similarity is too low (< 0.05), it dynamically defines a new category using key terms.
    """
    subcats = get_rule_subcategories()
    if not subcats:
        return "Supply / Installation / Testing & Commissioning"
    
    text_tokens = tokenize(text)
    best_subcat = None
    max_sim = 0.0
    
    for subcat in subcats:
        subcat_tokens = tokenize(subcat)
        sim = calculate_jaccard_similarity(text_tokens, subcat_tokens)
        if sim > max_sim:
            max_sim = sim
            best_subcat = subcat
            
    # If the match is solid, return it
    if max_sim >= 0.05 and best_subcat:
        return best_subcat
        
    # Dynamically extract a new category based on the most frequent noun-like words
    words = re.findall(r'\b[a-zA-Z]{5,15}\b', text.lower())
    ignored_words = {"invoice", "purchase", "order", "delivery", "challan", "document", "service", "project"}
    candidate_words = [w for w in words if w not in ignored_words]
    
    from collections import Counter
    counts = Counter(candidate_words)
    top_words = [w.capitalize() for w, _ in counts.most_common(2)]
    
    if top_words:
        new_cat = "Dynamic Services - " + " & ".join(top_words)
    else:
        new_cat = "Dynamic Custom Services"
        
    return new_cat

# --------------------------------------------------------------------------
# AI ENTITY EXTRACTOR (PROXIMITY-BASED LABELED PARSING)
# --------------------------------------------------------------------------

def extract_entities_ai(document_type: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    AI Entity Extractor:
    Uses a Layout-Semantic Scoring Engine to extract values from OCR blocks.
    It does not rely on strict keyword/proximity matching, but on semantic similarity 
    between surrounding context and field definitions.
    """
    extracted = {}
    if not blocks:
        return extracted
        
    # Sort blocks top-to-bottom, left-to-right (grouped by page first)
    sorted_blocks = sorted(blocks, key=lambda b: (b.get("page", 1), b.get("bbox", [0,0,0,0])[1], b.get("bbox", [0,0,0,0])[0]))
    
    # 1. Pre-process and collect all texts and coordinates
    full_text = "\n".join([b["text"] for b in sorted_blocks])
    
    # Define targets and their semantic context words
    field_contexts = {
        "invoice_no": {"invoice", "inv", "bill", "invoice_no", "inv_no", "bill_no", "no", "number", "invoice#", "invoice_number"},
        "po_number": {"po", "purchase", "order", "po_no", "po_number", "order_no", "p.o."},
        "invoice_date": {"date", "dated", "invoice_date", "inv_date", "date_of_issue", "billing_date", "issue"},
        "vendor_name": {"vendor", "supplier", "m/s", "issued_to", "seller", "from", "company", "name"},
        "gstin": {"gstin", "gst", "gst_no", "tin", "gstin/uin", "tax_id"},
        "taxable_value": {"taxable", "taxable_value", "taxable_amount", "subtotal", "sub_total", "assessable", "value", "excluding", "excl"},
        "total_amount": {"total", "grand_total", "net", "payable", "total_amount", "gross", "amount", "inclusive", "incl"},
        "cgst": {"cgst", "central", "central_gst"},
        "sgst": {"sgst", "sgst", "state", "state_gst"},
        "igst": {"igst", "igst", "integrated", "integrated_gst"},
        "quantity": {"qty", "quantity", "volume", "billed_qty"},
        "unit_rate": {"rate", "price", "unit_price", "unit_rate"},
        "certified_amount": {"certified", "approved", "certified_amount"},
        "approval_limit": {"limit", "approval_limit", "authority"},
        # New generic text fields to map words dynamically
        "item": {"item", "description", "details", "line item", "material", "goods"},
        "description": {"description", "item description", "work description", "scope", "specification"},
        "approved_by": {"approved by", "authorizer", "signatory", "approved", "manager", "by"},
        "dc_no": {"dc no", "challan no", "dc number", "challan number", "delivery challan"},
        "boq_no": {"boq no", "boq number", "bill of quantity no", "boq ref"},
        "wcc_no": {"wcc no", "wcc number", "work completion certificate no", "wcc ref"},
        "dc_summary_no": {"dc summary no", "dc summary number", "challan summary no", "summary ref"}
    }

    # Helper: tokenize text block
    def get_tokens(text: str) -> set:
        return set(re.findall(r'[a-z0-9]+', text.lower()))

    # Helper: calculate fuzzy similarity score between block tokens and context words
    def get_fuzzy_overlap_score(tokens: set, context_words: set) -> float:
        score = 0.0
        for tok in tokens:
            # Exact match
            if tok in context_words:
                score += 1.5
                continue
            # Fuzzy prefix/suffix match
            for cw in context_words:
                if tok.startswith(cw) or cw.startswith(tok):
                    score += 1.0
                    break
                # SequenceMatcher similarity
                import difflib
                if abs(len(tok) - len(cw)) <= 3:
                    ratio = difflib.SequenceMatcher(None, tok, cw).ratio()
                    if ratio > 0.8:
                        score += ratio * 1.2
                        break
        return score

    # Helper: calculate context score for a block index
    def get_context_score(block_idx: int, field_name: str) -> float:
        context_words = field_contexts[field_name]
        score = 0.0
        target_block = sorted_blocks[block_idx]
        tb_bbox = target_block.get("bbox", [0,0,0,0])
        tb_page = target_block.get("page", 1)
        
        # Check text in target block itself
        target_tokens = get_tokens(target_block["text"])
        score += get_fuzzy_overlap_score(target_tokens, context_words) * 1.5
        
        # Check text in nearby blocks in the list (index distance)
        for offset in [-2, -1, 1, 2]:
            idx = block_idx + offset
            if 0 <= idx < len(sorted_blocks):
                # Ensure context doesn't bleed across pages
                if sorted_blocks[idx].get("page", 1) == tb_page:
                    tokens = get_tokens(sorted_blocks[idx]["text"])
                    dist_factor = 1.0 / (abs(offset) + 0.5)
                    score += get_fuzzy_overlap_score(tokens, context_words) * dist_factor
                    
        # Check 2D physical spatial distance (same line or nearby column)
        for idx, block in enumerate(sorted_blocks):
            if idx == block_idx:
                continue
            if block.get("page", 1) != tb_page:
                continue
            b_bbox = block.get("bbox", [0,0,0,0])
            y_diff = abs(b_bbox[1] - tb_bbox[1])
            x_diff = abs(b_bbox[0] - tb_bbox[0])
            if y_diff < 35 and x_diff < 350:
                tokens = get_tokens(block["text"])
                score += get_fuzzy_overlap_score(tokens, context_words) * 1.0
                
        return score

    # 2. Extract specific datatypes
    gstin_candidates = []
    date_candidates = []
    amount_candidates = []
    code_candidates = []  
    vendor_candidates = [] 
    
    gstin_regex = re.compile(r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}')
    date_regex = re.compile(
        r'\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b|'
        r'\b\d{1,2}[\s\-./]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*[\s\-./]+\d{2,4}\b|'
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*[\s\-./]+\d{1,2}[\s\-./]*,?[\s\-./]*\d{2,4}\b', 
        re.IGNORECASE
    )
    amount_regex = re.compile(r'\b\d+(?:,\d{3})*(?:\.\d{2})?\b')

    for idx, block in enumerate(sorted_blocks):
        text = block["text"].strip()
        if not text:
            continue
            
        # Check GSTIN
        clean_text_for_gst = re.sub(r'[\s\-]+', '', text.upper())
        gstin_match = gstin_regex.search(clean_text_for_gst)
        if gstin_match:
            gstin_candidates.append((gstin_match.group(0), idx, 1.0))
            
        # Check Dates
        date_matches = date_regex.findall(text)
        for dm in date_matches:
            date_candidates.append((dm, idx, 1.0))
            
        # Check Alphanumeric code (Invoice No, PO Number)
        tokens = text.split()
        for tok in tokens:
            tok_clean = tok.strip(":,.;()#\"'<>-")
            if len(tok_clean) >= 4:
                # Exclude GSTIN from being classified as PO/Invoice number
                if gstin_regex.search(tok_clean.upper()):
                    continue
                # Exclude email addresses, bracketed terms, and domains
                if "@" in tok_clean or tok_clean.startswith("<") or tok_clean.endswith(">") or ("." in tok_clean and len(tok_clean) > 8):
                    continue
                # Exclude 4-digit years (e.g., 2026)
                if len(tok_clean) == 4 and tok_clean.isdigit() and (tok_clean.startswith("19") or tok_clean.startswith("20")):
                    continue
                has_digit = any(c.isdigit() for c in tok_clean)
                has_letter = any(c.isalpha() for c in tok_clean)
                if (has_digit and has_letter) or tok_clean.startswith(("INV", "PO", "WO", "SO", "BILL")):
                    code_candidates.append((tok_clean, idx, 1.2 if tok_clean.startswith(("INV", "PO", "WO")) else 0.8))
                elif has_digit and tok_clean.isdigit() and 4 <= len(tok_clean) <= 10:
                    code_candidates.append((tok_clean, idx, 0.5))

        # Check Amounts
        amount_matches = amount_regex.findall(text)
        for am in amount_matches:
            val_fl = _clean_float(am)
            if val_fl is not None and val_fl > 0.0:
                if not date_regex.search(text) and len(am.replace(",", "").split('.')[0]) < 12:
                    prior = 1.0
                    if "." in am:
                        prior += 0.2
                    if "," in am:
                        prior += 0.2
                    amount_candidates.append((val_fl, idx, prior))

        # Check Vendor name
        if idx < len(sorted_blocks) * 0.4:
            lower_text = text.lower()
            if any(suffix in lower_text for suffix in ["ltd", "pvt", "solutions", "limited", "private", "enterprises", "associates", "industries", "systems"]):
                clean_vendor = text
                for kw in ["vendor:", "supplier:", "m/s", "issued to:", "from:"]:
                    if clean_vendor.lower().startswith(kw):
                        clean_vendor = clean_vendor[len(kw):].strip()
                vendor_candidates.append((clean_vendor.strip(" :,.;"), idx, 1.2))

    # Helper to pick best candidate
    def resolve_best(candidates, field_name):
        best_val = None
        best_score = -1.0
        best_idx = 0
        
        for val, idx, prior in candidates:
            context_score = get_context_score(idx, field_name)
            total_score = prior + context_score
            
            if field_name == "po_number":
                if str(val).upper().startswith("PO"):
                    total_score += 2.0
                if str(val).upper().startswith("INV") or str(val).upper().startswith("BILL"):
                    total_score -= 5.0
                if extracted.get("invoice_no") and str(val) == extracted["invoice_no"]["value"]:
                    total_score -= 5.0
            elif field_name == "invoice_no":
                if str(val).upper().startswith("INV") or "BILL" in str(val).upper():
                    total_score += 2.0
                if str(val).upper().startswith("PO"):
                    total_score -= 5.0
                    
            if total_score > best_score:
                best_score = total_score
                best_val = val
                best_idx = idx
                
        if best_val is not None:
            extracted[field_name] = {
                "field": field_name,
                "value": best_val,
                "page": sorted_blocks[best_idx].get("page", 1),
                "bbox": sorted_blocks[best_idx].get("bbox", [0, 0, 0, 0]),
                "page_width": sorted_blocks[best_idx].get("page_width"),
                "page_height": sorted_blocks[best_idx].get("page_height")
            }

    # 3. Resolve each target field
    resolve_best(gstin_candidates, "gstin")
    resolve_best(date_candidates, "invoice_date")
    
    if vendor_candidates:
        resolve_best(vendor_candidates, "vendor_name")
    else:
        top_blocks = sorted_blocks[:5]
        fallback_vendors = []
        for idx, block in enumerate(top_blocks):
            txt = block["text"].strip()
            if len(txt) > 5 and not any(x in txt.lower() for x in ["invoice", "date", "no:", "gstin", "po"]):
                fallback_vendors.append((txt, idx, 0.5))
        resolve_best(fallback_vendors, "vendor_name")

    resolve_best(code_candidates, "invoice_no")
    resolve_best(code_candidates, "po_number")
    
    if "invoice_no" in extracted and "po_number" in extracted:
        if extracted["invoice_no"]["value"] == extracted["po_number"]["value"]:
            filtered_po_candidates = [c for c in code_candidates if c[0] != extracted["invoice_no"]["value"]]
            if filtered_po_candidates:
                resolve_best(filtered_po_candidates, "po_number")

    # Resolve total_amount first
    resolve_best(amount_candidates, "total_amount")
    
    total_val = None
    if "total_amount" in extracted:
        total_val = extracted["total_amount"]["value"]
        
    # taxable_value: must be less than or equal to total_amount
    taxable_candidates = amount_candidates.copy()
    if total_val is not None:
        taxable_candidates = [c for c in taxable_candidates if c[0] <= total_val]
    resolve_best(taxable_candidates, "taxable_value")
    
    taxable_val = None
    if "taxable_value" in extracted:
        taxable_val = extracted["taxable_value"]["value"]
        
    # cgst, sgst, igst: must be less than taxable_value
    tax_candidates = amount_candidates.copy()
    if taxable_val is not None:
        tax_candidates = [c for c in tax_candidates if c[0] < taxable_val]
    elif total_val is not None:
        tax_candidates = [c for c in tax_candidates if c[0] < total_val]
    
    # Also boost if it is close to 9% or 18% of taxable_value
    if taxable_val is not None:
        boosted_tax = []
        for val, idx, prior in tax_candidates:
            ratio = val / taxable_val
            boost = 0.0
            if abs(ratio - 0.09) < 0.01 or abs(ratio - 0.18) < 0.01 or abs(ratio - 0.05) < 0.01 or abs(ratio - 0.025) < 0.005 or abs(ratio - 0.14) < 0.01:
                boost = 2.0
            boosted_tax.append((val, idx, prior + boost))
        tax_candidates = boosted_tax

    resolve_best(tax_candidates, "cgst")
    resolve_best(tax_candidates, "sgst")
    resolve_best(tax_candidates, "igst")
    
    # quantity: usually smaller number, near "qty" or "quantity".
    qty_candidates = amount_candidates.copy()
    # Penalize large values for quantity
    qty_candidates = [(val, idx, prior - 2.0 if val > 10000 else prior) for val, idx, prior in qty_candidates]
    resolve_best(qty_candidates, "quantity")
    
    # unit_rate: unit price. Should be less than taxable_value (unless quantity is 1).
    rate_candidates = amount_candidates.copy()
    if taxable_val is not None:
        rate_candidates = [c for c in rate_candidates if c[0] <= taxable_val]
    resolve_best(rate_candidates, "unit_rate")
    
    # certified_amount & approval_limit
    resolve_best(amount_candidates, "certified_amount")
    resolve_best(amount_candidates, "approval_limit")

    # Helper for resolving general text fields
    def resolve_general_text(field_name: str):
        best_val = None
        best_score = 0.0
        best_idx = 0
        for idx, block in enumerate(sorted_blocks):
            txt = block["text"].strip()
            if not txt or len(txt) < 3:
                continue
            # Skip common field names to avoid false positive matches on label elements
            if any(l in txt.lower() for l in ["invoice no", "gstin", "po number", "date"]):
                continue
            context_score = get_context_score(idx, field_name)
            if context_score > best_score:
                best_score = context_score
                best_val = txt
                best_idx = idx
        if best_val is not None:
            cleaned_val = best_val
            for label in field_contexts.get(field_name, []):
                if label in cleaned_val.lower():
                    parts = re.split(r':|-', cleaned_val, 1)
                    if len(parts) > 1:
                        cleaned_val = parts[1].strip()
                    break
            extracted[field_name] = {
                "field": field_name,
                "value": cleaned_val,
                "page": sorted_blocks[best_idx].get("page", 1),
                "bbox": sorted_blocks[best_idx].get("bbox", [0, 0, 0, 0])
            }

    # Resolve new generic fields using layout-semantic scoring
    resolve_general_text("item")
    resolve_general_text("description")
    resolve_general_text("approved_by")
    resolve_general_text("dc_no")
    resolve_general_text("boq_no")
    resolve_general_text("wcc_no")
    resolve_general_text("dc_summary_no")

    # Fallbacks in case regex failed
    if "invoice_no" not in extracted:
        m = re.search(r'(?i)invoice\s*(?:no|number|#)[\s:]*([a-zA-Z0-9\-\/]+)', full_text)
        if m:
            matched_text = m.group(1).strip()
            extracted["invoice_no"] = {
                "field": "invoice_no",
                "value": matched_text,
                "page": 1,
                "bbox": _find_block_bbox(blocks, matched_text)
            }
    if "po_number" not in extracted:
        m = re.search(r'(?i)po\s*(?:no|number|#)[\s:]*([a-zA-Z0-9\-\/]+)', full_text)
        if m:
            matched_text = m.group(1).strip()
            extracted["po_number"] = {
                "field": "po_number",
                "value": matched_text,
                "page": 1,
                "bbox": _find_block_bbox(blocks, matched_text)
            }
                    
    return extracted

def _clean_float(val: str) -> float:
    try:
        cleaned = re.sub(r'[^\d\.]', '', val)
        if cleaned:
            return float(cleaned)
    except:
        pass
    return None

def _find_block_bbox(blocks: List[Dict], search_text: str) -> List[int]:
    for b in blocks:
        if search_text.lower() in b["text"].lower() or b["text"].lower() in search_text.lower():
            return b["bbox"]
    return [0, 0, 0, 0]
