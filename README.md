# Operating Room Digital Twin — Surgical Procedure Simulator

An advanced Operating Room (OR) Digital Twin platform integrating semantic-web technologies (OWL, SHACL, SPARQL) with a real-time simulation engine for surgical procedure planning, validation, and training. The system accommodates tasks ranging from introductory assembly demonstrations to highly complex surgical interventions.

---

##  Core Functionality

| Capability | Description |
|------------|-------------|
| **Semantic reasoning** | Ontology-based knowledge representation with RDFS materialisation |
| **Real-time validation** | SHACL constraint evaluation of current procedural state |
| **Multi-procedure coverage** | *Lego Assembly* (demonstration), *Laparoscopic*, *Microsurgical*, and *Robotic* surgeries |
| **Interactive visualisation** | Three-js 3-D scene for assembly tasks and instrument-tracking panels for surgical modes |
| **Question–answer interface** | SPARQL-driven queries on instruments, actors, tissues, and capabilities |
| **Error-recovery loop** | Detailed SHACL violation reports supplemented by sensor-based alerts |

---

## Technical Synopsis

* **Architecture** RESTful API realised with *Flask* (Python ≥ 3.8)  
* **Knowledge base** RDF/OWL ontology aligned to PROV-O and Hybrid-Intelligence (HI) ontologies  
* **Validation** Multi-severity SHACL shapes expressing procedural constraints  
* **State management** Transactional graph checkpoints enabling rollback after violations  
* **Web interface** Single-page application (pure *HTML/JS/CSS*) with responsive layout  

---

##  Prerequisites

| Component | Minimum version |
|-----------|-----------------|
| Python | 3.8 |
| Browser | Recent Chrome, Firefox, Safari, or Edge |
| RAM | 4 GB (≥ 8 GB recommended) |

---

## 🛠 Installation Guide

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/or-digital-twin.git
cd or-digital-twin
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify installation
```bash
python -c "import rdflib, pyshacl, flask; print('All dependencies installed successfully.')"
```

---

## 🚦 Quick Start

1. **Start the server**
   ```bash
   python flask_server.py
   ```
   Default address: <http://localhost:5000>

2. **Open the web interface**  
   Navigate to `http://localhost:5000` in your browser.

3. **Initialise and run a simulation**

   | Control | Action |
   |---------|--------|
   | **🚀 Initialise System** | Load knowledge graph, SHACL shapes, and sensor scenario |
   | **▶️ Start** | Begin automatic progression |
   | **⏸ Pause** | Halt automatic progression |
   | **⏭ Single Step** | Advance a single step manually |
   | **🔄 Reset** | Re-establish initial state |
   | **❓ Questions** | Query requirements for the current step |

---

##  Project Structure
```
or-digital-twin/
├─ flask_server.py          # REST API server
├─ OR_simulator.py          # Core simulation engine
├─ ontology_utils.py        # RDF/OWL helper functions
├─ queries.py               # SPARQL templates
├─ requirements.txt         # Python dependencies
│
├─ alignments/
│  └─ twin_or_2_aligned.owl # Alignment ontology
│
├─ ontologies/
│  ├─ SHACL_constraints.ttl # Validation shapes
│  ├─ prov-o.ttl            # PROV-O vocabulary
│  └─ hi.ttl                # Hybrid-Intelligence ontology
│
├─ data/
│  └─ sensor_data.json      # Procedure scenarios
│
└─ web/
   └─ index.html            # Single-page interface
```

---

##  Configuration

### Modifying procedures  
Edit `data/sensor_data.json`:

```jsonc
{
  "procedures": {
    "YourProcedure": {
      "Step_X1_1": {
        "message": "Step description",
        "triples": [
          {
            "subject": "Step_X1_1",
            "predicate": "requiresCapability",
            "object": "YourCapability"
          }
        ],
        "action": "add"
      }
    }
  }
}
```

### Customising constraints  
Edit `ontologies/SHACL_constraints.ttl`:

```turtle
:YourShape
    a sh:NodeShape ;
    sh:targetClass :YourClass ;
    sh:property [
        sh:path :yourProperty ;
        sh:minCount 1 ;
        sh:severity sh:Violation ;
        sh:message "Your validation message" ;
    ] .
```

---

##  Usage Examples

### Command-line simulation
```bash
python OR_simulator.py
```

### API interaction (Python)
```python
import requests

# initialise
requests.post("http://localhost:5000/init",
              json={"procedure": "LaparoscopicProcedure"})

# single step
requests.post("http://localhost:5000/step")

# current state
state = requests.get("http://localhost:5000/state").json()
```

---

## 🔍 System Semantics

| Conceptual layer | Representative classes |
|------------------|------------------------|
| **Actors** | `Surgeon`, `Nurse`, `Robot` |
| **Instruments** | `Scalpel`, `Forceps`, `Microscope` |
| **Tissues** | `Skin`, `Fascia`, `Muscle` |
| **Capabilities** | `MicroManipulationSkill`, `VisionCapability` |
| **Workflow** | `Step`, `Phase`, `SurgicalProcedure` |

**Validation workflow**

1. Sensor data is ingested and translated into RDF triples.  
2. SHACL shapes evaluate the updated graph.  
3. Violations trigger alerts, pausing the simulation until resolved or acknowledged.

---

##  Troubleshooting

| Symptom | Probable cause | Remedy |
|---------|----------------|--------|
| `OSError: [Errno 98] Address already in use` | Default port 5000 occupied | Change `port` in `flask_server.py` |
| `FileNotFoundError` | Incorrect working directory | Run commands from project root |
| SHACL validation fails immediately | Missing or inconsistent triples | Enable `show_validation_report=True` in `OR_simulator.py` |
| Browser shows CORS errors | Misconfigured headers | Ensure *flask-cors* is installed and enabled |

---

##  Testing

```bash
pytest tests/
```

Manual checklist:

- System initialises without errors.  
- Procedure selection loads correct sensor scenario.  
- Missing instruments are detected by SHACL.  
- Lego assembly renders in 3-D scene.  
- Q&A interface returns correct requirements.  
- Error-recovery pathway restores valid state.

---

##  Contribution Protocol

1. Fork the repository.  
2. Create a feature branch:  
   ```bash
   git checkout -b feature/<descriptive-name>
   ```  
3. Commit with conventional messages.  
4. Push and open a Pull Request.
