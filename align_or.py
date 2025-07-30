#!/usr/bin/env python
"""
align_or_local.py
────────────────────────────────────────────────────────────
Creates a stand-alone alignment ontology that links the
Twin-OR surgery ontology to local copies of PROV-O and the
Hybrid-Intelligence (HI) ontology.

⮞ Inputs
    • --onto   : path to the base OWL file (default: twin_or_2.owl)
    • --refdir : folder with prov-o.ttl and hi.ttl
    • --out    : output .owl path (will be created)

The script:
  1. loads the base ontology (with Owlready2 reasoning),
  2. creates alignment axioms linking to PROV-O and HI,
  3. adds import statements for the reference ontologies,
  4. writes the result as a separate OWL file.

"""
import argparse
import logging
import sys
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, URIRef, Literal
from ontology_utils import load_and_materialize_ontology


def parse_arguments() -> argparse.Namespace:
    ROOT = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(description="Create OR alignment ontology")

    parser.add_argument(
        "--onto",
        type=Path,
        default=ROOT / "ontologies" / "twin_or_2.owl",
        help="base OR ontology (.owl)",
    )
    parser.add_argument(
        "--refdir",
        type=Path,
        default=ROOT / "ontologies",
        help="folder that contains prov-o.ttl and hi.ttl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "alignments" / "twin_or_2_aligned.owl",
        help="output alignment OWL file",
    )

    return parser.parse_args()


def create_action_core_classes(g_align, align_ns, OR, HI):
    """Create action core classes in OR namespace."""
    core_classes = [
        "IncisionCore", "TissueGripCore", "SuturingCore",
        "CoagulationCore", "IrrigationCore", "ImagingCore"
    ]

    # First declare ActionCore as a class in OR namespace
    g_align.add((OR.ActionCore, RDF.type, OWL.Class))
    g_align.add((OR.ActionCore, RDFS.subClassOf, HI.ProcessingTask))

    # Then create the specific core classes
    for cls_name in core_classes:
        g_align.add((OR[cls_name], RDF.type, OWL.Class))
        g_align.add((OR[cls_name], RDFS.subClassOf, OR.ActionCore))
        g_align.add((OR[cls_name], RDFS.subClassOf, HI.ProcessingTask))


def create_action_group_classes(g_align, align_ns, OR):
    """Create action group classes in OR namespace."""
    g_align.add((OR.ActionGroup, RDF.type, OWL.Class))
    g_align.add((OR.ActionGroup, RDFS.subClassOf, OR.ActionCore))

    group_mappings = [
        ("SkinIncisionAG", "IncisionCore"),
        ("VesselOpeningAG", "IncisionCore"),
        ("MembraneFenestrateAG", "IncisionCore"),
        ("TissueRetractionAG", "TissueGripCore"),
        ("TissueApproxAG", "TissueGripCore"),
        ("InterruptedSutureAG", "SuturingCore"),
        ("ContinuousSutureAG", "SuturingCore"),
        ("SpotCauteryAG", "CoagulationCore"),
        ("LineCoagulationAG", "CoagulationCore"),
    ]

    for group_name, parent_core in group_mappings:
        g_align.add((OR[group_name], RDF.type, OWL.Class))
        g_align.add((OR[group_name], RDFS.subClassOf, OR[parent_core]))
        g_align.add((OR[group_name], RDFS.subClassOf, OR.ActionGroup))


def create_properties(g_align, align_ns, OR, PROV):
    """Create properties for action cores."""
    object_props = [
        ("hasInstrument", OR.ActionCore, OR.Instrument),
        ("targetTissue", OR.ActionCore, OR.Tissue),
        ("implementsGroup", OR.Step, OR.ActionGroup),
    ]

    for prop_name, domain, range_cls in object_props:
        prop = OR[prop_name]
        g_align.add((prop, RDF.type, OWL.ObjectProperty))
        g_align.add((prop, RDFS.domain, domain))
        g_align.add((prop, RDFS.range, range_cls))
        g_align.add((prop, RDFS.subPropertyOf, PROV.used))

    datatype_props = [
        ("motionParam", OR.ActionCore, XSD.string),
        ("forceValue", OR.ActionCore, XSD.float),
    ]

    for prop_name, domain, range_type in datatype_props:
        prop = OR[prop_name]
        g_align.add((prop, RDF.type, OWL.DatatypeProperty))
        g_align.add((prop, RDFS.domain, domain))
        g_align.add((prop, RDFS.range, range_type))


def add_class_alignments(g_align, align_ns, OR, PROV, HI):
    """Add class alignment axioms."""
    alignments = [
        (OR.Surgeon, HI.Actor),
        (OR.Nurse, HI.Actor),
        (OR.Robot, HI.Actor),

        (OR.Step, HI.ProcessingTask),
        (OR.Step, PROV.Activity),
        (OR.InteractionStep, HI.InteractionTask),
        (OR.Phase, PROV.Activity),

        (OR.Tool, PROV.Entity),
        (OR.Instrument, PROV.Entity),
        (OR.Tissue, PROV.Entity),
        (OR.Tissue, HI.PhysicalObject),
        (OR.Patient, PROV.Entity),
        (OR.Parameter, PROV.Entity),
    ]

    for source, target in alignments:
        g_align.add((source, RDFS.subClassOf, target))


def add_property_alignments(g_align, align_ns, OR, PROV, HI):
    """Add property alignment axioms."""
    subprop_alignments = [
        (OR.performedBy, PROV.wasAssociatedWith),
        (OR.consumes, PROV.used),
        (OR.produces, PROV.wasGeneratedBy),
        (OR.hasActionGroup, PROV.qualifiedAssociation),
        (OR.hasParameter, PROV.used),
        (OR.hasCapability, HI.hasCapability),
    ]

    for source, target in subprop_alignments:
        g_align.add((source, RDFS.subPropertyOf, target))

    equiv_alignments = [
        (OR.usesInstrument, PROV.used),
        (OR.consumesMaterial, PROV.used),
        (OR.producesOutcome, PROV.generated),
        (OR.generatesImage, PROV.generated),
        (OR.followsStep, PROV.wasInformedBy),
        (OR.hasPrecondition, PROV.wasDerivedFrom),
    ]

    for source, target in equiv_alignments:
        g_align.add((source, OWL.equivalentProperty, target))


def add_capability_instances(g_align, align_ns, OR, HI):
    """Add capability instances and relationships."""
    capabilities = ["MicroManipulationSkill", "AssistSkill"]
    for cap in capabilities:
        g_align.add((OR[cap], RDF.type, HI.Capability))

    capability_triples = [
        (OR.Surgeon, HI.hasCapability, OR.MicroManipulationSkill),
        (OR.Nurse, HI.hasCapability, OR.AssistSkill),
        (OR.Robot, HI.hasCapability, OR.MicroManipulationSkill),
    ]

    for subject, predicate, obj in capability_triples:
        g_align.add((subject, predicate, obj))


def main():
    """Main execution function."""
    args = parse_arguments()
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    OR = Namespace("http://www.semanticweb.org/Twin_OR/")
    PROV = Namespace("http://www.w3.org/ns/prov#")
    HI = Namespace("http://www.semanticweb.org/vbr240/ontologies/2022/4/untitled-ontology-51/")

    base_path = args.onto.resolve()
    g_base = load_and_materialize_ontology(str(base_path), OR, "or")
    logging.info("Loaded base ontology: %s", base_path)

    ALIGN_BASE = "http://www.semanticweb.org/Twin_OR_2_alignment"
    ALIGN_NS = Namespace(ALIGN_BASE + "#")
    ALIGN_IRI = URIRef(ALIGN_BASE)

    g_align = Graph()

    g_align.bind("", ALIGN_NS)  # Default namespace
    g_align.bind("align", ALIGN_NS)
    g_align.bind("or", OR)
    g_align.bind("prov", PROV)
    g_align.bind("hi", HI)
    g_align.bind("owl", OWL)
    g_align.bind("rdfs", RDFS)
    g_align.bind("rdf", RDF)
    g_align.bind("xsd", XSD)

    g_align.add((ALIGN_IRI, RDF.type, OWL.Ontology))
    g_align.add((ALIGN_IRI, RDFS.label, Literal("Twin-OR Alignment Ontology")))
    g_align.add((ALIGN_IRI, RDFS.comment,
                 Literal("Alignment ontology linking Twin-OR to PROV-O and HI ontologies")))

    refdir = args.refdir.resolve()

    prov_file = refdir / "prov-o.ttl"
    hi_file = refdir / "hi.ttl"

    if not prov_file.exists():
        logging.error("PROV-O ontology missing: %s", prov_file)
        sys.exit(1)
    if not hi_file.exists():
        logging.error("HI ontology missing: %s", hi_file)
        sys.exit(1)

    prov_iri = URIRef("http://www.w3.org/ns/prov-o#")
    hi_iri = URIRef(str(hi_file.as_uri()))

    g_align.add((ALIGN_IRI, OWL.imports, prov_iri))
    g_align.add((ALIGN_IRI, OWL.imports, hi_iri))

    logging.info("Added import statements for reference ontologies")

    create_action_core_classes(g_align, ALIGN_NS, OR, HI)
    create_action_group_classes(g_align, ALIGN_NS, OR)
    create_properties(g_align, ALIGN_NS, OR, PROV)
    add_class_alignments(g_align, ALIGN_NS, OR, PROV, HI)
    add_property_alignments(g_align, ALIGN_NS, OR, PROV, HI)
    add_capability_instances(g_align, ALIGN_NS, OR, HI)

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    g_align.serialize(
        destination=out_path,
        format="pretty-xml",
        base=ALIGN_BASE
    )

    logging.info("Alignment ontology written to %s with base IRI: %s",
                 out_path, ALIGN_BASE)


if __name__ == "__main__":
    main()
