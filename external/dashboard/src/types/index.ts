// Missions & Jobs
export type MissionStatus = "planned" | "running" | "completed" | "failed";
export type JobStatus = "queued" | "working" | "done" | "error" | "running" | "completed" | "failed" | "pending";
export type JobType = "analysis" | "build" | "relay" | "trading" | "mesh" | string;

export interface Mission {
  id: string;
  name: string;
  status: MissionStatus;
  createdAt: string;
  lastUpdate: string;
  priority: "low" | "normal" | "high";
  progress: number;
  jobsTotal: number;
  jobsCompleted: number;
  tags?: string[];
  metadata?: {
    [key: string]: any;
  };
}

export interface Job {
  id: string;
  missionId: string;
  agent: string;
  type: JobType;
  status: JobStatus;
  startedAt?: string;
  finishedAt?: string;
  duration?: number;
  error?: string;
  payload?: {
    loop_state?: LoopState;
    [key: string]: any;
  };
  result?: {
    text?: string;
    output?: string;
    [key: string]: any;
  };
}

// Task
export interface Task {
  id: string;
  missionId: string;
  name: string;
  kind?: string;
  status?: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
  updatedAt?: string;
}

// Self-Loop State
export interface LoopState {
  iteration: number;
  history_summary: string;
  open_questions: string[];
  constraints: string[];
}

export interface SelfLoopParsedSections {
  A: string; // Standortanalyse
  B: string; // Nächster Schritt
  C: string; // Umsetzung
  D: string; // Vorschlag für nächsten Loop
}

// Mesh & Nodes
export type NodeStatus = "online" | "offline" | "degraded";
export type NodeRole = "core" | "relay" | "worker" | "trader";

export interface MeshNode {
  id: string;
  name: string;
  role: NodeRole;
  status: NodeStatus;
  ip: string;
  port: number;
  latency: number;
  score: number;
  lastSeen: string;
  endpoints: string[];
}

// Trader
export interface TradePosition {
  id: string;
  symbol: string;
  side: "long" | "short";
  entry: number;
  current: number;
  size: number;
  pnl: number;
  pnlPercent: number;
}

export interface EquityPoint {
  timestamp: string;
  value: number;
}

// Chat
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  name: string;
  projectId?: string;
  lastMessage: string;
  updatedAt: string;
  messageCount: number;
}

// Projects
export interface Project {
  id: string;
  name: string;
  path: string;
  status: "active" | "inactive";
  lastAccess: string;
  fileCount: number;
}

export interface FileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileNode[];
}

// System Health
export type ServiceStatus = "up" | "down" | "degraded";

export interface Service {
  name: string;
  port: number;
  status: ServiceStatus;
  uptime: string;
  lastCheck: string;
}

export interface SystemMetrics {
  cpu: number;
  memory: number;
  queueLength: number;
  errorRate: number;
}

// Notifications & Events
export type NotificationType = "error" | "warning" | "info" | "success";
export type NotificationCategory = "worker" | "mesh" | "trader" | "selfloop" | "api" | "mission";

export interface Notification {
  id: string;
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

// Logs
export type LogLevel = "debug" | "info" | "warn" | "error";
export type LogSource = "selfloop" | "mesh" | "trader" | "relay" | "core";

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  source: LogSource;
  message: string;
  metadata?: Record<string, any>;
}

// Model Info
export interface ModelInfo {
  name: string;
  type: "gguf" | "gpt-relay" | "mistral" | "anthropic";
  tokensUsed: number;
  tokensPerSecond: number;
  temperature: number;
  contextSize: number;
  systemPrompt: string;
  routing: string;
}

// System Status
export interface SystemStatus {
  selfloopState: "running" | "degraded" | "stopped";
  activeModel: string;
  meshNodesOnline: number;
  meshNodesTotal: number;
  jobsInQueue: number;
  unreadAlerts: number;
}

// Service Dependencies
export interface ServiceNode {
  id: string;
  name: string;
  type: "core" | "engine" | "worker" | "relay";
  status: "active" | "inactive" | "error";
  dependencies: string[];
}
