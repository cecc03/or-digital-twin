import os
import traceback
from threading import Lock
from datetime import datetime

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from OR_simulator import ORSimulator
import queries

app = Flask(__name__)
CORS(app)

_sim_lock = Lock()
_sim = None
_validation_details = {"conforms": True, "violations": [], "report": ""}


def find_file(filename, search_paths):
    """Find a file in multiple possible locations."""
    for path in search_paths:
        if os.path.exists(path):
            return path
    return None


def _snapshot():
    """Return complete simulator state."""
    if _sim is None:
        return {"error": "Simulator not initialized"}

    return {
        "plan": _sim.current_plan,
        "phase": _sim.current_phase,
        "steps": _sim.current_steps,
        "procedure": _sim.current_procedure,
        "violation": _sim.violation_occurred,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "validationDetails": _validation_details,
        "ongoing": _sim.ongoing_procedure,
        "availableProcedures": list(_sim.procedures.keys()) if _sim else []
    }


@app.route('/')
def index():
    """Serve the main page."""
    web_path = os.path.join(os.path.dirname(__file__), 'web', 'index.html')
    if os.path.exists(web_path):
        return send_file(web_path)
    else:
        current_dir_path = os.path.join(os.path.dirname(__file__), 'index.html')
        if os.path.exists(current_dir_path):
            return send_file(current_dir_path)
        else:
            return f"Error: index.html not found. Looked in {web_path} and {current_dir_path}", 404


@app.route('/init', methods=['POST'])
def api_init():
    """Initialize the simulator."""
    global _sim, _validation_details

    data = request.get_json() or {}
    initial_procedure = data.get('procedure', 'LegoAssembly')

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    ontology_path = find_file('twin_or_2_aligned.owl', [
        os.path.join(BASE_DIR, 'alignments', 'twin_or_2_aligned.owl'),
        os.path.join(BASE_DIR, '..', 'alignments', 'twin_or_2_aligned.owl'),
        os.path.join(BASE_DIR, 'twin_or_2_aligned.owl'),
        'alignments/twin_or_2_aligned.owl',
        'twin_or_2_aligned.owl'
    ])

    shacl_path = find_file('SHACL_constraints.ttl', [
        os.path.join(BASE_DIR, 'ontologies', 'SHACL_constraints.ttl'),
        os.path.join(BASE_DIR, '..', 'ontologies', 'SHACL_constraints.ttl'),
        os.path.join(BASE_DIR, 'SHACL_constraints.ttl'),
        'ontologies/SHACL_constraints.ttl',
        'SHACL_constraints.ttl'
    ])

    sensor_path = find_file('sensor_data.json', [
        os.path.join(BASE_DIR, 'data', 'sensor_data.json'),
        os.path.join(BASE_DIR, '..', 'data', 'sensor_data.json'),
        os.path.join(BASE_DIR, 'sensor_data.json'),
        'data/sensor_data.json',
        'sensor_data.json'
    ])

    if not all([ontology_path, shacl_path, sensor_path]):
        missing = []
        if not ontology_path: missing.append("ontology")
        if not shacl_path: missing.append("SHACL constraints")
        if not sensor_path: missing.append("sensor data")
        return jsonify({"error": f"Missing files: {', '.join(missing)}"}), 400

    try:
        with _sim_lock:
            _sim = ORSimulator(
                ontology_path,
                shacl_path,
                sensor_path,
                show_validation_report=True,
                initial_procedure=initial_procedure
            )

            conforms = _sim.validate_current_state_with_shacl()
            _validation_details = _sim.get_validation_details() if hasattr(_sim, 'get_validation_details') else {
                "conforms": conforms,
                "violations": [],
                "report": "Initial state valid" if conforms else "Initial validation failed"
            }

        return jsonify(_snapshot())

    except Exception as e:
        print(f"Error initializing: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/switch-procedure', methods=['POST'])
def api_switch_procedure():
    """Switch to a different procedure."""
    global _validation_details

    if _sim is None:
        return jsonify({"error": "Simulator not initialized"}), 400

    data = request.get_json() or {}
    procedure = data.get('procedure')

    if not procedure:
        return jsonify({"error": "No procedure specified"}), 400

    try:
        with _sim_lock:
            if _sim.switch_procedure(procedure):
                conforms = _sim.validate_current_state_with_shacl()
                _validation_details = _sim.get_validation_details() if hasattr(_sim, 'get_validation_details') else {
                    "conforms": conforms,
                    "violations": [],
                    "report": ""
                }
                return jsonify(_snapshot())
            else:
                return jsonify({"error": f"Unknown procedure: {procedure}"}), 400

    except Exception as e:
        print(f"Error switching procedure: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/step', methods=['POST'])
def api_step():
    """Execute one simulation step."""
    global _validation_details

    if _sim is None:
        return jsonify({"error": "Simulator not initialized"}), 400

    try:
        with _sim_lock:
            _sim.simulate_robotic_sensor_output_and_update_ontology()

            
            conforms = _sim.validate_current_state_with_shacl()
            _validation_details = _sim.get_validation_details() if hasattr(_sim, 'get_validation_details') else {
                "conforms": conforms,
                "violations": [],
                "report": ""
            }

            if 'violations' in _validation_details:
                for violation in _validation_details['violations']:
                    focus_node = violation.get('focusNode', '')
                    if hasattr(_sim, 'sensor_data') and focus_node in _sim.sensor_data:
                        violation['sensor_message'] = _sim.sensor_data[focus_node].get('message', '')

            _sim.violation_occurred = not conforms

            if conforms:
                next_steps = _sim.get_next_steps()
                if next_steps:
                    _sim.current_steps = next_steps
                else:
                    if not _sim.advance_to_next_phase():
                        _sim.ongoing_procedure = False

        return jsonify(_snapshot())

    except Exception as e:
        print(f"Error in step: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/state', methods=['GET'])
def api_state():
    """Get current state."""
    if _sim is None:
        return jsonify({"error": "Simulator not initialized"}), 400
    return jsonify(_snapshot())


@app.route('/question', methods=['POST'])
def api_question():
    """Handle questions about the procedure."""
    if _sim is None:
        return jsonify({"error": "Simulator not initialized"}), 400

    data = request.get_json() or {}
    question_type = data.get('question', '')

    try:
        answer = "I can help with questions about instruments, actors, tissues, and capabilities."

        from ontology_utils import query_result_to_list

        if "instrument" in question_type:
            if hasattr(queries, 'get_instruments_for_steps'):
                query = queries.get_instruments_for_steps(_sim.current_steps)
                result = _sim.or_graph.query(query)
                instruments = []
                for row in result:
                    if row[0]:  
                        label = str(row[0]).split('/')[-1]  
                        instruments.append(label)

                if instruments:
                    answer = f"Instruments needed: {', '.join(instruments)}"
                else:
                    answer = "No specific instruments required for current steps"
            else:
                answer = "Instrument query not available"

        elif "actor" in question_type:
            if hasattr(queries, 'get_actors_for_steps'):
                query = queries.get_actors_for_steps(_sim.current_steps)
                result = _sim.or_graph.query(query)
                actors = []
                for row in result:
                    if row[0]:
                        label = str(row[0]).split('/')[-1]
                        actors.append(label)

                if actors:
                    answer = f"Actors required: {', '.join(actors)}"
                else:
                    answer = "No specific actors identified"
            else:
                answer = "Actor query not available"

        elif "tissue" in question_type:
            if hasattr(queries, 'get_target_tissues_for_steps'):
                query = queries.get_target_tissues_for_steps(_sim.current_steps)
                result = _sim.or_graph.query(query)
                tissues = []
                for row in result:
                    if row[0]:
                        label = str(row[0]).split('/')[-1]
                        tissues.append(label)

                if tissues:
                    answer = f"Target tissues: {', '.join(tissues)}"
                else:
                    answer = "No target tissues specified"
            else:
                answer = "Tissue query not available"

        elif "capability" in question_type:
            if hasattr(queries, 'get_capabilities_for_steps'):
                query = queries.get_capabilities_for_steps(_sim.current_steps)
                result = _sim.or_graph.query(query)
                capabilities = []
                for row in result:
                    if row[0]:
                        label = str(row[0]).split('/')[-1]
                        capabilities.append(label)

                if capabilities:
                    answer = f"Required capabilities: {', '.join(capabilities)}"
                else:
                    answer = "Standard capabilities sufficient"
            else:
                answer = "Capability query not available"

        return jsonify({"answer": answer})

    except Exception as e:
        print(f"Question error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("OR Digital Twin Web Server")
    print("=" * 60)
    print("Server will start at: http://localhost:5000")
    print("")
    print("Access the application at:")
    print("  http://localhost:5000/")
    print("")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5000, debug=True)
