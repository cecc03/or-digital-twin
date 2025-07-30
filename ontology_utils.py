from rdflib import Graph, Literal, Namespace, URIRef
from owlready2 import get_ontology, sync_reasoner_pellet, default_world
from rdflib.namespace import XSD, RDF, RDFS, OWL
from pathlib import Path
import logging
import platform
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OR = Namespace("http://www.semanticweb.org/Twin_OR/")
HI = Namespace("http://www.semanticweb.org/vbr240/ontologies/2022/4/untitled-ontology-51/")
PROV = Namespace("http://www.w3.org/ns/prov#")


def load_and_materialize_ontology(
        file_path: str,
        namespace: Namespace,
        prefix: str,
        *,
        format: str = "xml",
        reasoner: str = "pellet" 
) -> Graph:
    """Simply load the OWL ontology file."""
    logger.info(f"Loading ontology from: {file_path}")

    g = Graph()
    g.parse(file_path, format=format)

    g.bind(prefix, namespace)
    g.bind("twin", OR)
    g.bind("hi", HI)
    g.bind("prov", PROV)

    logger.info(f"✔ Ontology loaded with {len(g)} triples")
    return g


def parse_json_to_rdflib(json_triple: dict, namespace: Namespace):
    """Convert a JSON triple into an rdflib triple."""
    s = namespace[json_triple["subject"]]
    p_str = json_triple["predicate"]

    if ":" in p_str:
        prefix, local = p_str.split(":", 1)
        if prefix == "prov":
            p = PROV[local]
        elif prefix == "twin":
            p = namespace[local]
        else:
            p = namespace[p_str]
    else:
        p = namespace[p_str]

    o_raw = json_triple["object"]

    if isinstance(o_raw, bool):
        o = Literal(o_raw, datatype=XSD.boolean)
    elif isinstance(o_raw, (int, float)):
        o = Literal(o_raw, datatype=XSD.float if isinstance(o_raw, float) else XSD.integer)
    elif isinstance(o_raw, str) and o_raw.replace(".", "").replace("-", "").isdigit():
        try:
            if "." in o_raw:
                o = Literal(float(o_raw), datatype=XSD.float)
            else:
                o = Literal(int(o_raw), datatype=XSD.integer)
        except:
            o = namespace[o_raw]
    else:
        o = namespace[o_raw]

    return (s, p, o)


def query_result_to_list(query_result):
    """Flatten a SPARQL Result into a Python list of local names."""
    result = []
    for row in query_result:
        for cell in row:
            if cell:  
                result.append(get_label_from_uri(cell))
    return result


def get_label_from_uri(uri):
    """Return the fragment/local-name component of uri as a str."""
    if not uri:
        return ""
    return str(uri).split("/")[-1].split("#")[-1]

def validate_alignments(g: Graph) -> bool:
    """Validate that required alignments are present in the new ontology."""
    required_checks = [
        (OR.Surgeon, RDFS.subClassOf, HI.Actor),
        (OR.Nurse, RDFS.subClassOf, HI.Actor),
        (OR.Robot, RDFS.subClassOf, HI.Actor),
        (OR.ActionCore, RDFS.subClassOf, HI.ProcessingTask),

        (OR.Step, RDFS.subClassOf, PROV.Activity),
        (OR.Phase, RDFS.subClassOf, PROV.Activity),
        (OR.Instrument, RDFS.subClassOf, PROV.Entity),
        (OR.Tissue, RDFS.subClassOf, PROV.Entity),

        (OR.hasInstrument, RDFS.subPropertyOf, PROV.used),
        (OR.performedBy, RDFS.subPropertyOf, PROV.wasAssociatedWith),
    ]

    missing = []
    for s, p, o in required_checks:
        if (s, p, o) not in g:
            missing.append(f"{get_label_from_uri(s)} {get_label_from_uri(p)} {get_label_from_uri(o)}")

    if missing:
        logger.warning(f"Missing alignments: {missing}")
        return False

    logger.info("✔ All required alignments validated")
    return True
