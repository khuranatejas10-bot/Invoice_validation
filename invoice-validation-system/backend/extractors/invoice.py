import re
from typing import Dict, Any, List

def _find_block_bbox(blocks: List[Dict], search_text: str) -> List[int]:
    """Helper to find the bbox of the block containing the matched text."""
    if not search_text:
        return [0, 0, 0, 0]
    
    # We look for the block that has the search_text as a substring, or vice versa
    for b in blocks:
        if search_text.lower() in b["text"].lower() or b["text"].lower() in search_text.lower():
            return b["bbox"]
    
    # Fallback to first block or 0s
    return [0, 0, 0, 0]

def _build_field(name: str, value: Any, page: int, match_text: str, blocks: List[Dict]) -> Dict[str, Any]:
    if value is None:
        return None
    return {
        "field": name,
        "value": value,
        "page": page,
        "bbox": _find_block_bbox(blocks, match_text)
    }

def extract_invoice_fields(blocks: List[Dict], page: int = 1) -> Dict[str, Any]:
    """Extract standard fields from an Invoice using regex."""
    text = "\n".join([b["text"] for b in blocks])
    
    fields = {}
    
    inv_no_match = re.search(r'(?i)invoice\s*(?:no|number|#)[\s:]*([a-zA-Z0-9\-\/]+)', text)
    if inv_no_match:
        fields["invoice_no"] = _build_field("invoice_no", inv_no_match.group(1).strip(), page, inv_no_match.group(1), blocks)
        
    date_match = re.search(r'(?i)date[\s:]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text)
    if date_match:
        fields["invoice_date"] = _build_field("invoice_date", date_match.group(1).strip(), page, date_match.group(1), blocks)
        
    gstin_match = re.search(r'(?i)gstin[\s:]*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})', text)
    if gstin_match:
        fields["gstin"] = _build_field("gstin", gstin_match.group(1).strip().upper(), page, gstin_match.group(1), blocks)
        
    po_match = re.search(r'(?i)po\s*(?:no|number|#)[\s:]*([a-zA-Z0-9\-\/]+)', text)
    if po_match:
        fields["po_number"] = _build_field("po_number", po_match.group(1).strip(), page, po_match.group(1), blocks)
        
    taxable_match = re.search(r'(?i)taxable\s*(?:value|amount)[\s:]*(?:rs\.?|inr|\$)?[\s]*([\d,]+\.?\d*)', text)
    if taxable_match:
        val = float(taxable_match.group(1).replace(',', ''))
        fields["taxable_value"] = _build_field("taxable_value", val, page, taxable_match.group(1), blocks)
        
    total_match = re.search(r'(?i)(?:total|grand\s*total)[\s:]*(?:rs\.?|inr|\$)?[\s]*([\d,]+\.?\d*)', text)
    if total_match:
        val = float(total_match.group(1).replace(',', ''))
        fields["total_amount"] = _build_field("total_amount", val, page, total_match.group(1), blocks)
        
    return fields

def extract_po_fields(blocks: List[Dict], page: int = 1) -> Dict[str, Any]:
    """Extract standard fields from a Purchase Order."""
    text = "\n".join([b["text"] for b in blocks])
    fields = {}
    
    po_no_match = re.search(r'(?i)po\s*(?:no|number|#)[\s:]*([a-zA-Z0-9\-\/]+)', text)
    if po_no_match:
        fields["po_number"] = _build_field("po_number", po_no_match.group(1).strip(), page, po_no_match.group(1), blocks)
        
    date_match = re.search(r'(?i)date[\s:]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text)
    if date_match:
        fields["po_date"] = _build_field("po_date", date_match.group(1).strip(), page, date_match.group(1), blocks)
        
    return fields

def extract_approval_fields(blocks: List[Dict], page: int = 1) -> Dict[str, Any]:
    """Extract standard fields from an Approval Document."""
    text = "\n".join([b["text"] for b in blocks])
    fields = {}
    
    limit_match = re.search(r'(?i)(?:approval|approved)\s*(?:limit|amount)[\s:]*(?:rs\.?|inr|\$)?[\s]*([\d,]+\.?\d*)', text)
    if limit_match:
        val = float(limit_match.group(1).replace(',', ''))
        fields["approval_limit"] = _build_field("approval_limit", val, page, limit_match.group(1), blocks)
        
    return fields

def extract_fields(document_type: str, blocks: List[Dict], page: int = 1) -> Dict[str, Any]:
    """Main router for field extraction based on document type."""
    text = "\n".join([b["text"] for b in blocks])
    if document_type == "Invoice":
        res = extract_invoice_fields(blocks, page)
    elif document_type == "Purchase Order":
        res = extract_po_fields(blocks, page)
    elif document_type in ["Approval Document", "Approval Email"]:
        res = extract_approval_fields(blocks, page)
    else:
        res = {}
    res["raw_text"] = {"field": "raw_text", "value": text, "page": page, "bbox": [0, 0, 0, 0]}
    return res

