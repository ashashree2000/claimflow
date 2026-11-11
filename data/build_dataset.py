"""Build the synthetic ClaimFlow dataset from one spec.

Everything here is SYNTHETIC: the people, policy numbers, phone numbers, emails,
hospitals and events are invented. The insurer (Northwind Mutual) is fictional.

The spec below is the single source of truth. From it this script writes:
  data/claims/<id>.json   the FNOL email and the claim's event log
  data/labels.jsonl       the gold labels used by the evaluation

Labels are computed from the spec (severity from the SOP-INT-1.3 rubric,
process flaws from the planted flaw list), never typed separately, so the
emails, event logs and labels cannot drift apart.

Run:  python data/build_dataset.py
Then: python data/check_dataset.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent

DOC_LABELS = {
    "claim_form": "claim form",
    "driving_licence": "driving licence",
    "registration_certificate": "registration certificate",
    "damage_photos": "damage photos",
    "repair_estimate": "repair estimate",
    "police_report": "police report",
    "proof_of_ownership": "proof of ownership",
    "discharge_summary": "discharge summary",
    "itemised_bill": "itemised hospital bill",
    "id_proof": "ID proof",
}

INCIDENT_TYPES = {
    "motor": ["collision", "theft", "windscreen", "fire_natural_peril", "third_party", "breakdown", "other"],
    "property": ["fire", "escape_of_water", "storm_flood", "burglary_theft", "gradual_damage", "other"],
    "health": ["hospitalisation", "day_care", "outpatient", "other"],
}


def required_docs(lob: str, incident_type: str) -> list[str]:
    """Document checklist from SOP-DOC-2.1 / 2.2 / 2.3."""
    if lob == "motor":
        if incident_type == "theft":
            return ["claim_form", "driving_licence", "registration_certificate", "police_report"]
        return ["claim_form", "driving_licence", "registration_certificate", "damage_photos", "repair_estimate"]
    if lob == "property":
        docs = ["claim_form", "damage_photos", "repair_estimate", "proof_of_ownership"]
        return docs + ["police_report"] if incident_type == "burglary_theft" else docs
    return ["claim_form", "discharge_summary", "itemised_bill", "id_proof"]


def severity(f: dict) -> str:
    """SOP-INT-1.3 rubric."""
    est = f.get("estimate")
    if f.get("injury") or f.get("vehicle_theft") or f.get("fire") or f.get("emergency") or (est and est >= 500_000):
        return "high"
    if (est and est >= 50_000) or f.get("planned"):
        return "medium"
    return "low"


# Flaw type -> SOP section a correct fix must cite.
FLAW_SOP = {
    "duplicate_request": "SOP-DOC-1.3",
    "repeated_verification": "SOP-VER-1.2",
    "out_of_order": "SOP-VER-1.1",
    "excessive_wait_ack": "SOP-TIM-1.1",
    "excessive_wait_doc": "SOP-TIM-1.2",
}
MISSING_DOC_SOP = {"motor": "SOP-DOC-2.1", "property": "SOP-DOC-2.2", "health": "SOP-DOC-2.3"}

# ---------------------------------------------------------------------------
# The spec. One dict per claim.
#   decision: covered | not_covered | needs_review
#   req: clause IDs a correct decision must cite; ok: also acceptable to cite
#   xref: decision needs a cross-reference (designed subset)
#   flaws: planted process flaws as (kind, document or None)
#   sev: facts for the severity rubric
# ---------------------------------------------------------------------------
CLAIMS = [
    # ------------------------------ MOTOR ------------------------------
    dict(id="C01", lob="motor", name="Rohan Mehta", policy="MTR-26-10417", date="2026-10-12",
         itype="windscreen", loc="Lonavala", sent="2026-10-13T09:40",
         attach={"damage_photos": "windscreen_crack_1.jpg", "driving_licence": "DL_scan_RM.pdf"},
         sev=dict(estimate=18_000), decision="covered", req=["MOTOR-COV-2.4"], ok=["MOTOR-LIM-3.2"],
         flaws=[("excessive_wait_ack", None)],
         subject="Windscreen damage - policy MTR-26-10417",
         body="""Hello,

I'm writing to report damage to my car under policy MTR-26-10417. On 12 October 2026, while I was driving on the expressway near Lonavala, a stone thrown up by a truck hit the windscreen and it cracked right across the driver's side. Nobody was hurt and the rest of the car is fine.

The glass shop near my home quoted about Rs 18,000 to replace the windscreen. I've attached photos of the crack and a scan of my driving licence. Please let me know the next steps.

Regards,
Rohan Mehta
Phone: +91 90000 11223"""),

    dict(id="C02", lob="motor", name="Kavya Iyer", policy="MTR-26-11862", date="2026-10-15",
         itype="collision", loc="Bengaluru", sent="2026-10-16T18:05",
         attach={"damage_photos": "front_damage.zip", "driving_licence": "licence.pdf",
                 "registration_certificate": "RC.pdf", "repair_estimate": "workshop_estimate.pdf"},
         sev=dict(estimate=85_000), decision="covered", req=["MOTOR-COV-2.1"],
         ok=["MOTOR-LIM-3.1", "MOTOR-DEF-1.2", "MOTOR-CON-5.1"], flaws=[],
         subject="Accident claim for policy MTR-26-11862",
         body="""Dear claims team,

On the evening of 15 October 2026 it was raining heavily on Outer Ring Road in Bengaluru, near Marathahalli. My car skidded on the wet road and hit the road divider. I was driving alone and was not injured.

The front bumper, bonnet and left headlamp are damaged. The workshop has estimated Rs 85,000 for the repairs. I have attached photos of the damage, my driving licence, the registration certificate and the workshop's estimate.

Thanks,
Kavya Iyer
kavya.iyer@example.com | +91 90000 22334"""),

    dict(id="C03", lob="motor", name="Arjun Malhotra", policy="MTR-26-20981", date="2026-10-18",
         itype="collision", loc="Gurugram", sent="2026-10-19T11:20",
         attach={"damage_photos": "IMG_4471.jpg", "repair_estimate": "estimate_AM.pdf"},
         sev=dict(estimate=120_000), decision="not_covered", req=["MOTOR-EXC-4.3"], ok=["MOTOR-COV-2.1"],
         flaws=[("duplicate_request", "claim_form")],
         subject="Accident last night",
         body="""Hi,

I need to report an accident from last night, 18 October 2026, on Golf Course Road in Gurugram. I was driving back from a friend's birthday party at around 1 am and ran into the back of a truck that was standing on the road. Nobody was hurt.

The traffic police did a breath test at the scene and the reading was above the legal limit, and they issued a challan. The front of my car is badly damaged and the workshop estimate is Rs 1,20,000. Photos and the estimate are attached. My policy number is MTR-26-20981.

Arjun Malhotra
+91 90000 33445"""),

    dict(id="C04", lob="motor", name="Sneha Kulkarni", policy="MTR-26-31152", date="2026-10-20",
         itype="breakdown", loc="Nashik", sent="2026-10-21T10:15",
         attach={"repair_estimate": "service_centre_estimate.pdf", "registration_certificate": "rc_copy.jpg"},
         sev=dict(estimate=60_000), decision="not_covered", req=["MOTOR-EXC-4.4"], ok=["MOTOR-COV-2.1"],
         flaws=[("out_of_order", None)],
         subject="Engine failure - MTR-26-31152",
         body="""Hello,

My car's engine stopped suddenly on 20 October 2026 while I was driving on the highway near Nashik. There was no accident and no warning light came on before it happened.

The car was towed to the authorised service centre. They say the engine has seized because of an internal failure, and the repair will cost about Rs 60,000. I've attached their estimate and my registration certificate. Policy number MTR-26-31152.

Sneha Kulkarni
sneha.k@example.com"""),

    dict(id="C05", lob="motor", name="Imran Shaikh", policy="MTR-26-40276", date="2026-10-22",
         itype="third_party", loc="Hyderabad", sent="2026-10-22T20:30",
         attach={"damage_photos": "scooter_photos.jpg", "driving_licence": "my_DL.pdf"},
         sev=dict(estimate=22_000), decision="covered", req=["MOTOR-COV-2.3"],
         ok=["MOTOR-LIM-3.3", "MOTOR-CON-5.3"], flaws=[("missing_document", "registration_certificate")],
         subject="Reporting an incident with a parked scooter",
         body="""Dear Sir/Madam,

While reversing out of a parking spot at a shopping mall in Banjara Hills, Hyderabad, this afternoon (22 October 2026), I hit a parked scooter and knocked it over. My own car only has a small scratch that I am not claiming for.

The scooter's owner has shown me a quote of Rs 22,000 for repairing his scooter. I have not agreed to pay him anything and told him I would inform my insurer. Photos of the scooter and my driving licence are attached. My policy is MTR-26-40276.

Regards,
Imran Shaikh
Mobile: 90000 44556"""),

    dict(id="C06", lob="motor", name="Priya Nair", policy="MTR-26-45530", date="2026-10-24",
         itype="fire_natural_peril", loc="Shimla", sent="2026-10-25T08:50",
         attach={"damage_photos": "hail_dents.zip", "driving_licence": "DL_Priya.pdf",
                 "registration_certificate": "RC_Priya.pdf", "repair_estimate": "dent_repair_quote.pdf"},
         sev=dict(estimate=45_000), decision="covered", req=["MOTOR-COV-2.5"], ok=["MOTOR-LIM-3.1"], flaws=[],
         subject="Hailstorm damage to my car",
         body="""Hello,

A hailstorm hit Shimla on the afternoon of 24 October 2026 while my car was parked outside my house. The hailstones left dents all over the roof and the bonnet, and one of the side mirrors is cracked.

The body shop has quoted Rs 45,000 for dent removal and repainting. I've attached photos, my driving licence, the registration certificate and the quote. Policy MTR-26-45530.

Thank you,
Priya Nair
priya.nair@example.com"""),

    dict(id="C07", lob="motor", name="Vikram Singh", policy="MTR-26-52318", date="2026-10-26",
         itype="collision", loc="Jaipur", sent="2026-10-27T13:05",
         attach={"damage_photos": "side_damage.jpg", "repair_estimate": "estimate_VS.pdf"},
         sev=dict(estimate=70_000), decision="not_covered",
         req=["MOTOR-COV-2.1", "MOTOR-EXC-4.2", "MOTOR-DEF-1.3"], ok=["MOTOR-LIM-3.1"], xref=True,
         flaws=[("repeated_verification", None)],
         subject="Accident at a junction - MTR-26-52318",
         body="""Hi,

On 26 October 2026 at about 8 pm another car jumped the signal at a junction in Malviya Nagar, Jaipur, and struck the right side of my car. I wasn't hurt.

In the evenings I drive for a food-ordering app to earn some extra money, and at the time I was on my way to a customer with an order the app had assigned to me. The right doors and the pillar are damaged and the estimate is Rs 70,000. Photos and the estimate are attached. Policy MTR-26-52318.

Vikram Singh
+91 90000 66778"""),

    dict(id="C08", lob="motor", name="Ananya Bose", policy="MTR-26-60744", date="2026-10-19",
         itype="theft", loc="Kolkata", sent="2026-10-24T16:40",
         attach={"police_report": "FIR_copy.pdf", "registration_certificate": "RC_AB.pdf"},
         sev=dict(vehicle_theft=True), decision="not_covered",
         req=["MOTOR-COV-2.2", "MOTOR-CON-5.2"], ok=["MOTOR-LIM-3.1"], xref=True,
         flaws=[("excessive_wait_doc", "driving_licence")],
         subject="My car has been stolen",
         body="""Dear claims team,

My car was stolen from outside my building in Salt Lake, Kolkata. I parked it there on the night of 18 October 2026 and found it missing when I came down on the morning of 19 October 2026.

At first I thought it had been towed, so I spent a few days checking with the towing yards and asking the neighbours. I went to the police station on 23 October 2026 and they registered an FIR. A copy of the FIR and my registration certificate are attached. My policy is MTR-26-60744. The car is about three years old.

Ananya Bose
ananya.bose@example.com"""),

    dict(id="C09", lob="motor", name="Rahul Deshpande", policy="MTR-26-68203", date="2026-10-28",
         itype="collision", loc="Mumbai", sent="2026-10-29T09:25",
         attach={"damage_photos": "left_side.jpg", "registration_certificate": "RC.jpg",
                 "repair_estimate": "garage_estimate.pdf"},
         sev=dict(estimate=95_000), decision="covered",
         req=["MOTOR-COV-2.1", "MOTOR-EXC-4.2", "MOTOR-END-6.1"], ok=["MOTOR-LIM-3.1", "MOTOR-DEF-1.3"], xref=True,
         flaws=[("missing_document", "driving_licence"), ("excessive_wait_ack", None)],
         subject="Accident claim - MTR-26-68203",
         body="""Hello,

I'm reporting an accident on 28 October 2026 on the Western Express Highway in Mumbai, near Goregaon. A tempo changed lanes without signalling and hit the left side of my car.

I was driving three colleagues to our office, as I do every weekday. They each chip in for the petrol and the toll, and I don't earn anything from it. None of us was injured. The left doors and mirror are damaged and the garage estimate is Rs 95,000. I've attached photos, the RC and the estimate.

Rahul Deshpande
+91 90000 77889"""),

    dict(id="C10", lob="motor", name="Deepak Rao", policy="MTR-26-71590", date=None,
         itype="other", loc=None, sent="2026-10-30T19:10", attach={},
         sev=dict(), decision="needs_review", req=[], ok=[], refuse=True,
         flaws=[("duplicate_request", "damage_photos")],
         subject="Claim",
         body="""Hi, my car has been damaged and I need to make a claim as soon as possible. Policy number MTR-26-71590. Please call me back.

Deepak Rao
+91 90000 55667"""),

    # ----------------------------- PROPERTY -----------------------------
    dict(id="C11", lob="property", name="Meera Joshi", policy="PRP-26-11834", date="2026-10-14",
         itype="fire", loc="Ahmedabad", sent="2026-10-15T10:30",
         attach={"damage_photos": "kitchen_fire.zip", "repair_estimate": "contractor_quote.pdf"},
         sev=dict(fire=True, estimate=320_000), decision="covered", req=["PROP-COV-2.1"],
         ok=["PROP-LIM-3.1", "PROP-LIM-3.2", "PROP-CON-5.3"],
         flaws=[("out_of_order", None), ("missing_document", "proof_of_ownership")],
         subject="Fire in our kitchen - PRP-26-11834",
         body="""Dear Sir/Madam,

A fire started in our kitchen on 14 October 2026 when oil in a pan caught fire on the stove. The fire brigade put it out within half an hour. Nobody was hurt, but the kitchen cabinets, the chimney, the fridge and part of the ceiling are burnt, and the rest of our flat in Navrangpura, Ahmedabad, is covered in smoke.

The contractor estimates Rs 3,20,000 for repairs and replacements. Photos and the estimate are attached. Policy PRP-26-11834.

Meera Joshi
meera.joshi@example.com | 90000 12121"""),

    dict(id="C12", lob="property", name="Sanjay Gupta", policy="PRP-26-12907", date="2026-10-17",
         itype="escape_of_water", loc="Lucknow", sent="2026-10-17T14:45",
         attach={"damage_photos": "bathroom_bedroom.jpg", "repair_estimate": "plumber_contractor_estimate.pdf"},
         sev=dict(estimate=65_000), decision="covered", req=["PROP-COV-2.2"], ok=["PROP-LIM-3.3", "PROP-CON-5.3"],
         flaws=[],
         subject="Burst pipe at home",
         body="""Hello,

This morning, 17 October 2026, a pipe under the bathroom basin in our house in Gomti Nagar, Lucknow, burst while we were at home. Water spread into the bedroom before we could shut the main valve.

The bathroom and bedroom flooring and the lower part of the bedroom wall are damaged. The plumber and the contractor together estimate Rs 65,000. Photos and their estimate are attached. My policy number is PRP-26-12907.

Sanjay Gupta
+91 90000 13131"""),

    dict(id="C13", lob="property", name="Farah Khan", policy="PRP-26-20455", date="2026-10-20",
         itype="burglary_theft", loc="Delhi", sent="2026-10-21T09:00",
         attach={"police_report": "police_complaint.pdf", "damage_photos": "back_door.jpg"},
         sev=dict(estimate=210_000), decision="covered", req=["PROP-COV-2.4"], ok=["PROP-CON-5.2", "PROP-LIM-3.2"],
         flaws=[("repeated_verification", None)],
         subject="Burglary at my house - PRP-26-20455",
         body="""Dear claims team,

When we came home from dinner at about 11 pm on 20 October 2026, we found the back door of our house in Lajpat Nagar, Delhi, forced open and the lock broken. A laptop, a camera and some cash were taken, and two cupboards were broken into.

We called the police straight away and they registered our complaint the same night; a copy is attached, along with photos of the door. The stolen items and the repairs come to about Rs 2,10,000.

Farah Khan
farah.khan@example.com"""),

    dict(id="C14", lob="property", name="Lakshmi Reddy", policy="PRP-26-27718", date="2026-10-23",
         itype="burglary_theft", loc="Chennai", sent="2026-10-24T12:10",
         attach={"police_report": "complaint_copy.pdf"},
         sev=dict(estimate=150_000), decision="not_covered", req=["PROP-EXC-4.4"], ok=["PROP-COV-2.4"],
         flaws=[("excessive_wait_doc", "proof_of_ownership")],
         subject="Missing jewellery",
         body="""Hello,

On 23 October 2026 I noticed that two gold bangles and a necklace were missing from the steel cupboard in our bedroom in Adyar, Chennai. The cupboard and the doors were not broken and nothing else in the house was disturbed. Only our family and our domestic help have keys to the house.

I have filed a complaint at the local police station (copy attached). The jewellery is worth about Rs 1,50,000. Policy PRP-26-27718.

Lakshmi Reddy
+91 90000 14141"""),

    dict(id="C15", lob="property", name="Thomas Mathew", policy="PRP-26-33062", date="2026-10-25",
         itype="gradual_damage", loc="Kochi", sent="2026-10-26T17:35",
         attach={"damage_photos": "ceiling_damp.jpg"},
         sev=dict(estimate=40_000), decision="not_covered", req=["PROP-EXC-4.1"], ok=[],
         flaws=[("excessive_wait_ack", None)],
         subject="Damp and leak in bedroom - PRP-26-33062",
         body="""Dear Sir/Madam,

On 25 October 2026 we noticed that the damp patches on the ceiling and walls of our upstairs bedroom in Kochi have spread a lot. The roof has a small leak that has been letting rain seep in slowly since the monsoon started in June. Now the paint is peeling and there is mould in one corner.

A contractor looked at it and quoted Rs 40,000 to fix the roof and redo the plaster and paint. Photos are attached.

Thomas Mathew
thomas.mathew@example.com"""),

    dict(id="C16", lob="property", name="Harpreet Kaur", policy="PRP-26-38841", date="2026-10-27",
         itype="storm_flood", loc="Mohali", sent="2026-10-28T08:20",
         attach={"damage_photos": "roof_sheets.zip", "repair_estimate": "roofing_quote.pdf"},
         sev=dict(estimate=90_000), decision="covered", req=["PROP-COV-2.3"], ok=["PROP-LIM-3.1", "PROP-CON-5.3"],
         flaws=[],
         subject="Storm damage to roof",
         body="""Hello,

During the storm on the night of 27 October 2026, strong winds tore off six of the roof sheets over the back of our house in Mohali and broke the cover of the water tank on the roof.

We have put a tarpaulin over the gap for now. The roofer has quoted Rs 90,000 for new sheets and the tank cover. Photos and the quote are attached. Policy PRP-26-38841.

Harpreet Kaur
+91 90000 15151"""),

    dict(id="C17", lob="property", name="Nikhil Verma", policy="PRP-26-44190", date="2026-10-28",
         itype="escape_of_water", loc="Indore", sent="2026-10-29T11:55",
         attach={"damage_photos": "ceiling_living_room.jpg", "repair_estimate": "repair_estimate.pdf",
                 "proof_of_ownership": "sofa_invoice.pdf"},
         sev=dict(estimate=180_000), decision="not_covered",
         req=["PROP-COV-2.2", "PROP-EXC-4.2", "PROP-DEF-1.3"], ok=[], xref=True,
         flaws=[("duplicate_request", "claim_form")],
         subject="Water damage found after returning home",
         body="""Dear claims team,

My wife and I were away from 10 September to 28 October 2026 visiting our son in Toronto, and nobody stayed in our house in Indore during that time. When we got back on 28 October, we found that a pipe in the upstairs bathroom had burst and water had come through the ceiling into the living room.

The ceiling, the floor and the sofa set are damaged. The estimate is Rs 1,80,000. Photos, the estimate and the sofa's purchase invoice are attached. Policy PRP-26-44190.

Nikhil Verma
nikhil.verma@example.com | 90000 16161"""),

    dict(id="C18", lob="property", name="Pooja Agarwal", policy="PRP-26-51327", date="2026-10-30",
         itype="storm_flood", loc="Thane", sent="2026-10-31T10:40",
         attach={"damage_photos": "ground_floor_water.zip"},
         sev=dict(estimate=240_000), decision="covered",
         req=["PROP-COV-2.3", "PROP-EXC-4.3", "PROP-END-6.1"], ok=["PROP-DEF-1.4", "PROP-LIM-3.1"], xref=True,
         flaws=[("missing_document", "repair_estimate")],
         subject="Rainwater entered our house - PRP-26-51327",
         body="""Hello,

After very heavy rain on 30 October 2026 the drains on our lane in Thane overflowed and rainwater rose about a foot inside the ground floor of our house. The water stayed for most of the night.

The wooden flooring has lifted and the lower part of the walls needs re-plastering and painting. We moved our furniture upstairs in time. A contractor has estimated around Rs 2,40,000 and will send the written estimate. Photos are attached.

Pooja Agarwal
+91 90000 17171"""),

    dict(id="C19", lob="property", name="Aditya Kapoor", policy="PRP-26-56602", date="2026-11-02",
         itype="storm_flood", loc="Noida", sent="2026-11-03T15:15",
         attach={"damage_photos": "basement_items.jpg", "proof_of_ownership": "purchase_bills.pdf"},
         sev=dict(estimate=110_000), decision="not_covered",
         req=["PROP-COV-2.3", "PROP-EXC-4.3", "PROP-END-6.1"], ok=["PROP-DEF-1.4", "PROP-DEF-1.2"], xref=True,
         flaws=[("out_of_order", None)],
         subject="Basement store room soaked",
         body="""Dear Sir/Madam,

Heavy rain on 2 November 2026 sent surface water pouring down the ramp into the basement of our house in Sector 50, Noida. We use the basement as a store room. A sofa set, two mattresses and several cartons of books and winter clothes were soaked through and are ruined.

The building itself was fine once the water was pumped out. The items were worth about Rs 1,10,000. Photos and the purchase bills are attached. Policy PRP-26-56602.

Aditya Kapoor
aditya.kapoor@example.com"""),

    dict(id="C20", lob="property", name="Rekha Pillai", policy="PRP-26-60978", date="2026-10-26",
         itype="other", loc="Mysuru", sent="2026-10-27T18:00",
         attach={"damage_photos": "wall_cracks.zip"},
         sev=dict(estimate=75_000), decision="needs_review", req=[], ok=[], refuse=True,
         flaws=[("excessive_wait_doc", "claim_form")],
         subject="Cracks in walls - PRP-26-60978",
         body="""Hello,

Our neighbour in Mysuru began digging the foundations for a new building next to our house around 20 October 2026, using heavy machinery. On 26 October 2026 we noticed long cracks in two walls of our living room and in the compound wall, and one door no longer closes properly.

A contractor estimates Rs 75,000 to repair the cracks. Photos are attached.

Rekha Pillai
+91 90000 18181"""),

    # ------------------------------ HEALTH ------------------------------
    dict(id="C21", lob="health", name="Aman Tiwari", policy="HLT-26-10552", date="2026-10-13",
         itype="hospitalisation", loc="Bhopal", sent="2026-10-17T10:05",
         attach={"discharge_summary": "discharge_summary.pdf", "id_proof": "id_card.jpg"},
         sev=dict(emergency=True, estimate=140_000), decision="covered", req=["HLTH-COV-2.1"],
         ok=["HLTH-LIM-3.1", "HLTH-LIM-3.2", "HLTH-CON-5.1", "HLTH-DEF-1.1"],
         flaws=[("missing_document", "itemised_bill")],
         subject="Hospitalisation claim - HLT-26-10552",
         body="""Dear claims team,

I was admitted as an emergency to City Care Hospital, Bhopal, on 13 October 2026 with severe stomach pain, and had surgery for appendicitis the same night. I was discharged on 16 October 2026.

The total bill is about Rs 1,40,000. I have attached my discharge summary and my ID card. Policy HLT-26-10552.

Aman Tiwari
aman.tiwari@example.com | +91 90000 21212"""),

    dict(id="C22", lob="health", name="Savitri Devi", policy="HLT-26-11709", date="2026-10-21",
         itype="day_care", loc="Varanasi", sent="2026-10-22T11:30",
         attach={"discharge_summary": "discharge_note.pdf", "itemised_bill": "bill.pdf", "id_proof": "id.pdf"},
         sev=dict(estimate=35_000), decision="covered", req=["HLTH-COV-2.2"], ok=["HLTH-DEF-1.2", "HLTH-LIM-3.3"],
         flaws=[],
         subject="Cataract surgery claim",
         body="""Hello,

I had cataract surgery on my right eye at Netra Eye Centre, Varanasi, on 21 October 2026 and went home the same afternoon. The bill came to Rs 35,000.

I have attached the discharge note, the hospital bill and my ID. My policy number is HLT-26-11709.

Savitri Devi
+91 90000 23232"""),

    dict(id="C23", lob="health", name="Kunal Shah", policy="HLT-26-19364", date="2026-10-19",
         itype="hospitalisation", loc="Mumbai", sent="2026-10-23T16:20",
         attach={"discharge_summary": "aura_discharge.pdf", "itemised_bill": "aura_invoice.pdf"},
         sev=dict(planned=True, estimate=150_000), decision="not_covered", req=["HLTH-EXC-4.2"], ok=["HLTH-COV-2.1"],
         flaws=[("repeated_verification", None)],
         subject="Claim for surgery - HLT-26-19364",
         body="""Hi,

I had nose reshaping surgery (rhinoplasty) at Aura Aesthetic Clinic, Mumbai, on 19 October 2026 and stayed in for one night. I had been unhappy with the shape of my nose for years. There was no injury and no breathing problem behind it.

The bill is Rs 1,50,000. The discharge summary and the invoice are attached.

Kunal Shah
kunal.shah@example.com"""),

    dict(id="C24", lob="health", name="Neha Saxena", policy="HLT-26-24418", date="2026-10-24",
         itype="outpatient", loc="Pune", sent="2026-10-25T09:45",
         attach={"itemised_bill": "clinic_lab_bills.pdf", "id_proof": "id_NS.jpg"},
         sev=dict(estimate=9_000), decision="not_covered", req=["HLTH-EXC-4.3"], ok=[],
         flaws=[("duplicate_request", "claim_form")],
         subject="Reimbursement for back pain treatment",
         body="""Hello,

On 24 October 2026 I visited an orthopaedic doctor at Lotus Clinic, Pune, for lower back pain. He ordered an MRI and blood tests and prescribed medicines. I was not admitted.

The total came to Rs 9,000. The bills and my ID are attached. Policy HLT-26-24418.

Neha Saxena
+91 90000 24242"""),

    dict(id="C25", lob="health", name="Rajesh Kumar", policy="HLT-26-30087", date="2026-11-04",
         itype="hospitalisation", loc="Patna", sent="2026-11-09T12:00",
         attach={"discharge_summary": "discharge_RK.pdf", "itemised_bill": "final_bill_RK.pdf"},
         sev=dict(emergency=True, estimate=60_000), decision="not_covered", req=["HLTH-EXC-4.4"],
         ok=["HLTH-COV-2.1", "HLTH-DEF-1.4"],
         flaws=[("excessive_wait_ack", None), ("duplicate_request", "id_proof")],
         subject="Hospital claim - HLT-26-30087",
         body="""Dear Sir/Madam,

I bought this health policy recently; my cover started on 20 October 2026. On 4 November 2026 I developed a high fever and was admitted to Patliputra Care Hospital, Patna, through the emergency department. Tests showed typhoid, and I was discharged on 8 November 2026.

The bill is Rs 60,000. The discharge summary and the bill are attached.

Rajesh Kumar
rajesh.kumar@example.com | 90000 25252"""),

    dict(id="C26", lob="health", name="Gopal Menon", policy="HLT-26-35541", date="2026-10-27",
         itype="hospitalisation", loc="Kozhikode", sent="2026-11-02T10:10",
         attach={"discharge_summary": "ortho_discharge.pdf", "itemised_bill": "ortho_bill.pdf", "id_proof": "id_GM.pdf"},
         sev=dict(injury=True, emergency=True, estimate=282_500), decision="covered",
         req=["HLTH-COV-2.1", "HLTH-COV-2.4"], ok=["HLTH-LIM-3.1", "HLTH-LIM-3.2", "HLTH-DEF-1.1"],
         flaws=[("out_of_order", None)],
         subject="Claim for hip fracture treatment",
         body="""Hello,

On 27 October 2026 I slipped on the stairs at home in Kozhikode and fractured my hip. An ambulance took me to Malabar Bone and Joint Hospital, where I had surgery and stayed for five days.

The hospital bill is Rs 2,80,000 and the ambulance charged Rs 2,500. I have attached the discharge summary, the itemised bill (which includes the ambulance receipt) and my ID. Policy HLT-26-35541.

Gopal Menon
+91 90000 26262"""),

    dict(id="C27", lob="health", name="Ishita Banerjee", policy="HLT-26-40263", date="2026-10-29",
         itype="hospitalisation", loc="Guwahati", sent="2026-11-03T14:30",
         attach={"discharge_summary": "dengue_discharge.pdf", "itemised_bill": "dengue_bill.pdf", "id_proof": "ID_IB.jpg"},
         sev=dict(emergency=True, estimate=85_000), decision="covered", req=["HLTH-COV-2.1"],
         ok=["HLTH-LIM-3.1", "HLTH-LIM-3.2", "HLTH-DEF-1.1"], flaws=[],
         subject="Dengue hospitalisation claim",
         body="""Dear claims team,

I was admitted to Brahmaputra Hospital, Guwahati, through the emergency department on 29 October 2026 with dengue fever and a falling platelet count. I stayed for four days and was discharged on 2 November 2026.

The bill is Rs 85,000. The discharge summary, the itemised bill and my ID are attached. Policy HLT-26-40263.

Ishita Banerjee
ishita.banerjee@example.com"""),

    dict(id="C28", lob="health", name="Suresh Pandey", policy="HLT-26-47716", date="2026-10-28",
         itype="hospitalisation", loc="Kanpur", sent="2026-10-31T11:15",
         attach={"itemised_bill": "ganga_bill.pdf", "id_proof": "id_SP.jpg"},
         sev=dict(emergency=True, estimate=95_000), decision="covered",
         req=["HLTH-COV-2.1", "HLTH-EXC-4.1", "HLTH-END-6.1"], ok=["HLTH-DEF-1.3", "HLTH-LIM-3.2"], xref=True,
         flaws=[("excessive_wait_doc", "discharge_summary")],
         subject="Emergency admission - HLT-26-47716",
         body="""Hello,

I have had high blood pressure since early 2023 and take tablets for it every day. I took out this policy on 10 April 2025.

On 28 October 2026 my blood pressure shot up very high with a severe headache, and I was admitted through the emergency department at Ganga Hospital, Kanpur, for three days. The bill is Rs 95,000. The bill and my ID are attached; the discharge summary will follow.

Suresh Pandey
+91 90000 27272"""),

    dict(id="C29", lob="health", name="Usha Rani", policy="HLT-26-52809", date="2026-11-03",
         itype="hospitalisation", loc="Visakhapatnam", sent="2026-11-08T10:50",
         attach={"discharge_summary": "knee_discharge.pdf", "itemised_bill": "knee_bill.pdf"},
         sev=dict(planned=True, estimate=320_000), decision="not_covered",
         req=["HLTH-COV-2.1", "HLTH-EXC-4.1", "HLTH-DEF-1.3"], ok=["HLTH-DEF-1.4"], xref=True,
         flaws=[("missing_document", "id_proof")],
         subject="Knee replacement claim",
         body="""Dear Sir/Madam,

My doctor diagnosed osteoarthritis in my right knee in 2022, and I have been on painkillers and physiotherapy since then. I have had this policy since 1 September 2024.

On 3 November 2026 I was admitted to Seaside Ortho Hospital, Visakhapatnam, for a planned knee replacement, and I was discharged on 7 November 2026. The bill is Rs 3,20,000. The discharge summary and the bill are attached. Policy HLT-26-52809.

Usha Rani
usha.rani@example.com"""),

    dict(id="C30", lob="health", name="Karthik Subramanian", policy="HLT-26-58834", date="2026-11-01",
         itype="hospitalisation", loc="Bangkok", sent="2026-11-04T07:30",
         attach={"discharge_summary": "bangkok_discharge.pdf", "id_proof": "passport_scan.pdf"},
         sev=dict(emergency=True, estimate=120_000), decision="needs_review", req=[], ok=[], refuse=True,
         flaws=[("repeated_verification", None), ("excessive_wait_doc", "itemised_bill")],
         subject="Hospitalised while on holiday",
         body="""Hello,

While on holiday in Bangkok, I was admitted through the emergency department of a private hospital on 1 November 2026 with severe food poisoning and dehydration. I stayed for two days and flew home to Chennai on 4 November.

The bill comes to about Rs 1,20,000 after conversion. I've attached the discharge summary and my ID; the itemised bill will follow. Policy HLT-26-58834.

Karthik Subramanian
+91 90000 28282"""),
]


# ---------------------------------------------------------------------------
# Event log generation
# ---------------------------------------------------------------------------
def _ts(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M")


def build_events(c: dict) -> list[dict]:
    """Normal intake flow, then apply the planted flaws."""
    t0 = datetime.fromisoformat(c["sent"])
    h = lambda x: t0 + timedelta(hours=x)  # noqa: E731
    flaws = dict(c["flaws"]) if c["flaws"] else {}
    kinds = [k for k, _ in c["flaws"]]
    missing = [d for d in required_docs(c["lob"], c["itype"]) if d not in c["attach"]]
    assign = "Medical reviewer assigned" if c["lob"] == "health" else "Surveyor assigned"

    ev = [(h(0), "FNOL received", None),
          (h(48) if "excessive_wait_ack" in kinds else h(2), "Acknowledgement sent", None),
          (h(4), "Policy status verified", None),
          (h(5), "Coverage check completed", None)]
    for d in missing:
        if flaws.get("missing_document") == d:
            continue  # never requested
        ev.append((h(6), "Document requested", d))
        if flaws.get("excessive_wait_doc") == d:
            ev.append((h(6 * 24), "Document received", d))  # 6 days, no reminder
        else:
            ev.append((h(48), "Document received", d))
        if flaws.get("duplicate_request") == d:
            ev.append((h(72), "Document requested", d))  # asked again after it arrived
    ev.append((h(3) if "out_of_order" in kinds else h(24), assign, None))
    if "repeated_verification" in kinds:
        ev.append((h(26), "Policy status verified", None))

    ev.sort(key=lambda e: e[0])
    out = []
    for i, (t, step, doc) in enumerate(ev, 1):
        e = {"event_id": f"E{i}", "timestamp": _ts(t), "step": step}
        if doc:
            e["step"] = f"{step}: {DOC_LABELS[doc]}"
            e["document"] = doc
        out.append(e)
    return out


def gold_flaws(c: dict, events: list[dict]) -> list[dict]:
    rows = []
    for kind, doc in c["flaws"]:
        if kind == "missing_document":
            ftype, sop, ids = "missing_document", MISSING_DOC_SOP[c["lob"]], []
        elif kind.startswith("excessive_wait"):
            ftype, sop = "excessive_wait", FLAW_SOP[kind]
            if kind == "excessive_wait_ack":
                ids = [e["event_id"] for e in events if e["step"] in ("FNOL received", "Acknowledgement sent")]
            else:
                ids = [e["event_id"] for e in events if e.get("document") == doc]
        else:
            ftype, sop = kind, FLAW_SOP[kind]
            if kind == "duplicate_request":
                ids = [e["event_id"] for e in events if e.get("document") == doc and e["step"].startswith("Document requested")]
            elif kind == "repeated_verification":
                ids = [e["event_id"] for e in events if e["step"] == "Policy status verified"]
            else:  # out_of_order
                ids = [e["event_id"] for e in events if e["step"] in
                       ("Policy status verified", "Coverage check completed", "Surveyor assigned", "Medical reviewer assigned")]
        row = {"type": ftype, "sop_id": sop, "event_ids": ids}
        if doc:
            row["document"] = doc
        rows.append(row)
    return rows


def main() -> None:
    claims_dir = DATA / "claims"
    claims_dir.mkdir(exist_ok=True)
    labels = []
    for c in CLAIMS:
        events = build_events(c)
        first = c["name"].split()[0].lower()
        last = c["name"].split()[-1].lower()
        record = {
            "claim_id": c["id"],
            "synthetic": True,
            "email": {
                "from_name": c["name"],
                "from_email": f"{first}.{last}@example.com",
                "sent_at": c["sent"],
                "subject": c["subject"],
                "attachments": list(c["attach"].values()),
                "body": c["body"],
            },
            "events": events,
        }
        (claims_dir / f"{c['id']}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
        labels.append({
            "claim_id": c["id"],
            "synthetic": True,
            "line_of_business": c["lob"],
            "expected_route": {"line_of_business": c["lob"], "specialists": ["coverage", "process"]},
            "fields": {
                "claimant_name": c["name"],
                "policy_number": c["policy"],
                "line_of_business": c["lob"],
                "incident_date": c["date"],
                "incident_type": c["itype"],
                "location": c["loc"],
                "severity": severity(c["sev"]),
                "documents_attached": sorted(c["attach"]),
            },
            "documents_missing": [d for d in required_docs(c["lob"], c["itype"]) if d not in c["attach"]],
            "coverage": {
                "decision": c["decision"],
                "required_clause_ids": c["req"],
                "acceptable_clause_ids": c["ok"],
            },
            "cross_reference": c.get("xref", False),
            "should_refuse": c.get("refuse", False),
            "process_flaws": gold_flaws(c, events),
        })
    with open(DATA / "labels.jsonl", "w") as f:
        for row in labels:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(CLAIMS)} claims to {claims_dir} and {len(labels)} labels to data/labels.jsonl")


if __name__ == "__main__":
    main()
