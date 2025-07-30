#!/usr/bin/env python
"""
run.py - Fixed for Windows file paths
Creates a complete alignment ontology that links the Twin-OR surgery ontology
to PROV-O and HI ontologies.
"""
import argparse
import logging
import sys
import platform
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, URIRef, Literal, BNode
from ontology_utils import load_and_materialize_ontology


def parse_arguments():
    """Parse command line arguments."""
    ROOT = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Create OR alignment ontology")
    parser.add_argument(
        "--onto",
        type=Path,
        default=ROOT / "twin_or_2.owl",
        help="base OR ontology (.owl)"
    )
    parser.add_argument(
        "--refdir",
        type=Path,
        default=ROOT / "ontologies",
        help="folder with prov-o.ttl and hi.ttl"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "alignments" / "twin_or_2_aligned.owl",
        help="output alignment OWL file"
    )
    return parser.parse_args()


def copy_individuals_from_base(g_base, g_align, OR):
    """Copy all individuals from base ontology to alignment ontology."""
    logging.info("Copying individuals from base ontology...")

    query = """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT DISTINCT ?individual
    WHERE {
        ?individual rdf:type ?type .
        ?individual rdf:type owl:NamedIndividual .
    }
    """

    individuals = set()
    for row in g_base.query(query):
        individuals.add(row.individual)

    copied_count = 0
    for ind in individuals:
        for p, o in g_base.predicate_objects(ind):
            g_align.add((ind, p, o))
            copied_count += 1

        for s, p in g_base.subject_predicates(ind):
            if (s, p, ind) not in g_align:
                g_align.add((s, p, ind))
                copied_count += 1

    logging.info(f"Copied {len(individuals)} individuals with {copied_count} triples")
    return individuals


def create_action_core_classes(g_align, align_ns, OR, HI):
    """Create action core classes in OR namespace."""
    core_classes = [
        "IncisionCore", "TissueGripCore", "SuturingCore",
        "CoagulationCore", "IrrigationCore", "ImagingCore"
    ]

    g_align.add((OR.ActionCore, RDF.type, OWL.Class))
    g_align.add((OR.ActionCore, RDFS.subClassOf, HI.ProcessingTask))

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
    g_align.add((OR.Surgeon, RDF.type, OWL.Class))
    g_align.add((OR.Nurse, RDF.type, OWL.Class))
    g_align.add((OR.Robot, RDF.type, OWL.Class))
    g_align.add((OR.Instrument, RDF.type, OWL.Class))
    g_align.add((OR.Tissue, RDF.type, OWL.Class))
    g_align.add((OR.Patient, RDF.type, OWL.Class))
    g_align.add((OR.InteractionStep, RDF.type, OWL.Class))

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
    capabilities = ["MicroManipulationSkill", "AssistSkill", "VisionCapability", "PrecisionGraspingSkill"]
    for cap in capabilities:
        g_align.add((OR[cap], RDF.type, HI.Capability))
        g_align.add((OR[cap], RDF.type, OWL.NamedIndividual))

    capability_triples = [
        (OR.Surgeon, HI.hasCapability, OR.MicroManipulationSkill),
        (OR.Nurse, HI.hasCapability, OR.AssistSkill),
        (OR.Robot, HI.hasCapability, OR.MicroManipulationSkill),
    ]

    for subject, predicate, obj in capability_triples:
        g_align.add((subject, predicate, obj))


def add_surgical_individuals(g_align, OR, PROV, HI):
    """Add surgical-specific individuals to demonstrate the new ontology structure."""
    logging.info("Adding surgical-specific individuals...")

    actors = [
        ("ChiefSurgeon", OR.Surgeon, [OR.MicroManipulationSkill, OR.VisionCapability]),
        ("AssistantSurgeon", OR.Surgeon, [OR.MicroManipulationSkill]),
        ("ScrubNurse", OR.Nurse, [OR.AssistSkill, OR.PrecisionGraspingSkill]),
        ("CirculatingNurse", OR.Nurse, [OR.AssistSkill]),
        ("SurgicalRobot", OR.Robot, [OR.MicroManipulationSkill, OR.PrecisionGraspingSkill]),
    ]

    for actor_name, actor_type, capabilities in actors:
        actor = OR[actor_name]
        g_align.add((actor, RDF.type, actor_type))
        g_align.add((actor, RDF.type, OWL.NamedIndividual))
        g_align.add((actor, RDF.type, HI.Actor))

        for cap in capabilities:
            g_align.add((actor, OR.hasCapability, cap))

    instruments = [
        ("Scalpel", "Cutting instrument for incisions"),
        ("Forceps", "Grasping instrument"),
        ("Retractor", "Tissue retraction instrument"),
        ("Electrocautery", "Coagulation device"),
        ("NeedleHolder", "Suturing instrument"),
        ("Microscope", "Magnification device"),
        ("LaparoscopicCamera", "Minimally invasive visualization"),
        ("RoboticArm", "Robotic manipulation device"),
    ]

    for inst_name, description in instruments:
        inst = OR[inst_name]
        g_align.add((inst, RDF.type, OR.Instrument))
        g_align.add((inst, RDF.type, OWL.NamedIndividual))
        g_align.add((inst, RDFS.comment, Literal(description)))

    tissues = [
        ("Skin", "Cutaneous tissue"),
        ("Fascia", "Connective tissue layer"),
        ("Muscle", "Muscular tissue"),
        ("BloodVessel", "Vascular tissue"),
        ("Nerve", "Neural tissue"),
        ("AbdominalWall", "Abdominal tissue layers"),
        ("RetinalMembrane", "Eye tissue"),
    ]

    for tissue_name, description in tissues:
        tissue = OR[tissue_name]
        g_align.add((tissue, RDF.type, OR.Tissue))
        g_align.add((tissue, RDF.type, OWL.NamedIndividual))
        g_align.add((tissue, RDFS.comment, Literal(description)))

    logging.info("Added surgical-specific individuals")


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

    g_align.bind("", ALIGN_NS)
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
                 Literal("Complete alignment ontology with all individuals from base plus surgical extensions")))

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

    if platform.system() == 'Windows':
        hi_iri = URIRef(hi_file.as_uri())
    else:
        hi_iri = URIRef(f"file://{hi_file}")

    g_align.add((ALIGN_IRI, OWL.imports, prov_iri))
    g_align.add((ALIGN_IRI, OWL.imports, hi_iri))

    logging.info("Added import statements for reference ontologies")

    existing_individuals = copy_individuals_from_base(g_base, g_align, OR)

    create_action_core_classes(g_align, ALIGN_NS, OR, HI)
    create_action_group_classes(g_align, ALIGN_NS, OR)
    create_properties(g_align, ALIGN_NS, OR, PROV)
    add_class_alignments(g_align, ALIGN_NS, OR, PROV, HI)
    add_property_alignments(g_align, ALIGN_NS, OR, PROV, HI)
    add_capability_instances(g_align, ALIGN_NS, OR, HI)

    add_surgical_individuals(g_align, OR, PROV, HI)

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    g_align.serialize(
        destination=out_path,
        format="pretty-xml",
        base=ALIGN_BASE
    )

    logging.info("Complete alignment ontology written to %s", out_path)
    logging.info("Total triples in alignment: %d", len(g_align))


if __name__ == "__main__":
    main()
