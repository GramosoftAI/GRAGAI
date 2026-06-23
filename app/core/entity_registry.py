"""Entity Registry for Canonical Form Resolution"""

from typing import Dict, List, Optional

# Master mapping of canonical entity types to their known aliases
ENTITY_TYPES: Dict[str, List[str]] = {
    "GSTIN": [
        "GSTIN No", 
        "GST Reg. Number", 
        "Tax Identification Number", 
        "Buyer GST Registration", 
        "GST Registration No.", 
        "GSTIN/UIN",
        "GST Number"
    ],
    "PAN": [
        "PAN Number",
        "Permanent Account Number",
        "PAN No",
        "PAN"
    ],
    "VIN": [
        "Vehicle Identification Number",
        "VIN Number",
        "Chassis Number"
    ],
    "INVOICE_NUMBER": [
        "Invoice No",
        "Bill No",
        "Invoice ID",
        "Tax Invoice Number",
        "Reference No",
        "Inv No"
    ],
    "PO_NUMBER": [
        "PO Number",
        "Purchase Order Number",
        "Order No",
        "PO Ref"
    ],
    "ENGINE_NUMBER": [
        "Engine No",
        "Motor Number"
    ],
    "REGISTRATION_NUMBER": [
        "Registration No",
        "Vehicle Registration Number",
        "Reg No"
    ],
    "HSN_CODE": [
        "HSN",
        "HSN/SAC",
        "Harmonized System Nomenclature"
    ]
}

def resolve_entity_type(alias: str) -> str:
    """
    Resolve any extracted alias to its canonical entity type.
    Falls back to the uppercased, underscored alias if no match is found.
    """
    alias_clean = alias.strip().lower()
    
    for canonical, aliases in ENTITY_TYPES.items():
        if alias_clean == canonical.lower():
            return canonical
        for a in aliases:
            if alias_clean == a.lower():
                return canonical
                
    # Fallback normalizer
    return alias.strip().upper().replace(" ", "_")

def get_all_aliases() -> List[str]:
    """Returns a flat list of all recognized aliases and canonical names for LLM prompting."""
    aliases = []
    for canonical, alias_list in ENTITY_TYPES.items():
        aliases.append(canonical)
        aliases.extend(alias_list)
    return list(set(aliases))
