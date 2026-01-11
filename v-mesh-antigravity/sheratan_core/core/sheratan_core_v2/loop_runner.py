# loop_runner.py
"""
Sheratan SelfLoop Runner
Version: 1.0

Führt einen Sheratan-kompatiblen SelfLoop aus, basierend auf einem
LoopRunner-Job-JSON (z. B. loop_runner_job.template.json).

Abhängigkeiten:
- prompt_builder.build_selfloop_prompt
- lcp_validator.is_valid_lcp_response

Dieses Modul:
- lädt Job-Config
- baut ContextPacket
- ruft ein LLM (über einen austauschbaren Client) mit dem SelfLoop-Prompt auf
- validiert die LCP-Response
- führt erlaubte Actions über einen ActionExecutor aus
- aktualisiert State/Mission/Memory
- respektiert Loop-Policy (max_iterations, max_consecutive_errors, Safe-Mode)

Integration:
- die konkrete LLM-Anbindung (WebRelay, OpenAI, lokales GGUF) muss in
  `LLMClient.call()` implementiert werden.
- Action-Ausführung muss in `ActionExecutor.execute()` implementiert werden.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from prompt_builder import build_selfloop_prompt
from lcp_validator import is_valid_lcp_response


# ---------------------------------------------------------------------------
# Datamodels
# ---------------------------------------------------------------------------

@dataclass
class LoopConfig:
    max_iterations: int
    max_consecutive_errors: int
    profile: str  # "explore" | "execute" | "reflect" | "debug"
    safe_mode_on_policy_violation: bool = True
    context_profile: str = "execute"


@dataclass
class ModelConfig:
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 2000
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MissionState:
    mission_id: str
    goal: str
    mode: str  # "explore" | "execute" | "reflect" | "debug"
    constraints: List[str] = field(default_factory=list)
    finished: bool = False
    aborted: bool = False
    safe_mode: bool = False
    iteration: int = 0
    error_count_recent: int = 0


# ---------------------------------------------------------------------------
# LLM Client (Integration Point)
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Abstrakter LLM-Client.

    Implementiere hier:
    - WebRelay-Call
    - OpenAI-Call
    - Lokales GGUF-Modell
    """

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

    def call(self, prompt: str) -> str:
        """
        Führt den LLM-Call aus und gibt den rohen Response-Text zurück.

        HIER musst du dein reales Modell anbinden.
        Aktuell: Dummy-Implementation, die NotImplementedError wirft.
        """
        # Beispiel für spätere Integration:
        # if self.model_config.provider == "webrelay":
        #     return self._call_webrelay(prompt)
        # elif self.model_config.provider == "openai":
        #     return self._call_openai(prompt)
        # elif self.model_config.provider == "local":
        #     return self._call_local(prompt)
        # else:
        #     raise RuntimeError(f"Unknown provider: {self.model_config.provider}")
        raise NotImplementedError(
            "LLMClient.call() ist nicht implementiert. Bitte hier deine LLM-Anbindung ergänzen."
        )


# ---------------------------------------------------------------------------
# Action Executor (Integration Point)
# ---------------------------------------------------------------------------

class ActionExecutor:
    """
    Führt LCP-Actions aus.

    Integration-Point für:
    - Filesystem-Operationen
    - WebRelay-Job-Queue
    - interne Sheratan-Services

    Aktuell: Stub, der nur loggt.
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def execute(self, actions: List[Dict[str, Any]], state: MissionState) -> None:
        """
        Führt die übergebenen Actions aus.

        Diese Funktion sollte:
        - Policy prüfen (z. B. keine write-Actions im Safe-Mode)
        - pro Action den zuständigen Handler aufrufen
        - Ergebnisse ggf. in Memory/Logs speichern

        Aktuell: nur Debug-Ausgabe.
        """
        for idx, action in enumerate(actions):
            kind = action.get("kind", "")
            # Policy-Beispiele (einfach):
            if state.safe_mode and kind.startswith("filesystem.write"):
                print(f"[ActionExecutor] SKIP (Safe-Mode): {action}")
                continue

            if self.dry_run:
                print(f"[ActionExecutor] DRY-RUN execute[{idx}]: {json.dumps(action, ensure_ascii=False)}")
            else:
                # TODO: echte Handler implementieren
                print(f"[ActionExecutor] EXECUTE[{idx}]: {json.dumps(action, ensure_ascii=False)}")
                # Beispiel:
                # if kind == "filesystem.read": ...
                # elif kind == "webrelay.enqueue_job": ...
                # etc.


# ---------------------------------------------------------------------------
# Loop Runner
# ---------------------------------------------------------------------------

class LoopRunner:
    """
    Führt einen SelfLoop für eine Mission basierend auf einer Job-Config aus.
    """

    def __init__(
        self,
        job_config: Dict[str, Any],
        dry_run: bool = True,
    ) -> None:
        self.job_config = job_config
        self.dry_run = dry_run

        self.loop_config = self._parse_loop_config(job_config.get("loop_config", {}))
        self.model_config = self._parse_model_config(job_config.get("model_config", {}))
        self.mission_state = self._init_mission_state(job_config.get("mission", {}))

        self.llm_client = LLMClient(self.model_config)
        self.action_executor = ActionExecutor(dry_run=dry_run)

        self.context_packet = self._init_context_packet(job_config.get("initial_context_packet", {}))

    # ---------------------------
    # Config Parsing
    # ---------------------------

    def _parse_loop_config(self, cfg: Dict[str, Any]) -> LoopConfig:
        return LoopConfig(
            max_iterations=int(cfg.get("max_iterations", 20)),
            max_consecutive_errors=int(cfg.get("max_consecutive_errors", 3)),
            profile=str(cfg.get("profile", "execute")),
            safe_mode_on_policy_violation=bool(cfg.get("safe_mode_on_policy_violation", True)),
            context_profile=str(cfg.get("context_profile", "execute")),
        )

    def _parse_model_config(self, cfg: Dict[str, Any]) -> ModelConfig:
        provider = cfg.get("provider", "webrelay")
        model = cfg.get("model", "gpt-4o-or-equivalent")
        temperature = float(cfg.get("temperature", 0.2))
        max_tokens = int(cfg.get("max_tokens", 2000))
        extra = {k: v for k, v in cfg.items() if k not in {"provider", "model", "temperature", "max_tokens"}}
        return ModelConfig(
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            extra=extra,
        )

    def _init_mission_state(self, mission_cfg: Dict[str, Any]) -> MissionState:
        mission_id = mission_cfg.get("mission_id", "M-UNKNOWN")
        goal = mission_cfg.get("goal", "UNSPECIFIED_GOAL")
        mode = mission_cfg.get("mode", "execute")
        constraints = mission_cfg.get("constraints", [])
        return MissionState(
            mission_id=mission_id,
            goal=goal,
            mode=mode,
            constraints=constraints,
        )

    def _init_context_packet(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialer ContextPacket – später vom Loop aktualisiert.

        Erwartet Struktur ähnlich dem Template:
        {
          "mission": {...},
          "progress": [...],
          "state": {...},
          "memory": {...},
          "loop_focus": "..."
        }
        """
        # Fallbacks definieren, falls Felder fehlen:
        context = {
            "mission": ctx.get("mission", {
                "id": self.mission_state.mission_id,
                "goal": self.mission_state.goal,
                "mode": self.mission_state.mode,
            }),
            "progress": ctx.get("progress", []),
            "state": ctx.get("state", {
                "iteration": self.mission_state.iteration,
                "safe_mode": self.mission_state.safe_mode,
                "error_count_recent": self.mission_state.error_count_recent,
            }),
            "memory": ctx.get("memory", {}),
            "loop_focus": ctx.get("loop_focus", "bootstrap loop and run first decision"),
        }
        return context

    # ---------------------------
    # Loop Execution
    # ---------------------------

    def run(self) -> None:
        """
        Führt den SelfLoop gemäß LoopConfig aus.
        """
        print(f"[LoopRunner] Start Mission {self.mission_state.mission_id}")
        print(f"[LoopRunner] Goal: {self.mission_state.goal}")
        print(f"[LoopRunner] Mode: {self.mission_state.mode}, Max Iter: {self.loop_config.max_iterations}")

        while not self._should_stop():
            self.mission_state.iteration += 1
            print(f"\n[LoopRunner] === Iteration {self.mission_state.iteration} ===")

            # Kontext aktualisieren
            self._sync_context_from_state()

            # Prompt bauen
            prompt = build_selfloop_prompt(
                context_packet=self.context_packet,
                mode=self._current_loop_mode(),
            )

            # LLM-Call
            try:
                llm_response = self.llm_client.call(prompt)
            except NotImplementedError as e:
                print(f"[LoopRunner] LLMClient not implemented: {e}")
                print("[LoopRunner] Abbruch, da kein echter LLM-Client hinterlegt ist.")
                return
            except Exception as e:
                print(f"[LoopRunner] ERROR: LLM call failed: {e}")
                self._on_error("llm_call_error")
                continue

            # Validierung
            valid, error_msg = is_valid_lcp_response(llm_response)
            if not valid:
                print(f"[LoopRunner] INVALID LCP RESPONSE: {error_msg}")
                self._on_error("lcp_validation_error")
                continue

            # JSON parsen (wir wissen, dass es valid ist)
            response_obj = json.loads(llm_response)
            decision = response_obj.get("decision", {})
            actions = response_obj.get("actions", [])
            explanation = response_obj.get("explanation", "")

            print(f"[LoopRunner] Decision: {decision.get('kind')}")
            if explanation:
                print(f"[LoopRunner] Explanation: {explanation}")

            # Decision auswerten
            self._apply_decision(decision)

            # Actions ausführen
            self._execute_actions(actions)

            # Fehlerzähler zurücksetzen, da diese Iteration erfolgreich war
            self.mission_state.error_count_recent = 0

            # Mission beendet?
            if self.mission_state.finished or self.mission_state.aborted:
                print("[LoopRunner] Mission finished/aborted → Loop stop.")
                break

        print(f"[LoopRunner] End Mission {self.mission_state.mission_id}")
        print(f"[LoopRunner] Final iteration: {self.mission_state.iteration}")
        print(f"[LoopRunner] Safe mode: {self.mission_state.safe_mode}")
        print(f"[LoopRunner] Errors recent: {self.mission_state.error_count_recent}")

    # ---------------------------
    # Helpers
    # ---------------------------

    def _current_loop_mode(self) -> str:
        """
        Aktuellen Modus bestimmen: Mission-Mode oder Safe-Mode-Override.
        """
        if self.mission_state.safe_mode:
            return "debug"
        return self.loop_config.profile or self.mission_state.mode

    def _sync_context_from_state(self) -> None:
        """
        Aktualisiert den ContextPacket anhand des MissionState.
        """
        self.context_packet.setdefault("state", {})
        self.context_packet["state"]["iteration"] = self.mission_state.iteration
        self.context_packet["state"]["safe_mode"] = self.mission_state.safe_mode
        self.context_packet["state"]["error_count_recent"] = self.mission_state.error_count_recent

        self.context_packet.setdefault("mission", {})
        self.context_packet["mission"]["id"] = self.mission_state.mission_id
        self.context_packet["mission"]["goal"] = self.mission_state.goal
        self.context_packet["mission"]["mode"] = self.mission_state.mode

    def _apply_decision(self, decision: Dict[str, Any]) -> None:
        """
        Interpretiert die Decision (minimal).
        Du kannst hier später detailliertere Decision-Handling-Logik einbauen.
        """
        kind = decision.get("kind", "")
        if kind in ("summarize_and_finish", "finish_mission"):
            self.mission_state.finished = True
        elif kind in ("abort_mission", "abort"):
            self.mission_state.aborted = True
        elif kind in ("enter_safe_mode", "enter_safe_mode_recommendation"):
            if self.loop_config.safe_mode_on_policy_violation:
                print("[LoopRunner] Decision: enter_safe_mode → Safe-Mode aktiv.")
                self.mission_state.safe_mode = True
        # Weitere Decision-Typen können hier ergänzt werden

    def _execute_actions(self, actions: List[Dict[str, Any]]) -> None:
        if not actions:
            print("[LoopRunner] No actions to execute.")
            return
        self.action_executor.execute(actions, self.mission_state)

    def _on_error(self, reason: str) -> None:
        """
        Behandelt Loop-Fehler.
        """
        self.mission_state.error_count_recent += 1
        print(f"[LoopRunner] ERROR: {reason} (error_count_recent={self.mission_state.error_count_recent})")

        if self.mission_state.error_count_recent >= self.loop_config.max_consecutive_errors:
            print("[LoopRunner] Error limit reached → Safe-Mode aktiv.")
            self.mission_state.safe_mode = True

    def _should_stop(self) -> bool:
        """
        Prüft, ob der Loop beendet werden soll.
        """
        if self.mission_state.finished or self.mission_state.aborted:
            return True
        if self.mission_state.iteration >= self.loop_config.max_iterations:
            print("[LoopRunner] Max iterations reached.")
            return True
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def load_job_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sheratan SelfLoop Runner")
    parser.add_argument("job_file", type=str, help="Pfad zur LoopRunner-Job-JSON-Datei")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Actions nicht wirklich ausführen, nur loggen",
    )
    args = parser.parse_args(argv)

    job_path = Path(args.job_file)
    if not job_path.exists():
        print(f"[LoopRunner] Job file not found: {job_path}")
        return 1

    try:
        job_config = load_job_config(job_path)
    except Exception as e:
        print(f"[LoopRunner] Failed to load job config: {e}")
        return 1

    runner = LoopRunner(job_config=job_config, dry_run=args.dry_run)
    runner.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
