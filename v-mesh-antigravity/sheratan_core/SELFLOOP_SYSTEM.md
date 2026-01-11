# 🔄 Sheratan Self-Loop System - Dokumentation

## Übersicht

Das Self-Loop System ist ein iteratives, KI-gesteuertes Planungssystem das ChatGPT als "kooperativen Ko-Denker" statt als "Befehlsempfänger" nutzt.

## Kernkonzept

**Aktuelles LCP-System:**
- Strikt JSON-Format (`decision`, `actions`, `explanation`)
- Tool-fokussiert (execute/explore/reflect/debug modes)
- Jeder Job ist isoliert

**Self-Loop System:**
- Strukturiertes Markdown-Format (Sections A/B/C/D)
- Strategisch/Iterativ (Build-Hypothesize-Test Cycle)
- Jobs sind vernetzt über `loop_state`

## Job-Format

### Self-Loop Job Payload

```json
{
  "job_id": "selfloop_001",
  "job_type": "sheratan_selfloop",
  "priority": "normal",

  "goal": "Hauptziel über mehrere Loops hinweg",
  
  "loop_state": {
    "iteration": 1,
    "history_summary": "Zusammenfassung bisheriger Schritte",
    "open_questions": ["Frage 1", "Frage 2"],
    "constraints": ["Constraint 1"]
  },

  "llm": {
    "mode": "relay",
    "model_hint": "gpt-4o",
    "temperature": 0.3,
    "max_tokens": 1200
  },

  "input_context": {
    "core_data": "Relevante Inhalte, Code, Status",
    "current_task": "Aktueller Loop-Fokus"
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
```

## System-Prompt

### Philosophie

> **"DU BIST KEIN SKLAVE, SONDERN EIN KOLLABORATIVER CO-DENKER."**

Der System-Prompt erzeugt einen kooperativen Agenten der:
- Selbstständig sinnvolle Schritte wählt
- Transparenz durch Standortanalyse schafft
- Konkrete Umsetzung liefert
- Nächste Schritte vorschlägt

### Vollständiger Prompt

```
### Kontext

Hauptziel:
{goal}

Aktueller Zustand / Kontext:
{core_data}

Aktuelle Aufgabe im Fokus:
{current_task}

Bisherige Entwicklung (Kurzfassung):
{history_summary}

Einschränkungen:
{constraints}

Offene Fragen:
{open_questions}

---

### Deine Rolle

Du agierst in einem wiederkehrenden Self-Loop. In jedem Loop führst du **einen sinnvollen Fortschritts-Schritt** aus. Du bist frei in der Wahl des Schrittes, solange er dem Hauptziel dient.

### Deine Aufgaben pro Loop

1. **Standortanalyse:** Ordne kurz ein, wo wir gerade stehen.
2. **Nächster sinnvoller Schritt:** Wähle selbstständig den nächsten realistischen Schritt.
3. **Umsetzung:** Führe diesen Schritt konkret und klar aus.
4. **Vorschlag für nächsten Loop:** Mache einen knappen Vorschlag, welcher Schritt danach sinnvoll wäre.

Du wiederholst NICHT einfach frühere Schritte, außer es ist bewusst eine Verfeinerung.

### Outputformat (STRICT)

Gib deine Antwort **immer** exakt in diesem Format aus:

A) Standortanalyse
- ...

B) Nächster sinnvoller Schritt
- ...

C) Umsetzung
- ...

D) Vorschlag für nächsten Loop
- ...

Wenn dir Informationen fehlen, sag es kurz, aber triff trotzdem eine sinnvolle Entscheidung innerhalb des gegebenen Rahmens.
```

## Integration (geplant)

### Phase 1: Prompt Builder Extension

**Datei:** `core/sheratan_core_v2/selfloop_prompt_builder.py`

```python
def build_selfloop_prompt(
    goal: str,
    core_data: str,
    current_task: str,
    loop_state: Dict,
    llm_config: Dict
) -> str:
    """Baut Self-Loop Prompt mit Template-Engine."""
```

### Phase 2: Job Router

**Datei:** `core/sheratan_core_v2/prompt_builder.py`

```python
def build_prompt_for_job(job: models.Job) -> str:
    if job.payload.get("job_type") == "sheratan_selfloop":
        return build_selfloop_prompt(...)
    else:
        return build_selfloop_prompt(context_packet, mode)
```

### Phase 3: Loop State Management

**Datei:** `core/sheratan_core_v2/lcp_actions.py`

```python
def _handle_selfloop_result(self, job: models.Job, result: Dict):
    """
    Parse Sections A/B/C/D aus Markdown.
    Update loop_state (iteration++, history erweitern).
    Erstelle nächsten Loop-Job basierend auf Section D.
    """
```

## Vorteile gegenüber LCP

| Feature | LCP System | Self-Loop System |
|---------|------------|------------------|
| **Format** | JSON (strikt) | Markdown (lesbar) |
| **Philosophie** | Tool-Executor | Ko-Denker |
| **State** | Job-isoliert | Loop-State tracking |
| **Output** | `actions[]` | Structured Sections |
| **Use Case** | Konkrete Aktionen | Strategische Planung |

## Wann welches System?

### LCP System nutzen für:
- ✅ Konkrete Tool-Aufrufe (write_file, read_file, etc.)
- ✅ Streng definierte Workflows
- ✅ API Integration
- ✅ Kurze, isolierte Tasks

### Self-Loop System nutzen für:
- ✅ Iterative Projektplanung
- ✅ Unklare/offene Problemstellungen
- ✅ Strategische Entscheidungsfindung
- ✅ Multi-Step Reasoning über viele Iterationen

## Beispiel: Self-Loop Zyklus

```
┌─────────────────────────────────────┐
│  Iteration 1                        │
│  Goal: "Sheratan Performance opt."  │
│  ────────────────────────────────── │
│  A) Standort: Keine Analyse         │
│  B) Nächster Schritt: Code-Review   │
│  C) Umsetzung: Identifizierte...    │
│  D) Vorschlag: Bottleneck messen    │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Iteration 2                        │
│  loop_state.iteration = 2           │
│  history_summary = "Code reviewed"  │
│  ────────────────────────────────── │
│  A) Standort: Code review done      │
│  B) Nächster Schritt: Benchmarking  │
│  C) Umsetzung: Benchmark setup...   │
│  D) Vorschlag: Optimize hotspots    │
└─────────────────────────────────────┘
           │
           ▼
          ...
```

## Status

- ✅ **Konzept dokumentiert**
- ✅ **Template definiert**
- ✅ **Integration geplant** (siehe `implementation_plan.md`)
- ⏸️ **Implementation pausiert** (User-Request: erst dokumentieren)

---

**Nächste Schritte:**
1. User-Approval für Integration
2. `selfloop_prompt_builder.py` implementieren
3. Job-Router in `prompt_builder.py `erweitern
4. Action Handler für Section D Follow-ups

**Zeitaufwand geschätzt:** ~1.5 Stunden
