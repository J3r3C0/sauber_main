import React, { useEffect, useState } from "react";

const CORE_BASE_URL = "http://localhost:8001";
const WEBRELAY_BASE_URL = "http://localhost:3000";
const BACKEND_BASE_URL = "http://localhost:8000";  // Boss directive 4.1


type StatusResponse = {
  status: string;
  missions?: number;
};

type Mission = {
  id: string;
  title: string;
  description?: string;
  tags?: string[];
};

type Task = {
  id: string;
  mission_id: string;
  name: string;
  description?: string;
  kind?: string;
};

type JobStatus = "pending" | "dispatched" | "done" | "failed" | string;

type Job = {
  id: string;
  task_id: string;
  status: JobStatus;
  payload?: any;
  result?: any;
  created_at?: string;
  updated_at?: string;
};

type WebrelayHealth = {
  status?: string;
  healthy?: boolean;
};

type LlmCallResponse =
  | {
    type: "lcp";
    summary?: string;
    commentary?: string;
    action?: string;
    new_jobs?: any[];
    convoUrl?: string;
  }
  | {
    type: "plain";
    summary?: string;
  }
  | any;

type PageId = "overview" | "missions" | "jobs" | "console";

const SheratanDashboard: React.FC = () => {
  const [activePage, setActivePage] = useState<PageId>("overview");

  // Core status
  const [coreStatus, setCoreStatus] = useState<StatusResponse | null>(null);
  const [coreStatusError, setCoreStatusError] = useState<string | null>(null);

  // Webrelay status
  const [webrelayStatus, setWebrelayStatus] = useState<WebrelayHealth | null>(
    null
  );
  const [webrelayStatusError, setWebrelayStatusError] = useState<string | null>(
    null
  );

  // Missions / Tasks / Jobs
  const [missions, setMissions] = useState<Mission[]>([]);
  const [missionsError, setMissionsError] = useState<string | null>(null);

  const [tasks, setTasks] = useState<Task[]>([]);
  const [tasksError, setTasksError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(
    null
  );
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const selectedMission: Mission | undefined = missions.find(
    (m) => m.id === selectedMissionId
  );
  const selectedJob: Job | undefined = jobs.find((j) => j.id === selectedJobId);

  // Console
  const [prompt, setPrompt] = useState<string>("");
  const [consoleTab, setConsoleTab] = useState<"coreFlow" | "directLLM">(
    "coreFlow"
  );
  const [consoleOutput, setConsoleOutput] = useState<string>("Awaiting input…");
  const [consoleLoading, setConsoleLoading] = useState<boolean>(false);
  const [consoleError, setConsoleError] = useState<string | null>(null);

  // Filters
  const [jobStatusFilter, setJobStatusFilter] = useState<JobStatus | "all">(
    "all"
  );

  // Mission creation form
  const [newMissionTitle, setNewMissionTitle] = useState("");
  const [newMissionDescription, setNewMissionDescription] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [selfLoopMode, setSelfLoopMode] = useState(false);  // Boss directive 5.1

  // Helpers
  const handleFetchError = (err: any): string => {
    if (err instanceof Error) return err.message;
    try {
      return JSON.stringify(err);
    } catch {
      return String(err);
    }
  };

  // Data loader
  const loadCoreStatus = async () => {
    try {
      setCoreStatusError(null);
      const res = await fetch(`${CORE_BASE_URL}/api/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: StatusResponse = await res.json();
      setCoreStatus(data);
    } catch (err) {
      setCoreStatusError(handleFetchError(err));
      setCoreStatus(null);
    }
  };

  const loadWebrelayStatus = async () => {
    try {
      setWebrelayStatusError(null);
      const res = await fetch(`${WEBRELAY_BASE_URL}/health`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: WebrelayHealth = await res.json();
      setWebrelayStatus(data);
    } catch (err) {
      setWebrelayStatusError(handleFetchError(err));
      setWebrelayStatus(null);
    }
  };

  const loadMissions = async () => {
    try {
      setMissionsError(null);
      const res = await fetch(`${CORE_BASE_URL}/api/missions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Mission[] = await res.json();
      setMissions(data);
    } catch (err) {
      setMissionsError(handleFetchError(err));
      setMissions([]);
    }
  };

  const loadTasks = async () => {
    try {
      setTasksError(null);
      const res = await fetch(`${CORE_BASE_URL}/api/tasks`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Task[] = await res.json();
      setTasks(data);
    } catch (err) {
      setTasksError(handleFetchError(err));
      setTasks([]);
    }
  };

  const loadJobs = async () => {
    try {
      setJobsError(null);
      const res = await fetch(`${CORE_BASE_URL}/api/jobs`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Job[] = await res.json();
      setJobs(data);
    } catch (err) {
      setJobsError(handleFetchError(err));
      setJobs([]);
    }
  };

  const reloadAll = async () => {
    await Promise.all([
      loadCoreStatus(),
      loadWebrelayStatus(),
      loadMissions(),
      loadTasks(),
      loadJobs(),
    ]);
  };

  useEffect(() => {
    reloadAll();
    const interval = setInterval(() => {
      loadCoreStatus();
      loadWebrelayStatus();
      loadJobs();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Derived
  const openJobsCount = jobs.filter(
    (j) => j.status !== "done" && j.status !== "failed"
  ).length;

  const filteredJobs =
    jobStatusFilter === "all"
      ? jobs
      : jobs.filter((j) => j.status === jobStatusFilter);

  const missionTasks = selectedMissionId
    ? tasks.filter((t) => t.mission_id === selectedMissionId)
    : [];

  const missionTaskIds = new Set(missionTasks.map((t) => t.id));

  const missionJobs = selectedMissionId
    ? jobs.filter((j) => missionTaskIds.has(j.task_id))
    : [];

  // Actions

  const createMission = async (title: string, description?: string) => {
    const body = {
      title,
      description: description ?? "",
      metadata: {},
      tags: selfLoopMode ? ["self-loop"] : [],  // Boss directive 5.1
    };
    const res = await fetch(`${CORE_BASE_URL}/api/missions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Mission create failed: HTTP ${res.status}`);
    const mission: Mission = await res.json();
    await loadMissions();
    setSelectedMissionId(mission.id);
    return mission;
  };

  const createTask = async (
    missionId: string,
    name: string,
    kind: string,
    description?: string,
    params?: any
  ) => {
    const body = {
      name,
      description: description ?? "",
      kind,
      params: params ?? {},
    };
    const res = await fetch(
      `${CORE_BASE_URL}/api/missions/${missionId}/tasks`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    if (!res.ok) throw new Error(`Task create failed: HTTP ${res.status}`);
    const task: Task = await res.json();
    await loadTasks();
    return task;
  };

  const createJob = async (taskId: string, payload: any) => {
    const res = await fetch(`${CORE_BASE_URL}/api/tasks/${taskId}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    if (!res.ok) throw new Error(`Job create failed: HTTP ${res.status}`);
    const job: Job = await res.json();
    await loadJobs();
    return job;
  };

  const dispatchJob = async (jobId: string) => {
    const res = await fetch(
      `${CORE_BASE_URL}/api/jobs/${jobId}/dispatch`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error(`Dispatch failed: HTTP ${res.status}`);
    await loadJobs();
  };

  const syncJob = async (jobId: string): Promise<Job> => {
    const res = await fetch(
      `${CORE_BASE_URL}/api/jobs/${jobId}/sync`,
      {
        method: "POST",
      }
    );
    if (!res.ok) throw new Error(`Sync failed: HTTP ${res.status}`);
    const job: Job = await res.json();
    await loadJobs();
    return job;
  };

  const sendPromptCoreFlow = async () => {
    if (!prompt.trim()) {
      setConsoleError("Prompt darf nicht leer sein.");
      return;
    }
    setConsoleError(null);
    setConsoleLoading(true);
    setConsoleOutput("Starte Core Mission Flow…");

    try {
      const mission = await createMission(prompt.slice(0, 80), prompt);

      const task = await createTask(
        mission.id,
        "Agent Plan",
        "agent_plan",
        "Agent Plan Task aus Dashboard",
        { user_prompt: prompt }
      );

      const job = await createJob(task.id, { prompt });
      setSelectedJobId(job.id);

      await dispatchJob(job.id);
      setConsoleOutput(
        (prev) =>
          prev +
          `\n\nJob ${job.id} dispatched. Warte auf Resultat…`
      );

      // kurzes Polling
      let finalJob: Job | null = null;
      for (let i = 0; i < 10; i++) {
        const j = await syncJob(job.id);
        finalJob = j;
        if (j.status === "done" || j.status === "failed") break;
        await new Promise((res) => setTimeout(res, 1000));
      }

      if (!finalJob) throw new Error("Kein Resultat erhalten.");

      const result = finalJob.result ?? {};
      const commentary = result.commentary ?? "";
      const action = result.action ?? "";
      const newJobs = result.new_jobs ?? [];
      const convoUrl = result.convoUrl ?? result.convo_url ?? null;

      let text = `Mission: ${mission.title}\nTask: ${task.name}\nJob: ${finalJob.id}\nStatus: ${finalJob.status}\n\nResult:\n${JSON.stringify(
        result,
        null,
        2
      )}`;

      if (commentary || action || newJobs.length || convoUrl) {
        text += `\n\n--- LCP Ansicht ---`;
        if (commentary) text += `\nCommentary:\n${commentary}`;
        if (action) text += `\n\nAction:\n${action}`;
        if (newJobs.length)
          text += `\n\nNew Jobs:\n${JSON.stringify(newJobs, null, 2)}`;
        if (convoUrl) text += `\n\nConversation URL:\n${convoUrl}`;
      }

      setConsoleOutput(text);
    } catch (err) {
      setConsoleError(handleFetchError(err));
    } finally {
      setConsoleLoading(false);
    }
  };

  const sendPromptDirectLLM = async () => {
    if (!prompt.trim()) {
      setConsoleError("Prompt darf nicht leer sein.");
      return;
    }
    setConsoleError(null);
    setConsoleLoading(true);
    setConsoleOutput("Sende Prompt direkt an WebRelay…");

    try {
      const res = await fetch(`${WEBRELAY_BASE_URL}/api/llm/call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: LlmCallResponse = await res.json();

      if (data.type === "lcp") {
        let text = "Typ: LCP\n";
        if (data.summary) text += `\nSummary:\n${data.summary}`;
        if (data.commentary) text += `\n\nCommentary:\n${data.commentary}`;
        if (data.action) text += `\n\nAction:\n${data.action}`;
        if (data.new_jobs)
          text += `\n\nNew Jobs:\n${JSON.stringify(data.new_jobs, null, 2)}`;
        if ((data as any).convoUrl)
          text += `\n\nConversation URL: ${(data as any).convoUrl}`;
        setConsoleOutput(text);
      } else if (data.type === "plain") {
        setConsoleOutput(data.summary ?? JSON.stringify(data, null, 2));
      } else {
        setConsoleOutput(JSON.stringify(data, null, 2));
      }
    } catch (err) {
      setConsoleError(handleFetchError(err));
    } finally {
      setConsoleLoading(false);
    }
  };

  const handleConsoleSubmit = () => {
    if (consoleTab === "coreFlow") {
      void sendPromptCoreFlow();
    } else {
      void sendPromptDirectLLM();
    }
  };

  const handleKeyDownPrompt: React.KeyboardEventHandler<HTMLTextAreaElement> = (
    e
  ) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleConsoleSubmit();
    }
  };

  const renderStatusPill = (online: boolean | null, label: string) => {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span
          className={`h-2.5 w-2.5 rounded-full ${online === null
            ? "bg-gray-400"
            : online
              ? "bg-emerald-500"
              : "bg-red-500"
            }`}
        />
        <span>{label}</span>
      </div>
    );
  };

  // PAGES

  const renderOverview = () => {
    const coreOnline =
      coreStatus?.status === "ok" && coreStatusError === null;
    const webrelayOnline =
      (webrelayStatus?.status === "ok" || webrelayStatus?.healthy === true) &&
      webrelayStatusError === null;

    return (
      <div className="p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Core */}
          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-sm font-semibold text-slate-200">Core</h2>
              {renderStatusPill(coreOnline, coreOnline ? "Online" : "Offline")}
            </div>
            <p className="text-xs text-slate-400 mb-1">
              Missions: {coreStatus?.missions ?? "—"}
            </p>
            {coreStatusError && (
              <p className="text-xs text-red-400">{coreStatusError}</p>
            )}
          </div>

          {/* WebRelay */}
          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-sm font-semibold text-slate-200">
                WebRelay
              </h2>
              {renderStatusPill(
                webrelayOnline,
                webrelayOnline ? "Online" : "Offline"
              )}
            </div>
            <p className="text-xs text-slate-400 mb-1">LLM Bridge</p>
            {webrelayStatusError && (
              <p className="text-xs text-red-400">{webrelayStatusError}</p>
            )}
          </div>

          {/* Offene Jobs */}
          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
            <h2 className="text-sm font-semibold text-slate-200">
              Offene Jobs
            </h2>
            <p className="text-3xl font-bold text-sky-400 mt-2">
              {openJobsCount}
            </p>
            {jobsError && (
              <p className="text-xs text-red-400 mt-1">{jobsError}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Recent Missions */}
          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-sm font-semibold text-slate-200">
                Letzte Missions
              </h2>
              <span className="text-xs text-slate-500">
                {missions.length} total
              </span>
            </div>
            <div className="space-y-2 max-h-64 overflow-auto">
              {missions
                .slice()
                .reverse()
                .slice(0, 5)
                .map((m) => (
                  <button
                    key={m.id}
                    onClick={() => {
                      setActivePage("missions");
                      setSelectedMissionId(m.id);
                    }}
                    className="w-full text-left bg-slate-800/60 hover:bg-slate-800 border border-slate-700 rounded-xl px-3 py-2"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-slate-100">
                        {m.title}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        {m.id}
                      </span>
                    </div>
                    {m.description && (
                      <p className="text-xs text-slate-400 truncate">
                        {m.description}
                      </p>
                    )}
                  </button>
                ))}
              {missions.length === 0 && (
                <p className="text-xs text-slate-500">
                  Noch keine Missions vorhanden.
                </p>
              )}
            </div>
          </div>

          {/* Recent Jobs */}
          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-sm font-semibold text-slate-200">
                Letzte Jobs
              </h2>
              <span className="text-xs text-slate-500">
                {jobs.length} total
              </span>
            </div>
            <div className="max-h-64 overflow-auto">
              <table className="w-full text-xs text-slate-300">
                <thead>
                  <tr className="text-slate-500 border-b border-slate-700">
                    <th className="py-1 pr-2 text-left">Job</th>
                    <th className="py-1 pr-2 text-left">Task</th>
                    <th className="py-1 pr-2 text-left">Status</th>
                    <th className="py-1 pr-2 text-left">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs
                    .slice()
                    .reverse()
                    .slice(0, 10)
                    .map((j) => (
                      <tr
                        key={j.id}
                        className="border-b border-slate-800 hover:bg-slate-800/60 cursor-pointer"
                        onClick={() => {
                          setActivePage("jobs");
                          setSelectedJobId(j.id);
                        }}
                      >
                        <td className="py-1 pr-2">{j.id}</td>
                        <td className="py-1 pr-2">{j.task_id}</td>
                        <td className="py-1 pr-2">
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] bg-slate-800 border border-slate-600">
                            {j.status}
                          </span>
                        </td>
                        <td className="py-1 pr-2">
                          {j.updated_at ?? j.created_at ?? "—"}
                        </td>
                      </tr>
                    ))}
                  {jobs.length === 0 && (
                    <tr>
                      <td
                        colSpan={4}
                        className="py-2 text-center text-slate-500"
                      >
                        Keine Jobs vorhanden.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const handleMissionCreate = async () => {
    if (!newMissionTitle.trim()) {
      setCreateError("Titel darf nicht leer sein.");
      return;
    }
    setCreateError(null);
    setCreating(true);
    try {
      await createMission(newMissionTitle, newMissionDescription);
      setNewMissionTitle("");
      setNewMissionDescription("");
    } catch (err) {
      setCreateError(handleFetchError(err));
    } finally {
      setCreating(false);
    }
  };

  // Boss Directive 4.1: Standard Code Analysis Mission
  const handleStartCodeAnalysis = async () => {
    setCreateError(null);
    setCreating(true);
    try {
      const res = await fetch(`${BACKEND_BASE_URL}/api/missions/standard-code-analysis`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadMissions();
    } catch (err) {
      setCreateError(handleFetchError(err));
    } finally {
      setCreating(false);
    }
  };

  const renderMissionsPage = () => {

    return (
      <div className="flex h-full">
        {/* Left pane: Missions list + create */}
        <div className="w-1/3 border-r border-slate-800 p-4 space-y-4">
          <div>
            <div className="flex justify-between items-center mb-2">
              <h2 className="text-sm font-semibold text-slate-200">
                Missions
              </h2>
              <span className="text-xs text-slate-500">
                {missions.length} total
              </span>
            </div>
            <div className="space-y-1 max-h-[60vh] overflow-auto">
              {missions.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setSelectedMissionId(m.id)}
                  className={`w-full text-left rounded-xl px-3 py-2 text-xs border ${selectedMissionId === m.id
                    ? "border-sky-500 bg-sky-500/10"
                    : "border-slate-700 bg-slate-900/60 hover:bg-slate-800/80"
                    }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-slate-100">
                      {m.title}
                    </span>
                    <span className="text-[9px] text-slate-500">{m.id}</span>
                  </div>
                  {m.description && (
                    <p className="text-[11px] text-slate-400 line-clamp-2">
                      {m.description}
                    </p>
                  )}
                </button>
              ))}
              {missions.length === 0 && (
                <p className="text-xs text-slate-500">
                  Noch keine Missions vorhanden.
                </p>
              )}
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800">
            <h3 className="text-xs font-semibold text-slate-300 mb-2">
              Neue Mission
            </h3>
            <input
              className="w-full mb-2 rounded-lg bg-slate-900 border border-slate-700 text-xs px-2 py-1 text-slate-100 placeholder:text-slate-600"
              placeholder="Titel"
              value={newMissionTitle}
              onChange={(e) => setNewMissionTitle(e.target.value)}
            />
            <textarea
              className="w-full mb-2 rounded-lg bg-slate-900 border border-slate-700 text-xs px-2 py-1 text-slate-100 placeholder:text-slate-600"
              rows={3}
              placeholder="Beschreibung"
              value={newMissionDescription}
              onChange={(e) => setNewMissionDescription(e.target.value)}
            />
            {/* Boss Directive 5.1: Self-Loop Mode Toggle */}
            <label className="flex items-center gap-2 mb-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={selfLoopMode}
                onChange={(e) => setSelfLoopMode(e.target.checked)}
                className="rounded border-slate-600 bg-slate-800 text-emerald-500 focus:ring-emerald-500"
              />
              <span>🔄 Self-Loop Mode (A/B/C/D iterativ)</span>
            </label>
            <button
              onClick={handleMissionCreate}
              disabled={creating}
              className="w-full rounded-lg bg-sky-500 hover:bg-sky-400 text-xs font-semibold text-slate-900 py-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {creating ? "Erstelle…" : "Mission erstellen"}
            </button>
            {/* Boss Directive 4.1: Quick Start Code Analysis */}
            <button
              onClick={handleStartCodeAnalysis}
              disabled={creating}
              className="w-full mt-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white py-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {creating ? "Starte…" : "🚀 Start Code Analysis"}
            </button>
            {createError && (
              <p className="mt-1 text-[11px] text-red-400">{createError}</p>
            )}
          </div>
        </div>

        {/* Right pane: Details */}
        <div className="flex-1 p-4 space-y-4">
          {selectedMission ? (
            <>
              <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h2 className="text-sm font-semibold text-slate-100">
                      {selectedMission.title}
                    </h2>
                    {selectedMission.description && (
                      <p className="text-xs text-slate-400 mt-1">
                        {selectedMission.description}
                      </p>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500">
                    ID: {selectedMission.id}
                  </span>
                </div>
                {selectedMission.tags && selectedMission.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {selectedMission.tags.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 border border-slate-600 text-slate-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Mission Tasks */}
                <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-xs font-semibold text-slate-300">
                      Tasks
                    </h3>
                    <span className="text-[10px] text-slate-500">
                      {missionTasks.length} tasks
                    </span>
                  </div>
                  <div className="max-h-64 overflow-auto text-xs">
                    {missionTasks.length > 0 ? (
                      <table className="w-full">
                        <thead>
                          <tr className="text-slate-500 border-b border-slate-700">
                            <th className="py-1 pr-2 text-left">Name</th>
                            <th className="py-1 pr-2 text-left">Kind</th>
                            <th className="py-1 pr-2 text-left">ID</th>
                          </tr>
                        </thead>
                        <tbody>
                          {missionTasks.map((t) => (
                            <tr
                              key={t.id}
                              className="border-b border-slate-800 hover:bg-slate-800/60"
                            >
                              <td className="py-1 pr-2">{t.name}</td>
                              <td className="py-1 pr-2">{t.kind ?? "—"}</td>
                              <td className="py-1 pr-2 text-[10px] text-slate-500">
                                {t.id}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="text-xs text-slate-500">
                        Keine Tasks für diese Mission.
                      </p>
                    )}
                  </div>
                </div>

                {/* Mission Jobs */}
                <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-xs font-semibold text-slate-300">
                      Jobs dieser Mission
                    </h3>
                    <span className="text-[10px] text-slate-500">
                      {missionJobs.length} jobs
                    </span>
                  </div>
                  <div className="max-h-64 overflow-auto text-xs">
                    {missionJobs.length > 0 ? (
                      <table className="w-full">
                        <thead>
                          <tr className="text-slate-500 border-b border-slate-700">
                            <th className="py-1 pr-2 text-left">Job</th>
                            <th className="py-1 pr-2 text-left">Task</th>
                            <th className="py-1 pr-2 text-left">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {missionJobs.map((j) => (
                            <tr
                              key={j.id}
                              className="border-b border-slate-800 hover:bg-slate-800/60 cursor-pointer"
                              onClick={() => setSelectedJobId(j.id)}
                            >
                              <td className="py-1 pr-2">{j.id}</td>
                              <td className="py-1 pr-2">{j.task_id}</td>
                              <td className="py-1 pr-2">
                                <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] bg-slate-800 border border-slate-600">
                                  {j.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="text-xs text-slate-500">
                        Noch keine Jobs für diese Mission.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <p className="text-xs text-slate-500">
                Wähle links eine Mission aus oder erstelle eine neue.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderJobsPage = () => {
    return (
      <div className="flex h-full">
        {/* Top: Jobs table */}
        <div className="flex-1 flex flex-col p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Jobs</h2>
              <p className="text-[11px] text-slate-500">
                Gesamt: {jobs.length}
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <label htmlFor="job-status-filter" className="text-slate-400">Status:</label>
              <select
                id="job-status-filter"
                className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-100"
                value={jobStatusFilter}
                onChange={(e) =>
                  setJobStatusFilter(e.target.value as JobStatus | "all")
                }
              >
                <option value="all">Alle</option>
                <option value="pending">pending</option>
                <option value="dispatched">dispatched</option>
                <option value="done">done</option>
                <option value="failed">failed</option>
              </select>
            </div>
          </div>

          <div className="flex-1 min-h-0">
            <div className="h-full border border-slate-800 rounded-2xl bg-slate-900/60 overflow-auto">
              <table className="w-full text-xs text-slate-300">
                <thead className="sticky top-0 bg-slate-900">
                  <tr className="text-slate-500 border-b border-slate-700">
                    <th className="py-1 px-2 text-left">Job</th>
                    <th className="py-1 px-2 text-left">Task</th>
                    <th className="py-1 px-2 text-left">Status</th>
                    <th className="py-1 px-2 text-left">Created</th>
                    <th className="py-1 px-2 text-left">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredJobs.map((j) => (
                    <tr
                      key={j.id}
                      className={`border-b border-slate-800 hover:bg-slate-800/60 cursor-pointer ${selectedJobId === j.id ? "bg-slate-800/80" : ""
                        }`}
                      onClick={() => setSelectedJobId(j.id)}
                    >
                      <td className="py-1 px-2">{j.id}</td>
                      <td className="py-1 px-2">{j.task_id}</td>
                      <td className="py-1 px-2">
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] bg-slate-800 border border-slate-600">
                          {j.status}
                        </span>
                      </td>
                      <td className="py-1 px-2">
                        {j.created_at ?? "—"}
                      </td>
                      <td className="py-1 px-2">
                        {j.updated_at ?? "—"}
                      </td>
                    </tr>
                  ))}
                  {filteredJobs.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="py-2 text-center text-slate-500"
                      >
                        Keine Jobs für diesen Filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {jobsError && (
              <p className="mt-1 text-[11px] text-red-400">{jobsError}</p>
            )}
          </div>
        </div>

        {/* Right: Job details */}
        <div className="w-[40%] border-l border-slate-800 p-4 space-y-4">
          {selectedJob ? (
            <>
              <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-xs font-semibold text-slate-300">
                    Job Details
                  </h3>
                  <span className="text-[10px] text-slate-500">
                    {selectedJob.id}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Task:{" "}
                  <span className="font-mono text-slate-200">
                    {selectedJob.task_id}
                  </span>
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Status:{" "}
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] bg-slate-800 border border-slate-600">
                    {selectedJob.status}
                  </span>
                </p>
                <p className="text-[10px] text-slate-500 mt-1">
                  Created: {selectedJob.created_at ?? "—"}
                  <br />
                  Updated: {selectedJob.updated_at ?? "—"}
                </p>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => dispatchJob(selectedJob.id)}
                    className="flex-1 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-[11px] font-semibold text-slate-900 py-1.5"
                  >
                    Dispatch
                  </button>
                  <button
                    onClick={async () => {
                      const j = await syncJob(selectedJob.id);
                      setSelectedJobId(j.id);
                    }}
                    className="flex-1 rounded-lg bg-sky-500 hover:bg-sky-400 text-[11px] font-semibold text-slate-900 py-1.5"
                  >
                    Sync Result
                  </button>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
                <h4 className="text-[11px] font-semibold text-slate-300 mb-1">
                  Payload
                </h4>
                <pre className="text-[10px] text-slate-200 bg-slate-950/60 border border-slate-800 rounded-xl p-2 max-h-40 overflow-auto">
                  {JSON.stringify(selectedJob.payload ?? {}, null, 2)}
                </pre>
              </div>

              <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4">
                <h4 className="text-[11px] font-semibold text-slate-300 mb-1">
                  Result
                </h4>
                <pre className="text-[10px] text-slate-200 bg-slate-950/60 border border-slate-800 rounded-xl p-2 max-h-40 overflow-auto">
                  {JSON.stringify(selectedJob.result ?? {}, null, 2)}
                </pre>
              </div>
            </>
          ) : (
            <div className="h-full flex items-center justify-center">
              <p className="text-xs text-slate-500">
                Wähle links einen Job aus.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderConsolePage = () => {
    return (
      <div className="flex h-full">
        {/* Left: Prompt + tabs */}
        <div className="w-1/2 border-r border-slate-800 p-4 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 mb-2">
              Prompt
            </h2>
            <textarea
              className="w-full h-40 rounded-xl bg-slate-900 border border-slate-700 text-xs px-3 py-2 text-slate-100 placeholder:text-slate-600 resize-none"
              placeholder="Beschreibe eine Mission / Frage / Aufgabe… (Ctrl+Enter zum Senden)"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDownPrompt}
            />
          </div>

          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-3 space-y-3">
            <div className="flex mb-1">
              <button
                onClick={() => setConsoleTab("coreFlow")}
                className={`flex-1 text-xs py-1.5 rounded-lg ${consoleTab === "coreFlow"
                  ? "bg-sky-500 text-slate-900 font-semibold"
                  : "bg-slate-900 text-slate-300 border border-slate-700"
                  }`}
              >
                Core Mission Flow
              </button>
              <button
                onClick={() => setConsoleTab("directLLM")}
                className={`flex-1 text-xs py-1.5 rounded-lg ml-2 ${consoleTab === "directLLM"
                  ? "bg-sky-500 text-slate-900 font-semibold"
                  : "bg-slate-900 text-slate-300 border border-slate-700"
                  }`}
              >
                Direkter LLM Call
              </button>
            </div>
            <p className="text-[11px] text-slate-400">
              {consoleTab === "coreFlow" ? (
                <>
                  Erzeugt eine Mission → Task → Job im Core und dispatcht +
                  synced den Job. Ideal für Agent-Plan-Experimente.
                </>
              ) : (
                <>
                  Sendet den Prompt direkt an WebRelay (
                  <code className="text-[10px]">/api/llm/call</code>).
                </>
              )}
            </p>
            <button
              onClick={handleConsoleSubmit}
              disabled={consoleLoading}
              className="w-full rounded-lg bg-sky-500 hover:bg-sky-400 text-xs font-semibold text-slate-900 py-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {consoleLoading ? "Sende…" : "Prompt ausführen (Ctrl+Enter)"}
            </button>
            {consoleError && (
              <p className="text-[11px] text-red-400">{consoleError}</p>
            )}
          </div>
        </div>

        {/* Right: Output */}
        <div className="flex-1 p-4">
          <div className="bg-slate-900/60 border border-slate-700 rounded-2xl p-4 h-full flex flex-col">
            <h2 className="text-sm font-semibold text-slate-200 mb-2">
              Output
            </h2>
            <pre className="flex-1 text-[10px] text-slate-100 bg-slate-950/60 border border-slate-800 rounded-xl p-3 overflow-auto whitespace-pre-wrap">
              {consoleOutput}
            </pre>
          </div>
        </div>
      </div>
    );
  };

  // MAIN RENDER

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex">
      {/* Sidebar */}
      <aside className="w-52 border-r border-slate-800 bg-slate-950/80 flex flex-col">
        <div className="px-4 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-xl bg-sky-500/80 shadow-lg shadow-sky-500/40 flex items-center justify-center text-slate-950 font-black text-lg">
              S
            </div>
            <div>
              <div className="text-xs font-semibold tracking-wide">
                SHERATAN
              </div>
              <div className="text-[10px] text-slate-500">
                Core Control Center
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 text-xs">
          <button
            className={`w-full text-left px-3 py-2 rounded-lg ${activePage === "overview"
              ? "bg-slate-800 text-sky-400"
              : "text-slate-300 hover:bg-slate-900"
              }`}
            onClick={() => setActivePage("overview")}
          >
            Overview
          </button>
          <button
            className={`w-full text-left px-3 py-2 rounded-lg ${activePage === "missions"
              ? "bg-slate-800 text-sky-400"
              : "text-slate-300 hover:bg-slate-900"
              }`}
            onClick={() => setActivePage("missions")}
          >
            Missions
          </button>
          <button
            className={`w-full text-left px-3 py-2 rounded-lg ${activePage === "jobs"
              ? "bg-slate-800 text-sky-400"
              : "text-slate-300 hover:bg-slate-900"
              }`}
            onClick={() => setActivePage("jobs")}
          >
            Job Queue
          </button>
          <button
            className={`w-full text-left px-3 py-2 rounded-lg ${activePage === "console"
              ? "bg-slate-800 text-sky-400"
              : "text-slate-300 hover:bg-slate-900"
              }`}
            onClick={() => setActivePage("console")}
          >
            LLM Console
          </button>
        </nav>

        <div className="px-3 py-3 border-t border-slate-800 text-[10px] text-slate-500">
          <button
            className="w-full rounded-lg border border-slate-700 text-slate-300 py-1.5 text-[10px] hover:bg-slate-900"
            onClick={reloadAll}
          >
            Reload data
          </button>
          <p className="mt-2">
            Core:{" "}
            {coreStatus?.status === "ok" ? (
              <span className="text-emerald-400">online</span>
            ) : (
              <span className="text-red-400">offline</span>
            )}
          </p>
          <p>
            WebRelay:{" "}
            {webrelayStatus &&
              (webrelayStatus.status === "ok" || webrelayStatus.healthy) ? (
              <span className="text-emerald-400">online</span>
            ) : (
              <span className="text-red-400">offline</span>
            )}
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-12 border-b border-slate-800 flex items-center justify-between px-4">
          <div>
            <h1 className="text-sm font-semibold text-slate-100">
              {activePage === "overview" && "Overview"}
              {activePage === "missions" && "Missions"}
              {activePage === "jobs" && "Job Queue"}
              {activePage === "console" && "LLM Console"}
            </h1>
            <p className="text-[10px] text-slate-500">
              Sheratan Agent Workspace · Core v2
            </p>
          </div>
        </header>

        {/* Page body */}
        <section className="flex-1 min-h-0">
          {activePage === "overview" && renderOverview()}
          {activePage === "missions" && renderMissionsPage()}
          {activePage === "jobs" && renderJobsPage()}
          {activePage === "console" && renderConsolePage()}
        </section>
      </main>
    </div>
  );
};

export default SheratanDashboard;
