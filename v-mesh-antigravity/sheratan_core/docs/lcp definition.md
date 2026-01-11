also, in dieser dati ist alles rund ums lcp recht genau beschrieben, achte dich vorallem darauf das "dein llm" von mir teilweise durch "webrelay" ersetzt wurde. es ist desswegen wichtig weil es worker "lcp" und separates llm lcp giebt/geben soll






ein **konkretes JSON-Beispiel**, das:

* das **LCP-Job-Format** zeigt (`job.json` in `webrelay_out`),
* und darunter **alle wichtigen `action`-Varianten** zeigt, die dein Backend/Worker versteht.

Du kannst das direkt als Referenz für webrelay oder deine eigenen Tools nutzen.

---

## 1️⃣ LCP-Job (so kommt es **vom Core** zum Worker)

Das ist das, was in `webrelay_out/<job_id>.job.json` landet, wenn du `dispatch` machst:

```json
{
  "job_id": "3fb00550-c006-48c6-b377-80ee7d2da561",
  "kind": "llm_call",
  "payload": {
    "response_format": "lcp",

    "mission": {
      "id": "ad90ec78-4cc7-4639-bb92-babd7f944090",
      "title": "Testmission",
      "description": "Ein PoC über docker-compose",
      "metadata": {
        "created_by": "jeremy",
        "max_iterations": 10
      },
      "tags": ["workspace", "user:jeremy"],
      "created_at": "2025-12-08T14:21:05.928566Z"
    },

    "task": {
      "id": "ed511e47-9a50-491d-8073-151355c8ad8a",
      "mission_id": "ad90ec78-4cc7-4639-bb92-babd7f944090",
      "name": "Initial agent plan",
      "description": "Plan steps for mission",
      "kind": "agent_plan",
      "params": {
        "project_root": "/workspace/project",
        "user_prompt": "Bitte analysiere den Code und sag mir, was main.py macht."
      },
      "created_at": "2025-12-09T04:58:28.484492Z"
    },

    "params": {
      /* optional, z.B. zusätzliche Payload für den Job */
    }
  }
}
```

**Wichtig:**

* Alles unter `payload` ist das, was dein Worker / LLM sehen soll:

  * `response_format: "lcp"` → „LCP-Modus“
  * `mission` → Kontext
  * `task.kind` → welches „Tool“ (list_files, read_file, rewrite_file, agent_plan, …)
  * `task.params` → Inputs für das Tool
* **Backend-Funktionen** (`list_missions`, `apply_agent_plan`, …) sind **HTTP-Endpunkte**, nicht direkt in LCP.
  Sie benutzen nur `job.result.action`, um zu entscheiden, was sie tun.

---

## 2️⃣ LCP-Resultate (so kommen Antworten **vom Worker** zurück)

Das hier ist ein „Katalog“ von **Result-JSONs**, die in
`webrelay_in/<job_id>.result.json` landen und dann von Core gespeichert werden (`job.result`).

Ich pack alles in ein großes Beispiel-Objekt – in echt ist natürlich immer nur **ein** Action-Result pro Datei.

```json
{
  "examples": {
    "list_files_result": {
      "ok": true,
      "action": "list_files_result",
      "files": [
        "project/config.py",
        "project/main.py",
        "project/utils.py"
      ],
      "info": "Listed 3 files for job 3ed8ddd7-6b78-4f45-b41c-fd066123ed2d",
      "root": "/workspace/project",
      "patterns": ["*.py"]
    },

    "read_file_result": {
      "ok": true,
      "action": "read_file_result",
      "path": "/workspace/project/main.py",
      "content": "print(\"Hello from Sheratan agent!\")\n"
    },

    "write_file_result": {
      "ok": true,
      "action": "write_file",
      "path": "/workspace/project/main.py",
      "bytes_written": 42,
      "info": "Rewrote file main.py with new content"
    },

    "agent_plan_create_followup_jobs": {
      "ok": true,
      "action": "create_followup_jobs",

      "commentary": "I will first list Python files in the project, then read main.py to understand the entrypoint.",

      "new_jobs": [
        {
          "name": "List project files",
          "description": "Discover Python files in the project",
          "kind": "list_files",
          "params": {
            "root": "/workspace/project",
            "patterns": ["**/*.py"]
          },
          "auto_dispatch": true
        },
        {
          "name": "Read main.py",
          "description": "Inspect the main entrypoint file",
          "kind": "read_file",
          "params": {
            "root": "/workspace/project",
            "rel_path": "main.py"
          },
          "auto_dispatch": false
        }
      ],

      "meta": {
        "user_prompt": "Bitte analysiere den Code und sag mir, was main.py macht.",
        "project_root": "/workspace/project"
      }
    },

    "noop_result": {
      "ok": true,
      "action": "noop",
      "message": "Nothing to do for this job (e.g. unknown task kind)."
    },

    "error_result": {
      "ok": false,
      "action": "error",
      "error": "File not found: /workspace/project/main.py",
      "details": {
        "code": "ENOENT",
        "path": "/workspace/project/main.py"
      }
    }
  }
}
```

---

## 3️⃣ Wie hängen `action` und Backend-Funktionen zusammen?

Deine **Backend-Funktionen** (Python) gucken auf `job.result.action` und reagieren:

| Backend-Funktion                           | Wo sie schaut / was sie tut                                                                 |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `get_mission_status`                       | holt `job.result` (egal welche `action`), zeigt nur Status an                               |
| `start_discovery_task`                     | erstellt `list_files`-Task/Job, dispatcht ihn                                               |
| **Worker → `action: "list_files_result"`** | Ergebnis von oben, wird nur angezeigt / geloggt                                             |
| `apply_agent_plan(mission_id, job_id)`     | **erwartet** `job.result.action == "create_followup_jobs"`                                  |
|                                            | liest `new_jobs[]`, legt daraus Tasks + Jobs im Core an, dispatcht, wo `auto_dispatch=true` |

Für webrelay/Worker bedeutet das:

* `list_files`, `read_file`, `rewrite_file` usw. → `action` beschreibt das „Tool-Ergebnis“ (`list_files_result`, `read_file_result`, `write_file`).
* `agent_plan` → **muss** `action: "create_followup_jobs"` liefern, damit `apply_agent_plan` greift.
* `noop` / `error` → sind „fallback“-Actions, die du beliebig verwenden kannst, wenn etwas nicht passt.

---

## 4️⃣ Wo „muss“ was im JSON stehen? (Kurz-Check)

Wenn du webrelay andockst, kannst du dir das so merken:

1. **Job (vom Core):**

   * liegt in: `webrelay_out/<job_id>.job.json`
   * relevante Felder:

     * `payload.response_format` → `"lcp"`
     * `payload.mission` → Kontext
     * `payload.task.kind` → welches Tool du ausführen sollst
     * `payload.task.params` → Input

2. **Result (von dir / Worker / LLM-Adapter):**

   * liegt in: `webrelay_in/<job_id>.result.json`
   * Top-Level-Keys (von dir definiert, aber **vertraglich** wichtig):

     * `ok`: `true` oder `false`
     * `action`: string → steuert, was Backend/Core damit macht
     * der Rest je nach `action`:

       * `list_files_result` → `files`, `root`, `patterns`, `info`
       * `read_file_result` → `path`, `content`
       * `write_file` → `path`, `bytes_written`, `info`
       * `create_followup_jobs` → `commentary`, `new_jobs[]`, `meta`
       * `noop` → `message`
       * `error` → `error`, `details`

---





also;

Ja, nice, jetzt machen wir einmal „alles auf einen Blick“ – **LCP-Job + alle Actions + wo was im JSON hängen soll**, so dass du webrelay und deine Worker sauber daran ausrichten kannst.

Ich baue dir unten eine **Meta-JSON-Struktur**, die:

* ein **Beispiel-LCP-Job** zeigt (so kommt er aus dem Core in `webrelay_out`)
* alle wichtigen **`action`-Result-Formate** gesammelt zeigt (so sollen sie in `webrelay_in` landen)

---

## 1️⃣ LCP-Job: so sieht ein Job im `webrelay_out` aus

Das ist ein **konkretes Beispiel** für einen `agent_plan`-Job im LCP-Format:

```json
{
  "job_id": "3fb00550-c006-48c6-b377-80ee7d2da561",
  "kind": "llm_call",

  "payload": {
    "response_format": "lcp",

    "mission": {
      "id": "ad90ec78-4cc7-4639-bb92-babd7f944090",
      "title": "Testmission",
      "description": "Ein PoC über docker-compose",
      "metadata": {
        "created_by": "jeremy",
        "max_iterations": 10
      },
      "tags": ["workspace", "user:jeremy"],
      "created_at": "2025-12-08T14:21:05.928566Z"
    },

    "task": {
      "id": "ed511e47-9a50-491d-8073-151355c8ad8a",
      "mission_id": "ad90ec78-4cc7-4639-bb92-babd7f944090",
      "name": "Initial agent plan",
      "description": "Plan steps for mission",
      "kind": "agent_plan",
      "params": {
        "project_root": "/workspace/project",
        "user_prompt": "Bitte analysiere den Code und sag mir, was main.py macht."
      },
      "created_at": "2025-12-09T04:58:28.484492Z"
    },

    "params": {
      "some_optional_payload": "frei für Worker/LLM"
    }
  }
}
```

**Merke:**

* **LCP lebt in `payload`**:

  * `mission`
  * `task`
  * `params`
* **`task.kind`** ist das zentrale Routing-Feld für deinen Worker / webrelay:

  * `"list_files"`
  * `"read_file"`
  * `"rewrite_file"`
  * `"agent_plan"`
* Der Worker / webrelay füllt **NICHT** `payload` um, sondern schreibt eine **separate Result-Datei**.

---

## 2️⃣ Result-Seite: `job.result` – wo die Actions rein müssen

Die Resultate landen in:

* Datei: `webrelay_in/<job_id>.result.json`
* Nach `sync`: im Core unter `job.result`

**Wichtig:**
Die `action` steht immer **top-level** im Result:

```json
{
  "ok": true,
  "action": "irgendwas",
  "...": "weitere Felder"
}
```

---

## 3️⃣ „Backend-Funktionen“ als Actions – Übersicht

Wir definieren jetzt einen sauberen „Antwortvertrag“ für die Haupt-Actions, die in deinem System Sinn machen:

* `list_files_result`  → Ergebnis von `task.kind = "list_files"`
* `read_file_result`   → Ergebnis von `task.kind = "read_file"`
* `write_file`         → Ergebnis von `task.kind = "rewrite_file"` (der eigentliche Schreibvorgang)
* `create_followup_jobs` → Ergebnis von `task.kind = "agent_plan"` (wird von `apply_agent_plan` interpretiert)
* optional: `noop` / `error` → zum Debuggen oder „nix Besonderes zu tun“

Ich pack das mal in **ein großes JSON-„Schema-Beispiel“**:

```json
{
  "lcp_job_example": {
    "job_id": "3fb00550-c006-48c6-b377-80ee7d2da561",
    "kind": "llm_call",
    "payload": {
      "response_format": "lcp",
      "mission": { "...": "siehe oben" },
      "task": {
        "id": "ed511e47-9a50-491d-8073-151355c8ad8a",
        "mission_id": "ad90ec78-4cc7-4639-bb92-babd7f944090",
        "name": "Initial agent plan",
        "description": "Plan steps for mission",
        "kind": "agent_plan",
        "params": {
          "project_root": "/workspace/project",
          "user_prompt": "Bitte analysiere den Code und sag mir, was main.py macht."
        },
        "created_at": "2025-12-09T04:58:28.484492Z"
      },
      "params": {}
    }
  },

  "result_shapes": {

    "list_files_result": {
      "description": "Ergebnis eines list_files-Tasks",
      "for_task_kind": "list_files",
      "example": {
        "ok": true,
        "action": "list_files_result",
        "files": [
          "project/config.py",
          "project/main.py",
          "project/utils.py"
        ],
        "root": "/workspace/project",
        "patterns": ["*.py", "**/*.py"],
        "info": "Listed 3 files for job 3ed8ddd7-6b78-4f45-b41c-fd066123ed2d"
      }
    },

    "read_file_result": {
      "description": "Ergebnis eines read_file-Tasks",
      "for_task_kind": "read_file",
      "example": {
        "ok": true,
        "action": "read_file_result",
        "path": "/workspace/project/main.py",
        "content": "print(\"Hello from Sheratan agent!\")\n",
        "encoding": "utf-8",
        "info": "Read 1 file"
      }
    },

    "write_file": {
      "description": "Ergebnis eines rewrite_file-Tasks (tatsächlicher Schreibvorgang)",
      "for_task_kind": "rewrite_file",
      "example": {
        "ok": true,
        "action": "write_file",
        "path": "/workspace/project/main.py",
        "bytes_written": 42,
        "info": "Rewrote file main.py with new content"
      }
    },

    "create_followup_jobs": {
      "description": "Agent-Plan: erzeugt neue Tasks/Jobs für die Mission",
      "for_task_kind": "agent_plan",
      "example": {
        "ok": true,
        "action": "create_followup_jobs",

        "commentary": "I will first list Python files in the project, then read main.py to understand the entrypoint.",

        "new_jobs": [
          {
            "name": "List project files",
            "description": "Discover Python files in the project",
            "kind": "list_files",
            "params": {
              "root": "/workspace/project",
              "patterns": ["**/*.py"]
            },
            "auto_dispatch": true
          },
          {
            "name": "Read main.py",
            "description": "Inspect the main entrypoint file",
            "kind": "read_file",
            "params": {
              "root": "/workspace/project",
              "rel_path": "main.py"
            },
            "auto_dispatch": false
          }
        ],

        "meta": {
          "user_prompt": "Bitte analysiere den Code und sag mir, was main.py macht.",
          "project_root": "/workspace/project"
        }
      }
    },

    "noop": {
      "description": "Kein spezielles Handling, nur Info/Debug",
      "for_task_kind": "beliebig",
      "example": {
        "ok": true,
        "action": "noop",
        "message": "Nothing to do for this task kind.",
        "payload_echo": {
          "response_format": "lcp",
          "mission": { "...": "original mission" },
          "task": { "...": "original task" },
          "params": {}
        }
      }
    },

    "error": {
      "description": "Fehlerfall im Worker/LLM",
      "for_task_kind": "beliebig",
      "example": {
        "ok": false,
        "action": "error",
        "error_type": "file_not_found",
        "message": "Could not open /workspace/project/main.py",
        "details": {
          "path": "/workspace/project/main.py"
        }
      }
    }
  }
}
```

---

## 4️⃣ Wie das Backend konkret mit den Actions umgeht

In deinem Backend hast du ja grob folgende „Funktionen“ (Python/mission_service):

* `start_discovery_task(...)`
  → erzeugt `list_files`-Task + Job → Worker gibt `list_files_result`
* `get_mission_status(...)`
  → ruft `/api/missions/{id}/status` + `sync` → sieht `job.result.action` (z.B. `read_file_result`, `write_file`, etc.)
* `apply_agent_plan(mission_id, job_id)`
  → macht `sync_job(job_id)` → schaut auf `job.result.action`:

  * wenn `create_followup_jobs`:

    * iteriert über `new_jobs`
    * legt Tasks/Jobs im Core an
    * dispatcht Jobs, wo `auto_dispatch = true` ist

👉 **Nur `create_followup_jobs` ist „backend-spezial“**, weil es zu echten neuen Tasks/Jobs führt.
Alle anderen Actions (`list_files_result`, `read_file_result`, `write_file`, `noop`, `error`) landen „nur“ im `job.result` und werden in `mission_status` sichtbar.

---

## 5️⃣ TL;DR – woran webrelay/Worker sich halten muss

1. **LCP-Job lesen**:

   * `payload.mission`
   * `payload.task.kind`
   * `payload.task.params`

2. **Je nach `task.kind`** ein Result bauen mit:

   * `ok`: `true` / `false`
   * `action`: einer der Strings, auf die du dich geeinigt hast
   * zusätzliche Felder je Action (siehe oben)

3. **In Datei schreiben**:

   * `webrelay_in/<job_id>.result.json`

4. **Core syncen** (außerhalb des Workers):

   * `POST /api/jobs/{job_id}/sync`

5. **Backend**:

   * Für `agent_plan`: `POST /missions/{mission_id}/apply_plan/{job_id}` → nutzt `create_followup_jobs`.

---

und zum schloss nochlas ;


Alles klar, machen wir beides 💾🧠

---

## 1️⃣ JSON-Schema für `create_followup_jobs` (für LLM-Prompts)

Das ist ein **konkretes Schema**, das du in deinen Prompt klatschen kannst:
„Antwort **MUSS** genau so aussehen“ – ideal für dein eigenes LLM.

### 1.1 Verbales Schema

**Top-Level Objekt:**

```json
{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "string",
  "new_jobs": [ ... ],
  "meta": { ... }
}
```

### 1.2 Strengere Schema-Definition (zum Kopieren in einen Prompt)

```json
{
  "type": "object",
  "required": ["ok", "action", "new_jobs"],
  "properties": {
    "ok": {
      "type": "boolean",
      "description": "Must be true if the agent plan was successfully created."
    },
    "action": {
      "type": "string",
      "enum": ["create_followup_jobs"],
      "description": "Always exactly 'create_followup_jobs' for a successful agent_plan result."
    },
    "commentary": {
      "type": "string",
      "description": "Short natural language explanation of the plan. Can be German or English."
    },
    "new_jobs": {
      "type": "array",
      "description": "List of followup tasks/jobs the backend should create for this mission.",
      "items": {
        "type": "object",
        "required": ["name", "kind", "params"],
        "properties": {
          "name": {
            "type": "string",
            "description": "Short, human-readable name of the followup task."
          },
          "description": {
            "type": "string",
            "description": "Optional longer description of what this step does."
          },
          "kind": {
            "type": "string",
            "enum": ["list_files", "read_file", "rewrite_file"],
            "description": "Type of followup task."
          },
          "params": {
            "type": "object",
            "description": "Tool-specific parameters. Must match the 'kind'."
          },
          "auto_dispatch": {
            "type": "boolean",
            "description": "If true, the backend will automatically create and dispatch a job for this task.",
            "default": false
          }
        },
        "additionalProperties": false
      }
    },
    "meta": {
      "type": "object",
      "description": "Optional metadata that the backend will store together with the job result.",
      "properties": {
        "user_prompt": {
          "type": "string"
        },
        "project_root": {
          "type": "string"
        }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": false
}
```

### 1.3 Beispiel, das exakt dem Schema entspricht

```json
{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "I will first list all Python files, then inspect main.py.",
  "new_jobs": [
    {
      "name": "List project files",
      "description": "Discover Python files in the project",
      "kind": "list_files",
      "params": {
        "root": "/workspace/project",
        "patterns": ["**/*.py"]
      },
      "auto_dispatch": true
    },
    {
      "name": "Read main.py",
      "description": "Inspect the main entrypoint file",
      "kind": "read_file",
      "params": {
        "root": "/workspace/project",
        "rel_path": "main.py"
      },
      "auto_dispatch": false
    }
  ],
  "meta": {
    "user_prompt": "Bitte analysiere den Code und sag mir, was main.py macht.",
    "project_root": "/workspace/project"
  }
}
```

Das ist genau das, was `apply_agent_plan(...)` später frisst.

---

## 2️⃣ Action-Tabelle: `task.kind` ↔ `action` ↔ wer macht was?

Hier eine Übersicht über die „Backend-Funktionen“ / Worker-Logik / Actions.

### 2.1 Übersichtstabelle

| **task.kind**  | **Typische `result.action`** | **Wer produziert das?**          | **Wer konsumiert das?**                               | **Wozu?**                                                  |
| -------------- | ---------------------------- | -------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- |
| `list_files`   | `list_files_result`          | Worker (oder dein eigener Agent) | Nur zum Anzeigen / Debug (z.B. `mission_status`)      | Dateiliste für Projekt-Discovery                           |
| `read_file`    | `read_file_result`           | Worker                           | UI / Agent-Logik (kann später vom LLM genutzt werden) | Dateiinhalt für Analyse/Änderungen                         |
| `rewrite_file` | `write_file`                 | Worker                           | UI / Agent-Logik / `mission_status`                   | Tatsächlicher Schreibvorgang auf dem Filesystem            |
| `agent_plan`   | `create_followup_jobs`       | Worker / LLM-Agent               | Backend: `apply_agent_plan(mission_id, job_id)`       | Aus einem Prompt einen Plan aus mehreren Folge-Tasks bauen |
| (beliebig)     | `noop`                       | Worker                           | Niemand speziell; nur Debug / Logs                    | „Ich habe nichts Spezielles getan“                         |
| (beliebig)     | `error`                      | Worker                           | Backend / UI (Fehler anzeigen)                        | Fehler kommunizieren (z.B. File nicht gefunden)            |

### 2.2 Wo sie „sein müssen“ im JSON

**Job-Datei (`webrelay_out/<job_id>.job.json`):**

* Enthält:

  * `job_id`
  * `kind`
  * `payload.response_format = "lcp"`
  * `payload.mission`
  * `payload.task` (inkl. `kind`, `params`)
  * `payload.params` (extra Worker-Input, optional)
* KEINE `action` da drin – das ist Input, nicht Output.

**Result-Datei (`webrelay_in/<job_id>.result.json`):**

* Enthält:

  * `ok`: `true` / `false`
  * `action`: einer aus der Tabelle oben
  * weitere Felder je nach `action`:

Beispiele kurz:

* `list_files_result`:

  ```json
  {
    "ok": true,
    "action": "list_files_result",
    "files": ["project/main.py"],
    "root": "/workspace/project",
    "patterns": ["**/*.py"]
  }
  ```

* `read_file_result`:

  ```json
  {
    "ok": true,
    "action": "read_file_result",
    "path": "/workspace/project/main.py",
    "content": "print(\"Hello from Sheratan agent!\")\n"
  }
  ```

* `write_file`:

  ```json
  {
    "ok": true,
    "action": "write_file",
    "path": "/workspace/project/main.py",
    "bytes_written": 42
  }
  ```

* `create_followup_jobs` (siehe Schema oben)

* `noop`:

  ```json
  {
    "ok": true,
    "action": "noop",
    "message": "Nothing to do for this task kind."
  }
  ```

* `error`:

  ```json
  {
    "ok": false,
    "action": "error",
    "error_type": "file_not_found",
    "message": "Could not open /workspace/project/main.py",
    "details": {
      "path": "/workspace/project/main.py"
    }
  }
  ```

**Nach `sync`** landet genau dieses Objekt unter `job.result` im Core.
Das Backend sieht also immer: `job.result.action`, `job.result.ok`, etc.

---



 hier kommt eine sauber kommentierte **„Action-Tabelle als Code-Kommentarblock“**, die du **1:1 in deinen Worker**, dein Backend oder deinen LLM-Code einkleben kannst.

Sie enthält:

* alle `task.kind`
* die zugehörigen erwarteten `result.action`
* wer die Action erzeugt
* wer sie später verarbeitet
* * mini-Beispiel-JSON pro Action

Das ist so formuliert, dass es ideal in Python-Dateien, Worker-Module oder LLM-Prompts passt.

---

# 📦 **ACTION TABLE – Sheratan Agent Framework**

### (Zum Einfügen in Code, Worker oder LLM-Definitionen)

```text
===============================================================================
SHERATAN ACTION TABLE – Mapping von task.kind → result.action
===============================================================================

Jeder Job, den der Core dispatcht, landet als *.job.json in webrelay_out.

Der Worker (oder dein eigenes LLM) erzeugt eine dazu passende *.result.json
in webrelay_in — darin steht immer ein Top-Level-Feld:

    "action": "<action_name>"

Hier ist die vollständige Übersicht, welche Actions erlaubt sind,
welche Inputs sie haben und wer sie konsumiert.
===============================================================================
```

---

## 1️⃣ `list_files`  →  **`list_files_result`**

```
task.kind:
    "list_files"

result.action:
    "list_files_result"

Produziert von:
    Worker oder externer Agent

Konsumiert von:
    - Backend (mission_status)
    - LLM / UI (optional)
    - Nicht automatisch weiterverarbeitet

Beispiel-Result:
{
  "ok": true,
  "action": "list_files_result",
  "files": ["project/main.py", "project/utils.py"],
  "root": "/workspace/project",
  "patterns": ["**/*.py"],
  "info": "Listed 2 files"
}
```

---

## 2️⃣ `read_file`  →  **`read_file_result`**

```
task.kind:
    "read_file"

result.action:
    "read_file_result"

Produziert von:
    Worker / Agent

Konsumiert von:
    - mission_status Anzeige
    - LLM für Code-Verständnis
    - UI

Beispiel-Result:
{
  "ok": true,
  "action": "read_file_result",
  "path": "/workspace/project/main.py",
  "content": "print('Hello world')\n"
}
```

---

## 3️⃣ `rewrite_file`  →  **`write_file`**

```
task.kind:
    "rewrite_file"

result.action:
    "write_file"

Produziert von:
    Worker / Agent nach dem tatsächlichen Schreiben

Konsumiert von:
    - mission_status Anzeige
    - LLM, z.B. zur Bestätigung der Änderung

Beispiel-Result:
{
  "ok": true,
  "action": "write_file",
  "path": "/workspace/project/main.py",
  "bytes_written": 56,
  "info": "File overwritten"
}
```

---

## 4️⃣ `agent_plan`  →  **`create_followup_jobs`**

```
task.kind:
    "agent_plan"

result.action:
    "create_followup_jobs"

Produziert von:
    Worker / LLM-Agent

Konsumiert von:
    - Backend-Funktion apply_agent_plan(mission_id, job_id)
      Diese erzeugt:
          - neue Tasks
          - neue Jobs
          - dispatcht Jobs mit auto_dispatch = true

WICHTIG:
    Dieses Result ist der "Gehirn-Output" des Agenten:
    Der Worker/LLM sagt dem System, welche Schritte folgen.

Beispiel-Result:
{
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "Listing Python files then reading main.py.",
  "new_jobs": [
    {
      "name": "List project files",
      "description": "Find all Python files",
      "kind": "list_files",
      "params": { "root": "/workspace/project", "patterns": ["**/*.py"] },
      "auto_dispatch": true
    },
    {
      "name": "Read main.py",
      "description": "Understand entrypoint",
      "kind": "read_file",
      "params": { "root": "/workspace/project", "rel_path": "main.py" },
      "auto_dispatch": false
    }
  ],
  "meta": {
      "user_prompt": "<original user command>",
      "project_root": "/workspace/project"
  }
}
```

---

## 5️⃣ `noop`  →  für alle Fälle, in denen nichts Besonderes passiert

```
task.kind:
    beliebig

result.action:
    "noop"

Produziert von:
    Worker

Konsumiert von:
    Niemand speziell (Debug / Logging)

Beispiel-Result:
{
  "ok": true,
  "action": "noop",
  "message": "Task kind not supported in this PoC."
}
```

---

## 6️⃣ `error`  →  universelles Fehlerformat

```
task.kind:
    beliebig

result.action:
    "error"

Produziert von:
    Worker / Agent bei Fehlschlägen

Konsumiert von:
    Backend, UI, Logs

Beispiel-Result:
{
  "ok": false,
  "action": "error",
  "error_type": "file_not_found",
  "message": "Could not open file",
  "details": { "path": "/workspace/project/missing.py" }
}
```

---

# 🎯 Komplette Action-Referenz (kurz)

```text
task.kind        → result.action
-------------------------------------------
list_files       → list_files_result
read_file        → read_file_result
rewrite_file     → write_file
agent_plan       → 
(any)            → noop
(any)            → error
```

---

# 