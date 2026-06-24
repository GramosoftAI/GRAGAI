"""
Configuration mapping semantic business groups to deterministic entity fields.
This enables "Business Object Intelligence" by grouping fields naturally requested together.
"""

ENTITY_GROUPS = {
    "vehicle_details": [
        "vin", 
        "engine_number", 
        "registration_number", 
        "chassis_number",
        "make",
        "model",
        "variant",
        "color",
        "fuel_type"
    ],
    "customer_details": [
        "customer_name", 
        "gstin", 
        "address", 
        "phone", 
        "email",
        "pan",
        "state",
        "state_code"
    ],
    "delivery_details": [
        "delivery_address", 
        "delivery_gstin", 
        "delivery_state",
        "place_of_supply",
        "ship_to_name"
    ],
    "invoice_details": [
        "invoice_number", 
        "po_number", 
        "invoice_date", 
        "total_amount",
        "tax_amount",
        "cgst",
        "sgst",
        "igst",
        "discount",
        "hsn_code"
    ],
    "dealer_details": [
        "dealer_name",
        "dealer_address",
        "dealer_gstin",
        "dealer_pan"
    ]
}
