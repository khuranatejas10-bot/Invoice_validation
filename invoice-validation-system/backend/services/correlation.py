import os
import json
import uuid
from typing import Dict, Any, List

def _format_extracted_fields(doc_type: str, extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw extracted fields to the user-requested schema per document category.
    Returns a dict containing only the relevant scalar values (no nested dicts).
    """
    def _val(key: str):
        v = extracted_fields.get(key)
        if v is None:
            return None
        if isinstance(v, dict):
            return v.get("value")
        return v  # already a plain value

    lt = doc_type.lower()
    if lt == "invoice":
        return {
            "invoice_no": _val("invoice_no"),
            "vendor": _val("vendor_name"),
            "amount": _val("total_amount"),
            "gst": _val("gstin")
        }
    if lt in ["purchase order", "po"]:
        return {
            "po_no": _val("po_number"),
            "item": _val("item"),
            "qty": _val("quantity")
        }
    if lt == "delivery challan":
        return {
            "dc_no": _val("dc_no") or _val("invoice_no"),
            "vendor": _val("vendor_name"),
            "qty": _val("quantity"),
            "amount": _val("total_amount")
        }
    if lt == "bill of quantity":
        return {
            "boq_no": _val("boq_no") or _val("invoice_no"),
            "description": _val("description"),
            "qty": _val("quantity"),
            "rate": _val("unit_rate"),
            "certified_amount": _val("certified_amount")
        }
    if lt in ["work completion", "work completion certificate"]:
        return {
            "wcc_no": _val("wcc_no") or _val("invoice_no"),
            "vendor": _val("vendor_name"),
            "certified_amount": _val("certified_amount") or _val("total_amount")
        }
    if lt in ["dc summary", "dcs"]:
        return {
            "dc_summary_no": _val("dc_summary_no") or _val("invoice_no"),
            "total_qty": _val("quantity"),
            "total_amount": _val("total_amount")
        }
    if lt in ["approval email", "email"]:
        return {
            "approval_from": _val("vendor_name"),
            "approval_limit": _val("approval_limit"),
            "approved_by": _val("approved_by")
        }
    # Default: return all raw extracted scalar values
    return {k: (v.get("value") if isinstance(v, dict) else v) for k, v in extracted_fields.items()}

DATA_STORE_DIR = "/Users/rabbanitejaskhurana/Desktop/EY/invoice-validation-system/backend/data_store"
os.makedirs(DATA_STORE_DIR, exist_ok=True)

class DuplicateDocumentError(Exception):
    """Exception raised when duplicate documents of the same category are detected."""
    pass

def get_all_cases() -> List[Dict[str, Any]]:
    """Loads all cases from the JSON data_store."""
    cases = []
    for filename in os.listdir(DATA_STORE_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(DATA_STORE_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cases.append(json.load(f))
            except Exception as e:
                print(f"Error reading case file {filename}: {e}")
    return cases

def save_case(case_data: Dict[str, Any]) -> str:
    """Saves case data to a specific JSON file."""
    case_id = case_data.get("case_id")
    if not case_id:
        case_id = str(uuid.uuid4())
        case_data["case_id"] = case_id
    
    # Safe filename
    safe_id = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in case_id])
    filepath = os.path.join(DATA_STORE_DIR, f"case_{safe_id}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(case_data, f, indent=4, ensure_ascii=False)
    return filepath

def correlate_and_store_document(
    doc_type: str, 
    extracted_fields: Dict[str, Any], 
    subcategory: str
) -> Dict[str, Any]:
    """
    Correlates an uploaded document with existing cases:
    1. If a document of the same category (e.g. 'Invoice') with the same identifier is already present in a case, raise DuplicateDocumentError.
    2. If there's a cross-match of identifiers (e.g. PO number, Invoice number) across other document types, map them together.
    3. Update the matching JSON file, or create a new one.
    """
    # Extract identifiers from the incoming document
    # extracted_fields here still has {field: {"value": ...}} structure (raw ai_extractor output)
    incoming_inv_no = None
    incoming_po_no = None

    def _safe_val(d, key):
        """Safely get value whether stored as plain string or {value: ...} dict."""
        v = d.get(key)
        if v is None:
            return None
        if isinstance(v, dict):
            return v.get("value")
        return v

    incoming_inv_no = _safe_val(extracted_fields, "invoice_no")
    incoming_po_no = _safe_val(extracted_fields, "po_number")
        
    all_cases = get_all_cases()
    matched_case = None
    for case in all_cases:
        # 2. Cross-matching correlation check (e.g. PO matches Invoice PO)
        if not matched_case:
            case_inv_no = case.get("invoice_no")
            case_po_no = case.get("po_number")
            
            # If po numbers or invoice numbers match, correlate
            po_match = (incoming_po_no and case_po_no and str(incoming_po_no).strip().upper() == str(case_po_no).strip().upper())
            inv_match = (incoming_inv_no and case_inv_no and str(incoming_inv_no).strip().upper() == str(case_inv_no).strip().upper())
            
            if po_match or inv_match:
                matched_case = case

    if matched_case:
        # Update existing case
        # Store formatted fields per category schema
        formatted = _format_extracted_fields(doc_type, extracted_fields)
        matched_case["documents"][doc_type] = formatted
        # Update overall case identifiers if newly found
        if incoming_inv_no and not matched_case.get("invoice_no"):
            matched_case["invoice_no"] = incoming_inv_no
        if incoming_po_no and not matched_case.get("po_number"):
            matched_case["po_number"] = incoming_po_no
            
        # Update subcategory if needed
        if subcategory:
            matched_case["subcategory"] = subcategory
            
        case_path = save_case(matched_case)
        # Return case data with file path for reference
        matched_case["case_file_path"] = case_path
        return matched_case
    else:
        # Create a new correlated case
        new_case_id = incoming_inv_no or incoming_po_no or str(uuid.uuid4())[:8]
        formatted = _format_extracted_fields(doc_type, extracted_fields)
        new_case = {
            "case_id": new_case_id,
            "invoice_no": incoming_inv_no,
            "po_number": incoming_po_no,
            "subcategory": subcategory,
            "documents": {
                doc_type: formatted
            }
        }
        case_path = save_case(new_case)
        new_case["case_file_path"] = case_path
        return new_case
