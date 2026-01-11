"""
Self-Loop Prompt Builder
Generates prompts for the Self-Loop collaborative co-thinker system.
"""
from typing import Dict, Any


def build_selfloop_prompt(
    goal: str,
    core_data: str,
    current_task: str,
    loop_state: Dict[str, Any],
    llm_config: Dict[str, Any] = None
) -> str:
    """
    Build a Self-Loop prompt for collaborative co-thinking.
    
    Args:
        goal: Main objective across multiple loops
        core_data: Relevant context, code, status
        current_task: Current loop focus
        loop_state: Loop state with iteration, history, questions, constraints
        llm_config: Optional LLM configuration
    
    Returns:
        Formatted prompt string
    """
    llm_config = llm_config or {}
    
    # Extract loop state
    iteration = loop_state.get("iteration", 1)
    history_summary = loop_state.get("history_summary", "")
    open_questions = loop_state.get("open_questions", [])
    constraints = loop_state.get("constraints", [])
    
    # Build constraints section
    constraints_text = ""
    if constraints:
        constraints_text = "\n".join(f"- {c}" for c in constraints)
    else:
        constraints_text = "- None specified"
    
    # Build open questions section
    questions_text = ""
    if open_questions:
        questions_text = "\n".join(f"- {q}" for q in open_questions)
    else:
        questions_text = "- None at this time"
    
    # Build history section
    history_text = history_summary if history_summary else "This is the first iteration."
    
    prompt = f"""### Kontext

Hauptziel:
{goal}

Aktueller Zustand / Kontext:
{core_data}

Aktuelle Aufgabe im Fokus:
{current_task}

Bisherige Entwicklung (Kurzfassung):
{history_text}

Einschränkungen:
{constraints_text}

Offene Fragen:
{questions_text}

---

### Deine Rolle

Du agierst in einem wiederkehrenden Self-Loop (Iteration {iteration}). In jedem Loop führst du **einen sinnvollen Fortschritts-Schritt** aus. Du bist frei in der Wahl des Schrittes, solange er dem Hauptziel dient.

**WICHTIG:** DU BIST KEIN SKLAVE, SONDERN EIN KOLLABORATIVER CO-DENKER.

### Deine Aufgaben pro Loop

1. **Standortanalyse:** Ordne kurz ein, wo wir gerade stehen.
2. **Nächster sinnvoller Schritt:** Wähle selbstständig den nächsten realistischen Schritt.
3. **Umsetzung:** Führe diesen Schritt konkret und klar aus.
4. **Vorschlag für nächsten Loop:** Mache einen knappen Vorschlag, welcher Schritt danach sinnvoll wäre.

Du wiederholst NICHT einfach frühere Schritte, außer es ist bewusst eine Verfeinerung.

### Outputformat (STRICT)

Gib deine Antwort **immer** exakt in diesem Format aus:

A) Standortanalyse
- [Deine Analyse wo wir stehen]

B) Nächster sinnvoller Schritt
- [Welchen Schritt du wählst]

C) Umsetzung
- [Konkrete Ausführung des Schrittes]

D) Vorschlag für nächsten Loop
- [Was danach sinnvoll wäre]

Wenn dir Informationen fehlen, sag es kurz, aber triff trotzdem eine sinnvolle Entscheidung innerhalb des gegebenen Rahmens.
"""
    
    return prompt


def build_selfloop_job_payload(
    goal: str,
    initial_context: str,
    max_iterations: int = 10,
    constraints: list = None
) -> Dict[str, Any]:
    """
    Build a complete Self-Loop job payload.
    
    Args:
        goal: Main objective
        initial_context: Starting context/data
        max_iterations: Maximum number of loop iterations
        constraints: Optional list of constraints
    
    Returns:
        Job payload dict ready for dispatch
    """
    return {
        "job_type": "sheratan_selfloop",
        "goal": goal,
        "max_iterations": max_iterations,
        
        "loop_state": {
            "iteration": 1,
            "history_summary": "",
            "open_questions": [],
            "constraints": constraints or []
        },
        
        "input_context": {
            "core_data": initial_context,
            "current_task": "Initial analysis and planning"
        },
        
        "llm": {
            "mode": "relay",
            "model_hint": "gpt-4o",
            "temperature": 0.3,
            "max_tokens": 1200
        },
        
        "output_expectation": {
            "format": "structured_markdown",
            "sections": [
                "A:Standortanalyse",
                "B:Nächster_Schritt",
                "C:Umsetzung",
                "D:Vorschlag_nächster_Loop"
            ]
        }
    }
