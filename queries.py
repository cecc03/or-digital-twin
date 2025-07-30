# queries.py
from rdflib import Graph

def get_all_instruments() -> str:
    """Get all instruments used in steps."""
    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?instrument WHERE {
        { ?step twin:hasInstrument ?instrument }
        UNION
        { ?step twin:toolUsed ?instrument }
    } LIMIT 100
    """


def get_all_steps() -> str:
    """Retrieve all steps."""
    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT ?step WHERE {
        ?step a twin:Step .
    } LIMIT 100
    """


def get_actors_with_capability(capability: str) -> str:
    """Get actors with specific capability."""
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?actor WHERE {{
        ?actor twin:hasCapability twin:{capability} .
    }} LIMIT 100
    """


def get_action_groups_for_core(core_type: str) -> str:
    """Get action groups for a specific core type."""
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?group WHERE {{
        ?group rdfs:subClassOf twin:{core_type} .
        ?group rdfs:subClassOf twin:ActionGroup .
    }} LIMIT 100
    """


def get_instruments_for_steps(steps: list[str]) -> str:
    """Get instruments required for given steps - checking both hasInstrument and toolUsed."""
    if not steps:
        return """
        PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
        SELECT DISTINCT ?instrument WHERE {
            FILTER(false)
        }
        """

    step_unions = []
    for step in steps:
        step_uri = f'twin:{step.replace(" ", "_")}'
        step_unions.append(f"""
        {{
            {step_uri} twin:hasInstrument ?instrument
        }}
        UNION
        {{
            {step_uri} twin:toolUsed ?instrument
        }}""")

    union_query = " UNION ".join(step_unions)

    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?instrument WHERE {{
        {union_query}
    }} LIMIT 100
    """


def get_target_tissues_for_steps(steps: list[str]) -> str:
    """Get target tissues for given steps."""
    if not steps:
        return """
        PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
        SELECT DISTINCT ?tissue WHERE {
            FILTER(false)
        }
        """

    # Create SPARQL for multiple steps
    step_unions = []
    for step in steps:
        step_uri = f'twin:{step.replace(" ", "_")}'
        step_unions.append(f"{{ {step_uri} twin:targetTissue ?tissue }}")

    union_query = " UNION ".join(step_unions)

    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?tissue WHERE {{
        {union_query}
    }} LIMIT 100
    """


def get_actors_for_steps(steps: list[str]) -> str:
    """Get actors performing given steps - checking multiple properties."""
    if not steps:
        return """
        PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
        SELECT DISTINCT ?actor WHERE {
            FILTER(false)
        }
        """

    step_unions = []
    for step in steps:
        step_uri = f'twin:{step.replace(" ", "_")}'
        step_unions.append(f"""
        {{
            {step_uri} prov:wasAssociatedWith ?actor
        }}
        UNION
        {{
            {step_uri} twin:performedBy ?actor
        }}
        UNION
        {{
            {step_uri} twin:performer ?actor
        }}
        UNION
        {{
            {step_uri} twin:actor ?actor
        }}""")

    union_query = " UNION ".join(step_unions)

    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT DISTINCT ?actor WHERE {{
        {union_query}
    }} LIMIT 100
    """


def get_capabilities_for_steps(steps: list[str]) -> str:
    """Get capabilities required for given steps."""
    if not steps:
        return """
        PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
        SELECT DISTINCT ?capability WHERE {
            FILTER(false)
        }
        """

    # Create SPARQL for multiple steps
    step_unions = []
    for step in steps:
        step_uri = f'twin:{step.replace(" ", "_")}'
        step_unions.append(f"{{ {step_uri} twin:requiresCapability ?capability }}")

    union_query = " UNION ".join(step_unions)

    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?capability WHERE {{
        {union_query}
    }} LIMIT 100
    """


def get_action_group_for_step(step: str) -> str:
    """Get the action group implemented by a step."""
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?group WHERE {{
        twin:{step} twin:implementsGroup ?group .
    }} LIMIT 10
    """


def get_force_value_for_step(step: str) -> str:
    """Get force value for a step."""
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT ?force WHERE {{
        twin:{step} twin:forceValue ?force .
    }} LIMIT 1
    """


def get_motion_params_for_step(step: str) -> str:
    """Get motion parameters for a step."""
    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT ?motion WHERE {{
        twin:{step} twin:motionParam ?motion .
    }} LIMIT 1
    """


def get_tools_for_steps(steps: list[str]) -> str:
    """Wrapper for backward compatibility - tools are now instruments."""
    return get_instruments_for_steps(steps)


def get_materials_for_steps(steps: list[str]) -> str:
    """Get materials - checking materialUsed property."""
    if not steps:
        return """
        PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
        SELECT DISTINCT ?material WHERE {
            FILTER(false)
        }
        """

    step_unions = []
    for step in steps:
        step_uri = f'twin:{step.replace(" ", "_")}'
        step_unions.append(f"{{ {step_uri} twin:materialUsed ?material }}")

    union_query = " UNION ".join(step_unions)

    return f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?material WHERE {{
        {union_query}
    }} LIMIT 100
    """


def get_next_steps(current_steps: list[str]) -> str:
    """Simple next step logic - in real implementation would use ontology relationships."""
    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT DISTINCT ?next_step WHERE {
        ?next_step a twin:Step .
    } LIMIT 1
    """


def get_phase_start_step(phase: str) -> str:
    """Get starting steps for a phase."""
    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT ?step WHERE {
        ?step a twin:Step .
    } LIMIT 1
    """


def is_final_phase(current_phase: str) -> str:
    """Check if current phase is final."""
    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    ASK WHERE {
        # Simplified - always returns false for demo
        FILTER(false)
    }
    """


def get_next_phase_and_phase_order_no(current_phase: str, current_plan: str) -> str:
    """Get next phase - simplified for demo."""
    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX twin: <http://www.semanticweb.org/Twin_OR/>
    SELECT ?next_phase WHERE {
        # Simplified - returns nothing to trigger phase advance in simulator
        FILTER(false)
    } LIMIT 1
    """
