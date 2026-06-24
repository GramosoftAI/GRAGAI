import pytest
import asyncio
from app.core.pdf_extractor import PDFExtractor

@pytest.mark.asyncio
async def test_extractive_gstin():
    text = "Please ship to our primary warehouse. GSTIN No: 33AAACS8779D1Z7. Place of Supply: TAMIL NADU."
    
    results = await PDFExtractor.extract_structured_entities(text)
    
    assert "identifiers" in results
    gstin_entities = [e for e in results["identifiers"] if e["type"] == "GSTIN"]
    
    assert len(gstin_entities) > 0, "Failed to extract GSTIN"
    
    # Critical: Character-level accuracy
    assert gstin_entities[0]["value"] == "33AAACS8779D1Z7"
    
@pytest.mark.asyncio
async def test_extractive_pan():
    text = "Vendor details: PAN Number ABCDE1234F. Address: 123 Main St."
    
    results = await PDFExtractor.extract_structured_entities(text)
    
    pan_entities = [e for e in results["identifiers"] if e["type"] == "PAN"]
    assert len(pan_entities) > 0, "Failed to extract PAN"
    assert pan_entities[0]["value"] == "ABCDE1234F"

@pytest.mark.asyncio
async def test_extractive_vin():
    text = "Vehicle VIN: W1K2231616L002324 is scheduled for maintenance."
    
    results = await PDFExtractor.extract_structured_entities(text)
    
    vin_entities = [e for e in results["identifiers"] if e["type"] == "VIN"]
    assert len(vin_entities) > 0, "Failed to extract VIN"
    assert vin_entities[0]["value"] == "W1K2231616L002324"

@pytest.mark.asyncio
async def test_extractive_invoice():
    text = "Payment required for Invoice Number: SU11C0825INC2048"
    
    results = await PDFExtractor.extract_structured_entities(text)
    
    inv_entities = [e for e in results["identifiers"] if e["type"] == "INVOICE_NUMBER"]
    assert len(inv_entities) > 0, "Failed to extract Invoice Number"
    assert inv_entities[0]["value"] == "SU11C0825INC2048"

@pytest.mark.asyncio
async def test_extractive_section():
    text = "Place of Delivery:\nAddress: 123 Logistics Way\nState: TN\nGSTIN: 33XYZ1234"
    
    results = await PDFExtractor.extract_structured_entities(text)
    
    sections = results.get("sections", [])
    assert len(sections) > 0, "Failed to extract sections"
    
    pod_section = next((s for s in sections if "Delivery" in s["name"] or "delivery" in s["name"].lower()), None)
    assert pod_section is not None
    assert isinstance(pod_section["content"], dict)

@pytest.mark.asyncio
async def test_extractive_multivendor_aliases():
    invoices = [
        "GSTIN No: 33AAACS8779D1Z7",
        "GST Registration Number: 33AAACS8779D1Z7",
        "GSTIN/UIN: 33AAACS8779D1Z7",
        "Tax Identification Number: 33AAACS8779D1Z7"
    ]
    
    for inv_text in invoices:
        results = await PDFExtractor.extract_structured_entities(inv_text)
        # All aliases should resolve to canonical GSTIN
        gstin_entities = [e for e in results["identifiers"] if e["type"] == "GSTIN"]
        assert len(gstin_entities) > 0, f"Failed to extract GSTIN from alias in: {inv_text}"
        assert gstin_entities[0]["value"] == "33AAACS8779D1Z7"
        
@pytest.mark.asyncio
async def test_extractive_confidence_workflow():
    text = "Our GSTIN might be 33AAACS8779D1Z7 but I am not sure."
    
    results = await PDFExtractor.extract_structured_entities(text)
    gstin_entities = [e for e in results["identifiers"] if e["type"] == "GSTIN"]
    
    assert len(gstin_entities) > 0
    # LLM should theoretically assign a lower confidence here, 
    # but we just assert the confidence field exists and is a float
    assert "confidence" in gstin_entities[0]
    assert isinstance(gstin_entities[0]["confidence"], float)
