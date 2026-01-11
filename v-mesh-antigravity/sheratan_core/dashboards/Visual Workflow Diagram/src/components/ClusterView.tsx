import React, { useState, useRef, useEffect } from "react";

interface Module {
  id: string;
  name: string;
  subtitle?: string;
  details: string[];
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
  color: string;
  connections: string[];
}

interface Point3D {
  x: number;
  y: number;
  z: number;
}

interface Point2D {
  x: number;
  y: number;
  scale: number;
}

export function ClusterView() {
  const [rotation, setRotation] = useState({ x: -20, y: 30 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [selectedModule, setSelectedModule] = useState<
    string | null
  >(null);
  const [hoveredModule, setHoveredModule] = useState<
    string | null
  >(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const modules: Module[] = [
    {
      id: "api-gateway",
      name: "WebRelay / API Gateway",
      details: [
        "HTTPS / Broker",
        "Traefik + FastAPI",
        "traefik.yml · main.py · auth.py · routers/*",
      ],
      x: 0,
      y: -200,
      z: 0,
      width: 280,
      height: 100,
      color: "#00C3D4",
      connections: ["orchestrator"],
    },
    {
      id: "orchestrator",
      name: "Core Orchestrator",
      subtitle: "Backend Orchestrierung",
      details: [
        "Mission/Task API",
        "Policy (max iters, safe mode)",
        "Follow-up Job Generator",
        "Node.js Microservices — docker-compose.yml",
      ],
      x: 0,
      y: 0,
      z: 0,
      width: 300,
      height: 120,
      color: "#00C3D4",
      connections: [
        "message-bus",
        "event-store",
        "state-memory",
      ],
    },
    {
      id: "state-memory",
      name: "memory",
      details: [
        "Redis + Qdrant",
        "session.js · qdrant.js · redis.js",
        "Vektor / Session",
      ],
      x: 280,
      y: -50,
      z: -100,
      width: 220,
      height: 90,
      color: "#2E8099",
      connections: [],
    },
    {
      id: "message-bus",
      name: "Message Bus",
      subtitle: "Queue / Bus",
      details: [
        "enqueue job_id",
        "ack/nack + retry",
        "backoff / DLQ",
        "idempotency key",
      ],
      x: 0,
      y: 200,
      z: 100,
      width: 260,
      height: 100,
      color: "#00C3D4",
      connections: ["worker-pool"],
    },
    {
      id: "worker-pool",
      name: "Worker Pool",
      subtitle: "Worker: ai_assistent_codder",
      details: [
        "claim lease",
        "fetch job + context refs",
        "execute pipeline",
        "Prompt Builder + Validator",
        "codder_agent.py · core/* · ui/*",
      ],
      x: 350,
      y: 200,
      z: 0,
      width: 300,
      height: 130,
      color: "#00C3D4",
      connections: ["llm-backends", "event-store"],
    },
    {
      id: "event-store",
      name: "Unified Event Store",
      subtitle: "(SQLite + Chunks)",
      details: [
        "missions, tasks, jobs",
        "job_events / results",
        "locks / leases",
        "large payloads (chunks)",
        "content-addressed refs",
      ],
      x: -350,
      y: 200,
      z: -50,
      width: 280,
      height: 120,
      color: "#00C3D4",
      connections: ["mesh-sync"],
    },
    {
      id: "mesh-sync",
      name: "Mesh Sync Daemon",
      details: [
        "Distributed Sync",
        "Node Coordination",
        "Conflict Resolution",
        "Replication",
      ],
      x: -350,
      y: 380,
      z: 0,
      width: 260,
      height: 100,
      color: "#00C3D4",
      connections: [],
    },
    {
      id: "llm-backends",
      name: "LLM Backends",
      details: [
        "OpenAI · Ollama · llama-cpp",
        "WebRelay/OpenAI/Local",
        "timeouts, retries",
        "Konfig: .env · requirements.txt",
      ],
      x: 350,
      y: 400,
      z: -100,
      width: 240,
      height: 110,
      color: "#2E8099",
      connections: [],
    },
    {
      id: "observability",
      name: "Observability & Security",
      subtitle: "Metrics / Logs",
      details: [
        "Prometheus + Grafana",
        "prometheus.yml · grafana-dashboards.json",
        "Metrics Collection",
        "Security Monitoring",
      ],
      x: 0,
      y: 420,
      z: 150,
      width: 280,
      height: 110,
      color: "#2E8099",
      connections: [
        "orchestrator",
        "worker-pool",
        "message-bus",
      ],
    },
  ];

  const project3D = (point: Point3D): Point2D => {
    const perspective = 800;
    const scale = 1.2;

    const radX = (rotation.x * Math.PI) / 180;
    const radY = (rotation.y * Math.PI) / 180;

    // Rotate around Y axis
    let x = point.x * Math.cos(radY) + point.z * Math.sin(radY);
    let z =
      -point.x * Math.sin(radY) + point.z * Math.cos(radY);

    // Rotate around X axis
    let y = point.y * Math.cos(radX) - z * Math.sin(radX);
    z = point.y * Math.sin(radX) + z * Math.cos(radX);

    // Apply perspective
    const scaleFactor = perspective / (perspective + z);

    return {
      x: x * scaleFactor * scale + 800,
      y: y * scaleFactor * scale + 450,
      scale: scaleFactor,
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;
      setRotation({
        x: rotation.x + deltaY * 0.3,
        y: rotation.y + deltaX * 0.3,
      });
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const drawModule = (module: Module) => {
    const corners = [
      {
        x: module.x - module.width / 2,
        y: module.y - module.height / 2,
        z: module.z,
      },
      {
        x: module.x + module.width / 2,
        y: module.y - module.height / 2,
        z: module.z,
      },
      {
        x: module.x + module.width / 2,
        y: module.y + module.height / 2,
        z: module.z,
      },
      {
        x: module.x - module.width / 2,
        y: module.y + module.height / 2,
        z: module.z,
      },
      {
        x: module.x - module.width / 2,
        y: module.y - module.height / 2,
        z: module.z - 40,
      },
      {
        x: module.x + module.width / 2,
        y: module.y - module.height / 2,
        z: module.z - 40,
      },
      {
        x: module.x + module.width / 2,
        y: module.y + module.height / 2,
        z: module.z - 40,
      },
      {
        x: module.x - module.width / 2,
        y: module.y + module.height / 2,
        z: module.z - 40,
      },
    ];

    const projected = corners.map((c) => project3D(c));
    const center = project3D({
      x: module.x,
      y: module.y,
      z: module.z,
    });

    const isHovered = hoveredModule === module.id;
    const isSelected = selectedModule === module.id;

    // Calculate average z for depth sorting
    const avgZ =
      corners.reduce((sum, c) => {
        const radX = (rotation.x * Math.PI) / 180;
        const radY = (rotation.y * Math.PI) / 180;
        let x = c.x * Math.cos(radY) + c.z * Math.sin(radY);
        let z = -c.x * Math.sin(radY) + c.z * Math.cos(radY);
        let y = c.y * Math.cos(radX) - z * Math.sin(radX);
        z = c.y * Math.sin(radX) + z * Math.cos(radX);
        return sum + z;
      }, 0) / corners.length;

    return {
      avgZ,
      element: (
        <g
          key={module.id}
          className="cursor-pointer transition-all duration-200"
          onMouseEnter={() => setHoveredModule(module.id)}
          onMouseLeave={() => setHoveredModule(null)}
          onClick={() =>
            setSelectedModule(
              selectedModule === module.id ? null : module.id,
            )
          }
        >
          {/* Back face */}
          <path
            d={`M ${projected[4].x} ${projected[4].y} L ${projected[5].x} ${projected[5].y} L ${projected[6].x} ${projected[6].y} L ${projected[7].x} ${projected[7].y} Z`}
            fill="#070B16"
            stroke={isSelected ? module.color : "#1C3250"}
            strokeWidth={isSelected ? 2 : 1.2}
            opacity={0.4}
          />

          {/* Top face */}
          <path
            d={`M ${projected[0].x} ${projected[0].y} L ${projected[1].x} ${projected[1].y} L ${projected[5].x} ${projected[5].y} L ${projected[4].x} ${projected[4].y} Z`}
            fill="#0E172A"
            stroke={isSelected ? module.color : "#263551"}
            strokeWidth={isSelected ? 2 : 1}
            opacity={0.6}
          />

          {/* Right face */}
          <path
            d={`M ${projected[1].x} ${projected[1].y} L ${projected[2].x} ${projected[2].y} L ${projected[6].x} ${projected[6].y} L ${projected[5].x} ${projected[5].y} Z`}
            fill="#0B1020"
            stroke={isSelected ? module.color : "#263551"}
            strokeWidth={isSelected ? 2 : 1}
            opacity={0.5}
          />

          {/* Front face */}
          <path
            d={`M ${projected[0].x} ${projected[0].y} L ${projected[1].x} ${projected[1].y} L ${projected[2].x} ${projected[2].y} L ${projected[3].x} ${projected[3].y} Z`}
            fill="#070B16"
            stroke={
              isSelected
                ? module.color
                : isHovered
                  ? module.color
                  : "#1C3250"
            }
            strokeWidth={isSelected ? 2.5 : isHovered ? 2 : 1.8}
            opacity={isHovered || isSelected ? 0.9 : 0.7}
          />

          {/* Glow effect when hovered or selected */}
          {(isHovered || isSelected) && (
            <path
              d={`M ${projected[0].x} ${projected[0].y} L ${projected[1].x} ${projected[1].y} L ${projected[2].x} ${projected[2].y} L ${projected[3].x} ${projected[3].y} Z`}
              fill={module.color}
              fillOpacity="0.12"
              stroke={module.color}
              strokeWidth={isSelected ? 3 : 2}
              filter="url(#glow)"
            />
          )}

          {/* Text */}
          <text
            x={center.x}
            y={center.y - 10}
            textAnchor="middle"
            fill="#e5f4ff"
            fontSize={13 * center.scale}
            className="pointer-events-none select-none font-['Inter',sans-serif]"
          >
            {module.name}
          </text>

          {module.subtitle && (
            <text
              x={center.x}
              y={center.y + 8}
              textAnchor="middle"
              fill="#9aa4c6"
              fontSize={11 * center.scale}
              className="pointer-events-none select-none font-['Inter',sans-serif]"
            >
              {module.subtitle}
            </text>
          )}

          {/* Connection indicator */}
          {isHovered && module.connections.length > 0 && (
            <circle
              cx={center.x}
              cy={center.y + 40}
              r={4}
              fill={module.color}
              opacity={0.8}
            >
              <animate
                attributeName="r"
                values="4;6;4"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </circle>
          )}
        </g>
      ),
    };
  };

  const drawConnection = (fromId: string, toId: string) => {
    const fromModule = modules.find((m) => m.id === fromId);
    const toModule = modules.find((m) => m.id === toId);
    if (!fromModule || !toModule) return null;

    const from = project3D({
      x: fromModule.x,
      y: fromModule.y,
      z: fromModule.z,
    });
    const to = project3D({
      x: toModule.x,
      y: toModule.y,
      z: toModule.z,
    });

    const isHighlighted =
      hoveredModule === fromId ||
      hoveredModule === toId ||
      selectedModule === fromId ||
      selectedModule === toId;

    return (
      <line
        key={`${fromId}-${toId}`}
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        stroke={isHighlighted ? fromModule.color : "#2E8099"}
        strokeWidth={isHighlighted ? 2.5 : 1.5}
        strokeDasharray="5 4"
        opacity={isHighlighted ? 0.9 : 0.3}
        className="transition-all duration-300"
      />
    );
  };

  const sortedModules = modules
    .map((module) => drawModule(module))
    .sort((a, b) => a.avgZ - b.avgZ);

  const selectedModuleData = modules.find(
    (m) => m.id === selectedModule,
  );

  return (
    <div
      ref={containerRef}
      className="relative w-full h-screen"
    >
      {/* Title */}
      <div className="absolute top-8 left-8 z-10">
        <h1 className="text-[#e5f4ff] text-2xl mb-2 font-['Inter',sans-serif]">
          SHERATAN CORE v1 mdash; RUNTIME FLOW
        </h1>
        <p className="text-[#9aa4c6] font-['Inter',sans-serif]">
          INTERAKTIVE ÜBERSICHT mdash; VON COCKPIT BIS LLM
          BACKENDS
        </p>
      </div>

      {/* Controls */}
      <div className="absolute top-8 right-8 z-10 flex gap-3">
        <button
          onClick={() => setRotation({ x: -20, y: 30 })}
          className="px-4 py-2 bg-[#070B16] border border-[#1C3250] text-[#9aa4c6] rounded hover:border-[#00C3D4] hover:text-[#bff8ff] transition-all"
        >
          Reset View
        </button>
        <button
          onClick={() => setRotation({ x: 0, y: 0 })}
          className="px-4 py-2 bg-[#070B16] border border-[#1C3250] text-[#9aa4c6] rounded hover:border-[#00C3D4] hover:text-[#bff8ff] transition-all"
        >
          Front
        </button>
        <button
          onClick={() => setRotation({ x: -90, y: 0 })}
          className="px-4 py-2 bg-[#070B16] border border-[#1C3250] text-[#9aa4c6] rounded hover:border-[#00C3D4] hover:text-[#bff8ff] transition-all"
        >
          Top
        </button>
      </div>

      {/* 3D Canvas */}
      <div
        className="w-full h-full relative"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isDragging ? "grabbing" : "grab" }}
      >
        {/* Radial Background Glow */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
            style={{
              width: "1040px",
              height: "1040px",
              background:
                "radial-gradient(circle, rgba(0,195,212,0.4) 0%, rgba(0,195,212,0.12) 35%, rgba(0,195,212,0) 100%)",
              opacity: 0.4,
            }}
          />
        </div>

        {/* Concentric Circles */}
        <svg
          className="absolute inset-0 pointer-events-none"
          width="100%"
          height="100%"
          viewBox="0 0 1600 900"
        >
          <defs>
            <filter id="glow">
              <feGaussianBlur
                stdDeviation="3"
                result="coloredBlur"
              />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <circle
            cx="800"
            cy="450"
            r="360"
            fill="none"
            stroke="#123248"
            strokeWidth="1.4"
            strokeDasharray="6 6"
            opacity="0.7"
          />
          <circle
            cx="800"
            cy="450"
            r="260"
            fill="none"
            stroke="#123248"
            strokeWidth="1.4"
            strokeDasharray="3 12"
            opacity="0.7"
          />
        </svg>

        <svg className="w-full h-full" viewBox="0 0 1600 900">
          <defs>
            <filter id="glow">
              <feGaussianBlur
                stdDeviation="4"
                result="coloredBlur"
              />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Connections */}
          <g className="connections">
            {modules.flatMap((module) =>
              module.connections.map((connId) =>
                drawConnection(module.id, connId),
              ),
            )}
          </g>

          {/* Modules (depth-sorted) */}
          {sortedModules.map((item) => item.element)}
        </svg>
      </div>

      {/* Help Text */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[#5e6fa0] text-center font-['Inter',sans-serif] z-10">
        Drag to rotate • Click modules for details
      </div>

      {/* Details Panel */}
      {selectedModuleData && (
        <div className="absolute bottom-8 right-8 w-96 bg-[#070B16] border border-[#1C3250] rounded-lg p-6 z-10 shadow-2xl">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-[#e5f4ff] mb-1 font-['Inter',sans-serif]">
                {selectedModuleData.name}
              </h3>
              {selectedModuleData.subtitle && (
                <p className="text-[#9aa4c6] text-sm font-['Inter',sans-serif]">
                  {selectedModuleData.subtitle}
                </p>
              )}
            </div>
            <button
              onClick={() => setSelectedModule(null)}
              className="text-[#9aa4c6] hover:text-[#bff8ff] transition-colors"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-2">
            {selectedModuleData.details.map((detail, idx) => (
              <div
                key={idx}
                className="text-[#7b86ae] text-sm font-['Inter',sans-serif] border-l-2 border-[#00C3D4]/30 pl-3"
              >
                {detail}
              </div>
            ))}
          </div>

          {selectedModuleData.connections.length > 0 && (
            <div className="mt-4 pt-4 border-t border-[#1C3250]">
              <p className="text-[#9aa4c6] text-sm mb-2 font-['Inter',sans-serif]">
                Connections:
              </p>
              <div className="flex flex-wrap gap-2">
                {selectedModuleData.connections.map(
                  (connId) => {
                    const connModule = modules.find(
                      (m) => m.id === connId,
                    );
                    return (
                      <button
                        key={connId}
                        onClick={() =>
                          setSelectedModule(connId)
                        }
                        className="px-3 py-1 bg-[#00C3D4]/10 border border-[#00C3D4]/30 text-[#bff8ff] rounded text-sm hover:bg-[#00C3D4]/20 transition-all font-['Inter',sans-serif]"
                      >
                        {connModule?.name}
                      </button>
                    );
                  },
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}