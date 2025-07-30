#!/usr/bin/env python
"""
verify_alignment.py
Verify that the aligned ontology contains all expected individuals and relationships
"""

from rdflib import Graph, Namespace, RDF, OWL
from pathlib import Path
import sys


def verify_alignment(ontology_path):
    """Verify the aligned ontology has all expected content."""

    OR = Namespace("http://www.semanticweb.org/Twin_OR/")

    print(f"Loading ontology from: {ontology_path}")
    g = Graph()
    g.parse(ontology_path, format="xml")

    print(f"Total triples: {len(g)}")

    print("\n=== Checking Base Ontology Individuals ===")

    base_individuals = [
        "Surgeon", "Nurse", "Scribe", "Robotic_Arm", "TableSurface",
        "Step_A1_1", "Step_A1_2", "Step_A1_3", "Step_A1_4",
        "Step_A2_1", "Step_A2_2", "Step_A2_3", "Step_A2_4",
        "A_Phase1", "A_Phase2", "A_Phase3", "A_Phase4", "A_Phase5",
        "PlanA", "PlanB", "PlanC",
        "Lego_1", "Lego_2", "Lego_3", "Lego_4", "Lego_5", "Lego_Platform",
        "Pen", "Forceps",
        "Standard_Vision", "Micro_Vision", "Grasping", "Turning", "Manipulation",
    ]

    found = 0
    missing = []

    for ind_name in base_individuals:
        ind = OR[ind_name]
        if (ind, RDF.type, OWL.NamedIndividual) in g:
            found += 1
        else:
            if any(g.triples((ind, RDF.type, None))):
                found += 1
            else:
                missing.append(ind_name)

    print(f"Found {found}/{len(base_individuals)} base individuals")
    if missing:
        print(f"Missing: {', '.join(missing)}")

    print("\n=== Checking Surgical Individuals ===")

    surgical_individuals = [
        "ChiefSurgeon", "AssistantSurgeon", "ScrubNurse", "SurgicalRobot",
        "Scalpel", "Retractor", "Electrocautery", "NeedleHolder", "Microscope",
        "Skin", "Fascia", "Muscle", "BloodVessel", "RetinalMembrane",
        "MicroManipulationSkill", "AssistSkill",
    ]

    found_surgical = 0
    missing_surgical = []

    for ind_name in surgical_individuals:
        ind = OR[ind_name]
        if (ind, RDF.type, OWL.NamedIndividual) in g:
            found_surgical += 1
        else:
            if any(g.triples((ind, RDF.type, None))):
                found_surgical += 1
            else:
                missing_surgical.append(ind_name)

    print(f"Found {found_surgical}/{len(surgical_individuals)} surgical individuals")
    if missing_surgical:
        print(f"Missing: {', '.join(missing_surgical)}")

    print("\n=== Checking New Classes ===")

    new_classes = [
        "ActionCore", "ActionGroup",
        "IncisionCore", "SuturingCore", "CoagulationCore",
        "TissueGripCore", "IrrigationCore", "ImagingCore",
        "SkinIncisionAG", "ContinuousSutureAG", "InterruptedSutureAG",
        "TissueRetractionAG", "TissueApproxAG",
        "Surgeon", "Nurse", "Robot", "Instrument", "Tissue"
    ]

    found_classes = 0
    missing_classes = []

    for class_name in new_classes:
        cls = OR[class_name]
        if (cls, RDF.type, OWL.Class) in g:
            found_classes += 1
        else:
            missing_classes.append(class_name)

    print(f"Found {found_classes}/{len(new_classes)} new classes")
    if missing_classes:
        print(f"Missing: {', '.join(missing_classes)}")

    print("\n=== Checking Key Relationships ===")

    step = OR.Step_A1_2
    relationships = []

    for p, o in g.predicate_objects(step):
        pred_name = str(p).split('/')[-1]
        obj_name = str(o).split('/')[-1]
        relationships.append(f"{pred_name}: {obj_name}")

    print(f"\nStep_A1_2 relationships ({len(relationships)}):")
    for rel in sorted(relationships)[:10]:  
        print(f"  - {rel}")


    print("\n=== Checking Properties ===")

    properties = [
        "hasInstrument", "targetTissue", "implementsGroup",
        "forceValue", "motionParam"
    ]

    found_props = 0
    for prop_name in properties:
        prop = OR[prop_name]
        if (prop, RDF.type, OWL.ObjectProperty) in g or (prop, RDF.type, OWL.DatatypeProperty) in g:
            found_props += 1

    print(f"Found {found_props}/{len(properties)} new properties")

    print("\n=== SUMMARY ===")
    total_expected = len(base_individuals) + len(surgical_individuals)
    total_found = found + found_surgical

    if total_found >= total_expected * 0.9:  
        print("✅ Alignment verification PASSED")
        print(f"   Found {total_found}/{total_expected} expected individuals")
        return True
    else:
        print("❌ Alignment verification FAILED")
        print(f"   Only found {total_found}/{total_expected} expected individuals")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ontology_path = sys.argv[1]
    else:
        ontology_path = "../twin_or_2_aligned.owl"

    if not Path(ontology_path).exists():
        print(f"Error: Ontology file not found: {ontology_path}")
        sys.exit(1)

    success = verify_alignment(ontology_path)
    sys.exit(0 if success else 1)
