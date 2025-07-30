# OR_simulator.py
import json
from pathlib import Path
from typing import List, Optional, Dict

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, RDFS, Literal, OWL
from rdflib.namespace import XSD

import queries
from ontology_utils import (
    load_and_materialize_ontology,
    parse_json_to_rdflib,
    get_label_from_uri,
)

OR = Namespace("http://www.semanticweb.org/Twin_OR/")
PROV = Namespace("http://www.w3.org/ns/prov#")



class ORSimulator:
    """Digital‑Twin of an OR procedure driven by an ontology + SHACL."""

    def __init__(
            self,
            ontology_path: str,
            shacl_shape_path: str,
            sensor_data_path: str = "sensor_data.json",
            *,
            show_validation_report: bool = False,
            initial_procedure: str = "LegoAssembly"
    ) -> None:
        self.input_ontology_path = ontology_path
        self.prefix = "twin"
        self.sensor_data_path = sensor_data_path
        self.show_validation_report = show_validation_report

        self.current_procedure = initial_procedure
        self.current_steps: List[str] = []
        self.current_phase = "Phase1"
        self.current_plan = initial_procedure
        self.ongoing_procedure = True
        self.violation_occurred = False
        self.step_counter = 0  # Track progression

        self.or_graph: Graph = load_and_materialize_ontology(
            ontology_path, OR, self.prefix
        )

        self._ensure_default_actors()

        self.shacl_shapes_graph = Graph().parse(shacl_shape_path)

        with open(sensor_data_path, encoding="utf-8") as fp:
            sensor_data_full = json.load(fp)
            self.procedures = sensor_data_full.get("procedures", {})
            self.sensor_data = self.procedures.get(initial_procedure, {})

        self.graph_checkpoint: Optional[Graph] = None
        self.last_valid_steps = self.current_steps.copy()
        self.last_valid_phase = self.current_phase

        self._initialize_procedure()

        self._set_initial_steps()

    def _ensure_default_actors(self):
        """Ensure required actors exist in the graph."""
        actors_to_check = [
            (OR.Surgeon, OR.Surgeon, OR.Standard_Vision), 
            (OR.Nurse, OR.Nurse, OR.Standard_Vision), 
            (OR.Robotic_Arm, OR.Actor, OR.Micro_Vision), 
            (OR.ChiefSurgeon, OR.Surgeon, OR.MicroManipulationSkill),  
            (OR.SurgicalRobot, OR.Robot, OR.MicroManipulationSkill), 
        ]

        for actor_uri, actor_type, capability in actors_to_check:
            if not any(self.or_graph.triples((actor_uri, RDF.type, None))):
                self.or_graph.add((actor_uri, RDF.type, actor_type))
                self.or_graph.add((actor_uri, RDF.type, OWL.NamedIndividual))
                if capability:
                    self.or_graph.add((actor_uri, OR.hasCapability, capability))

    def _initialize_procedure(self):
        """Initialize the current procedure in the graph."""
        proc_uri = OR[self.current_procedure]
        self.or_graph.add((proc_uri, RDF.type, OR.SurgicalProcedure))
        self.or_graph.add((proc_uri, RDFS.label, Literal(self.current_procedure)))

    def _set_initial_steps(self):
        """Set initial steps based on procedure type."""
        initial_steps_map = {
            "LegoAssembly": ["Step_A1_1"],
            "LaparoscopicProcedure": ["Step_L1_1"],
            "MicrosurgicalProcedure": ["Step_M1_1"],
            "RoboticProcedure": ["Step_R1_1"]
        }
        self.current_steps = initial_steps_map.get(self.current_procedure, ["Step_A1_1"])
        self.step_counter = 0

    def switch_procedure(self, procedure_name: str) -> bool:
        """Switch to a different procedure."""
        if procedure_name not in self.procedures:
            return False

        self.current_procedure = procedure_name
        self.sensor_data = self.procedures[procedure_name]
        self.current_phase = "Phase1"
        self.step_counter = 0
        self.ongoing_procedure = True
        self.violation_occurred = False

        self._set_initial_steps()
        self._initialize_procedure()

        return True

    def validate_current_state_with_shacl(self) -> bool:
        """Validate current state and capture detailed error information."""
        conforms, results_graph, results_text = validate(
            data_graph=self.or_graph,
            shacl_graph=self.shacl_shapes_graph,
            inference="rdfs",
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )

        self.last_validation_report = results_text
        self.last_validation_graph = results_graph
        self.validation_violations = []

        if not conforms and results_graph:
            violation_query = """
                PREFIX sh: <http://www.w3.org/ns/shacl#>
                SELECT ?focusNode ?path ?message ?value ?severity
                WHERE {
                    ?result a sh:ValidationResult ;
                        sh:focusNode ?focusNode ;
                        sh:resultMessage ?message .
                    OPTIONAL { ?result sh:resultPath ?path }
                    OPTIONAL { ?result sh:value ?value }
                    OPTIONAL { ?result sh:resultSeverity ?severity }
                }
            """

            for row in results_graph.query(violation_query):
                violation = {
                    'focusNode': str(row.focusNode).split('/')[-1] if row.focusNode else 'Unknown',
                    'path': str(row.path).split('/')[-1] if row.path else 'N/A',
                    'message': str(row.message) if row.message else 'No message',
                    'value': str(row.value) if row.value else 'N/A',
                    'severity': str(row.severity).split('#')[-1] if row.severity else 'Violation'
                }
                self.validation_violations.append(violation)

        if self.show_validation_report and not conforms:
            self._display_validation_errors()

        return bool(conforms)

    def _display_validation_errors(self):
        """Display validation errors in a formatted way."""
        print("\n" + "=" * 60)
        print("🚨 SHACL VALIDATION ERRORS DETECTED 🚨")
        print("=" * 60)

        if self.validation_violations:
            for i, v in enumerate(self.validation_violations, 1):
                print(f"{i}. Node: {v['focusNode']}")
                print(f"   Path: {v['path']}")
                print(f"   Message: {v['message']}")
                if v['value'] != 'N/A':
                    print(f"   Value: {v['value']}")
                print()

        print("=" * 60 + "\n")

    def get_validation_details(self):
        """Get structured validation details for web interface."""
        violations = getattr(self, 'validation_violations', [])
        return {
            "conforms": len(violations) == 0,
            "violations": violations,
            "report": self.last_validation_report if hasattr(self, 'last_validation_report') else ""
        }

    def simulate_robotic_sensor_output_and_update_ontology(self) -> None:
        """Apply sensor triples for current steps."""
        self.graph_checkpoint = Graph()
        for s, p, o in self.or_graph:
            self.graph_checkpoint.add((s, p, o))

        for step_id in self.current_steps:
            step_data = self.sensor_data.get(step_id)
            if not step_data:
                continue

            for triple_data in step_data.get("triples", []):
                triple = parse_json_to_rdflib(triple_data, OR)
                if step_data.get("action", "add") == "add":
                    self.or_graph.add(triple)
                else:
                    self.or_graph.remove(triple)

    def get_next_steps(self) -> List[str]:
        """Get next steps based on current procedure and progression."""
        step_sequences = {
            "LegoAssembly": [
                ["Step_A1_1"], ["Step_A1_2"], ["Step_A2_1"], ["Step_A2_2"],
                ["Step_A2_3"], ["Step_A3_1"], ["Step_A3_2"], ["Step_A4_1"],
                ["Step_A4_2"], ["Step_A4_3"], ["Step_A4_4"], ["Step_A5_1"], ["Step_A5_2"]
            ],
            "LaparoscopicProcedure": [
                ["Step_L1_1"], ["Step_L1_2"], ["Step_L2_1"], ["Step_L2_2"],
                ["Step_L3_1"], ["Step_L3_2"], ["Step_L3_3"]
            ],
            "MicrosurgicalProcedure": [
                ["Step_M1_1"], ["Step_M1_2"], ["Step_M2_1"], ["Step_M2_2"],
                ["Step_M3_1"], ["Step_M3_2"]
            ],
            "RoboticProcedure": [
                ["Step_R1_1"], ["Step_R1_2"], ["Step_R2_1"], ["Step_R2_2"],
                ["Step_R2_3"], ["Step_R3_1"]
            ]
        }

        sequence = step_sequences.get(self.current_procedure, [])

        self.step_counter += 1

        if self.step_counter < len(sequence):
            return sequence[self.step_counter]

        return []

    def advance_to_next_phase(self) -> bool:
        """Advance to next phase based on procedure type."""
        phase_map = {
            "LegoAssembly": {
                "Phase1": ("Phase2", 4), 
                "Phase2": ("Phase3", 7), 
                "Phase3": ("Phase4", 10), 
                "Phase4": ("Phase5", 13),  
                "Phase5": (None, -1)
            },
            "LaparoscopicProcedure": {
                "Phase1": ("Phase2", 2),  
                "Phase2": ("Phase3", 5), 
                "Phase3": (None, -1)
            },
            "MicrosurgicalProcedure": {
                "Phase1": ("Phase2", 2), 
                "Phase2": ("Phase3", 4),  
                "Phase3": (None, -1)
            },
            "RoboticProcedure": {
                "Phase1": ("Phase2", 2), 
                "Phase2": ("Phase3", 5), 
                "Phase3": (None, -1)
            }
        }

        procedure_phases = phase_map.get(self.current_procedure, {})
        current_phase_info = procedure_phases.get(self.current_phase, (None, -1))

        next_phase, step_threshold = current_phase_info


        if next_phase and self.step_counter >= step_threshold:
            self.current_phase = next_phase
            return True
        elif not next_phase:

            self.ongoing_procedure = False
            return False

        return True

    def run_simulation(self) -> None:
        """Main simulation loop."""
        print("\n" + "=" * 60)
        print("OR DIGITAL TWIN SIMULATION")
        print("=" * 60)
        print(f"Current Procedure: {self.current_procedure}")
        print("Controls:")
        print("- Press Enter to advance")
        print("- Press 'p' to switch procedure")
        print("- Press 'q' to quit")
        print("=" * 60 + "\n")

        # Initial validation
        print("Performing initial validation…")
        if not self.validate_current_state_with_shacl():
            print("❌ Initial state validation failed!")
        else:
            print("✅ Initial validation passed\n")

        while self.ongoing_procedure:
            print(f"\n Procedure: {self.current_procedure}")
            print(f" Phase: {self.current_phase}")
            print(f" Steps: {', '.join(self.current_steps)}")

            user_input = input("\nPress Enter to continue, 'p' to switch procedure, 'q' to quit: ").strip().lower()

            if user_input == 'q':
                break
            elif user_input == 'p':
                print("\nAvailable procedures:")
                for i, proc in enumerate(self.procedures.keys(), 1):
                    print(f"{i}. {proc}")

                try:
                    choice = int(input("Select procedure number: ")) - 1
                    proc_names = list(self.procedures.keys())
                    if 0 <= choice < len(proc_names):
                        if self.switch_procedure(proc_names[choice]):
                            print(f"✅ Switched to {proc_names[choice]}")
                            continue
                except ValueError:
                    print("Invalid selection")
                    continue

            # Apply sensor updates
            print("\n🔄 Applying sensor updates...")
            self.simulate_robotic_sensor_output_and_update_ontology()

            # Validate
            print("🔍 Validating...")
            if not self.validate_current_state_with_shacl():
                print("\n❌ VALIDATION FAILED!")

                # Show sensor messages
                for step_id in self.current_steps:
                    if step_id in self.sensor_data:
                        print(f"\n⚠️  {step_id}: {self.sensor_data[step_id].get('message', '')}")

                if input("\nContinue anyway? (y/n): ").lower() != 'y':
                    break
            else:
                print("✅ Validation passed!")

                # Advance
                next_steps = self.get_next_steps()
                if next_steps:
                    self.current_steps = next_steps
                    print(f"➡️  Advanced to: {', '.join(next_steps)}")

                    # Check if we should advance phase
                    self.advance_to_next_phase()
                else:
                    if not self.advance_to_next_phase():
                        print("\n🎉 Procedure completed!")

        print("\n✅ Simulation ended!")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    here = Path(__file__).parent
    sim = ORSimulator(
        ontology_path=here / "twin_or_2_aligned.owl",
        shacl_shape_path=here / "SHACL_constraints.ttl",
        sensor_data_path=here / "sensor_data.json",
        show_validation_report=True,
    )
    sim.run_simulation()
