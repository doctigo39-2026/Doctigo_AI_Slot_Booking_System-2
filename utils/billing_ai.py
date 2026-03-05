# utils/billing_ai.py

# Simple AI-based suggestion mapping
# Later you can connect this with GPT/OpenAI for advanced suggestions

def suggest_charges(diagnosis: str):
    diagnosis = diagnosis.lower()
    
    charges = []

    # Example rules
    if "appendicitis" in diagnosis or "appendectomy" in diagnosis:
        charges.append(("Surgery - Appendectomy", 1, 50000, 50000))
        charges.append(("Operation Theatre Charges", 1, 10000, 10000))
        charges.append(("Anesthesia Charges", 1, 8000, 8000))
        charges.append(("Post-op Medicines", 5, 200, 1000))
    
    elif "angioplasty" in diagnosis or "heart" in diagnosis:
        charges.append(("Surgery - Angioplasty", 1, 75000, 75000))
        charges.append(("Stent Cost", 1, 30000, 30000))
        charges.append(("Cardiology OT Charges", 1, 12000, 12000))
        charges.append(("Medicines & Consumables", 10, 300, 3000))

    elif "fracture" in diagnosis:
        charges.append(("Fracture Reduction Procedure", 1, 15000, 15000))
        charges.append(("Plaster of Paris (POP) Cast", 1, 2000, 2000))
        charges.append(("X-Ray", 1, 1500, 1500))
        charges.append(("Pain Medicines", 5, 150, 750))
    
    elif "general checkup" in diagnosis or "fever" in diagnosis:
        charges.append(("Consultation Fee", 1, 1000, 1000))
        charges.append(("Lab Test - Blood", 1, 500, 500))
        charges.append(("Lab Test - Urine", 1, 300, 300))
        charges.append(("Medicines", 5, 100, 500))
    
    else:
        charges.append(("Consultation Fee", 1, 1000, 1000))
        charges.append(("Basic Medicines", 5, 100, 500))

    return charges
