import React, { useState, useEffect } from 'react';

interface Lane {
  id: string;
  name: string;
  color: string;
  y: number;
  height: number;
}

interface Box {
  id: string;
  lane: string;
  title: string;
  items: string[];
  x: number;
  width: number;
  color: string;
}

interface FlowStep {
  from: string;
  to: string;
  step: number;
  path: string;
}

export function WorkflowDiagram() {
  const [animatedStep, setAnimatedStep] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [hoveredBox, setHoveredBox] = useState<string | null>(null);

  const lanes: Lane[] = [
    { id: 'core', name: 'Core (Orchestrator / API)', color: 'from-slate-700 to-slate-800', y: 20, height: 160 },
    { id: 'job', name: 'Job Plane (Queue + DB)', color: 'from-slate-600 to-slate-700', y: 200, height: 180 },
    { id: 'worker', name: 'Worker Plane (Prompt → LLM → Actions)', color: 'from-slate-700 to-slate-800', y: 400, height: 170 }
  ];

  const boxes: Box[] = [
    {
      id: 'orchestrator',
      lane: 'core',
      title: 'Core Orchestrator',
      items: ['Mission/Task API', 'Policy (max iters, safe mode)', 'Follow-up Job Generator'],
      x: 60,
      width: 240,
      color: 'from-blue-500 to-blue-700'
    },
    {
      id: 'context-builder',
      lane: 'core',
      title: 'Context Builder',
      items: ['Collect state + progress', 'Pull memory/artifacts', 'Produce ContextPacket'],
      x: 340,
      width: 240,
      color: 'from-indigo-500 to-indigo-700'
    },
    {
      id: 'state-memory',
      lane: 'core',
      title: 'State & Memory',
      items: ['mission_state', 'progress log', 'summaries / exemplars'],
      x: 620,
      width: 340,
      color: 'from-purple-500 to-purple-700'
    },
    {
      id: 'job-db',
      lane: 'job',
      title: 'Job DB (Source of truth)',
      items: ['missions, tasks, jobs', 'job_events / results', 'locks / leases'],
      x: 60,
      width: 240,
      color: 'from-emerald-500 to-emerald-700'
    },
    {
      id: 'queue',
      lane: 'job',
      title: 'Queue / Bus',
      items: ['enqueue job_id', 'ack/nack + retry', 'backoff / DLQ', 'idempotency key'],
      x: 340,
      width: 240,
      color: 'from-teal-500 to-teal-700'
    },
    {
      id: 'artifact-store',
      lane: 'job',
      title: 'Artifact Store',
      items: ['large payloads (chunks)', 'files, screenshots, logs', 'content-addressed refs', 'retention policies'],
      x: 620,
      width: 340,
      color: 'from-cyan-500 to-cyan-700'
    },
    {
      id: 'worker',
      lane: 'worker',
      title: 'Worker',
      items: ['claim lease', 'fetch job + context refs', 'execute pipeline'],
      x: 60,
      width: 220,
      color: 'from-orange-500 to-orange-700'
    },
    {
      id: 'prompt-builder',
      lane: 'worker',
      title: 'Prompt Builder + Validator',
      items: ['build prompt', 'validate structured response', 'safe-mode on violation'],
      x: 310,
      width: 220,
      color: 'from-amber-500 to-amber-700'
    },
    {
      id: 'llm-provider',
      lane: 'worker',
      title: 'LLM Provider',
      items: ['WebRelay/OpenAI/Local', 'timeouts, retries', 'cost metrics'],
      x: 560,
      width: 180,
      color: 'from-rose-500 to-rose-700'
    },
    {
      id: 'action-executor',
      lane: 'worker',
      title: 'Action Executor',
      items: ['filesystem/web tools', 'emit results/events', 'attach artifacts'],
      x: 770,
      width: 190,
      color: 'from-pink-500 to-pink-700'
    }
  ];

  const flowSteps: FlowStep[] = [
    { from: 'orchestrator', to: 'context-builder', step: 1, path: 'M 300 95 L 340 95' },
    { from: 'context-builder', to: 'state-memory', step: 2, path: 'M 580 95 L 620 95' },
    { from: 'orchestrator', to: 'job-db', step: 3, path: 'M 180 135 L 180 220' },
    { from: 'job-db', to: 'queue', step: 4, path: 'M 300 290 L 340 290' },
    { from: 'queue', to: 'worker', step: 5, path: 'M 460 340 L 460 380 L 170 380 L 170 420' },
    { from: 'worker', to: 'job-db', step: 6, path: 'M 170 490 L 170 360' },
    { from: 'worker', to: 'artifact-store', step: 7, path: 'M 210 490 L 210 380 L 790 380 L 790 360' },
    { from: 'worker', to: 'prompt-builder', step: 8, path: 'M 280 490 L 310 490' },
    { from: 'prompt-builder', to: 'llm-provider', step: 9, path: 'M 530 490 L 560 490' },
    { from: 'llm-provider', to: 'action-executor', step: 10, path: 'M 740 490 L 770 490' },
    { from: 'action-executor', to: 'job-db', step: 11, path: 'M 865 550 L 865 590 L 180 590 L 180 360' },
    { from: 'artifact-store', to: 'artifact-store', step: 12, path: 'M 960 290 L 1000 290 L 1000 290' },
    { from: 'job-db', to: 'context-builder', step: 13, path: 'M 180 220 L 180 180 L 420 180 L 420 135' }
  ];

  useEffect(() => {
    if (isAnimating) {
      const timer = setInterval(() => {
        setAnimatedStep(prev => {
          if (prev >= flowSteps.length) {
            setIsAnimating(false);
            return 0;
          }
          return prev + 1;
        });
      }, 800);
      return () => clearInterval(timer);
    }
  }, [isAnimating, flowSteps.length]);

  const getBoxPosition = (boxId: string) => {
    const box = boxes.find(b => b.id === boxId);
    const lane = lanes.find(l => l.id === box?.lane);
    if (!box || !lane) return { x: 0, y: 0 };
    return { x: box.x + box.width / 2, y: lane.y + 75 };
  };

  return (
    <div className="relative">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-slate-300">
          <p>Loop: Core erzeugt Job → Queue → Worker baut Prompt → LLM → Actions → Result/Event → neuer Job …</p>
        </div>
        <button
          onClick={() => {
            setAnimatedStep(0);
            setIsAnimating(true);
          }}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Animation starten
        </button>
      </div>

      <svg
        viewBox="0 0 1080 650"
        className="w-full h-auto"
        style={{ minHeight: '650px' }}
      >
        <defs>
          <marker
            id="flow-arrow"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#3b82f6" />
          </marker>

          <marker
            id="flow-arrow-active"
            markerWidth="12"
            markerHeight="12"
            refX="10"
            refY="4"
            orient="auto"
          >
            <polygon points="0 0, 12 4, 0 8" fill="#22d3ee" />
          </marker>

          <filter id="box-shadow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
            <feOffset dx="4" dy="6" result="offsetblur"/>
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.4"/>
            </feComponentTransfer>
            <feMerge>
              <feMergeNode/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          <filter id="glow-active">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {boxes.map(box => (
            <linearGradient key={`grad-${box.id}`} id={`grad-box-${box.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={`var(--${box.color.split(' ')[0].replace('from-', '')})`} />
              <stop offset="100%" stopColor={`var(--${box.color.split(' ')[2].replace('to-', '')})`} />
            </linearGradient>
          ))}
        </defs>

        {/* Swimlanes */}
        {lanes.map(lane => (
          <g key={lane.id}>
            <rect
              x="20"
              y={lane.y}
              width="1040"
              height={lane.height}
              fill="url(#lane-gradient)"
              className="fill-slate-800/30"
              stroke="#475569"
              strokeWidth="1"
              rx="8"
            />
            <text
              x="35"
              y={lane.y + 25}
              fill="white"
              className="select-none"
            >
              {lane.name}
            </text>
          </g>
        ))}

        {/* Flow connections */}
        <g className="flow-connections">
          {flowSteps.map((flow, idx) => {
            const isActive = isAnimating && idx < animatedStep;
            const isCurrent = isAnimating && idx === animatedStep - 1;
            
            return (
              <g key={idx}>
                <path
                  d={flow.path}
                  fill="none"
                  stroke={isCurrent ? '#22d3ee' : isActive ? '#3b82f6' : '#475569'}
                  strokeWidth={isCurrent ? 4 : isActive ? 3 : 2}
                  markerEnd={isCurrent ? 'url(#flow-arrow-active)' : isActive ? 'url(#flow-arrow)' : 'url(#flow-arrow)'}
                  opacity={isCurrent ? 1 : isActive ? 0.8 : 0.3}
                  className="transition-all duration-500"
                  filter={isCurrent ? 'url(#glow-active)' : 'none'}
                />
                <circle
                  cx={flow.path.split(' ')[1]}
                  cy={flow.path.split(' ')[2]}
                  r={isCurrent ? 8 : 6}
                  fill={isCurrent ? '#22d3ee' : isActive ? '#3b82f6' : '#64748b'}
                  opacity={isCurrent ? 1 : 0.7}
                  filter={isCurrent ? 'url(#glow-active)' : 'none'}
                >
                  {isCurrent && (
                    <animate
                      attributeName="r"
                      values="6;10;6"
                      dur="1s"
                      repeatCount="indefinite"
                    />
                  )}
                </circle>
                <text
                  x={parseInt(flow.path.split(' ')[1]) + 10}
                  y={parseInt(flow.path.split(' ')[2]) - 10}
                  fill={isCurrent ? '#22d3ee' : isActive ? '#60a5fa' : '#94a3b8'}
                  className="select-none"
                >
                  {flow.step}
                </text>
              </g>
            );
          })}
        </g>

        {/* Boxes */}
        {boxes.map(box => {
          const lane = lanes.find(l => l.id === box.lane);
          if (!lane) return null;

          const y = lane.y + 50;
          const isHovered = hoveredBox === box.id;
          
          // Check if this box is active in animation
          const isActive = isAnimating && flowSteps.slice(0, animatedStep).some(
            step => step.from === box.id || step.to === box.id
          );

          return (
            <g
              key={box.id}
              onMouseEnter={() => setHoveredBox(box.id)}
              onMouseLeave={() => setHoveredBox(null)}
              className="cursor-pointer"
              style={{
                transform: isHovered ? 'scale(1.02)' : 'scale(1)',
                transformOrigin: `${box.x + box.width/2}px ${y + 50}px`,
                transition: 'transform 0.2s ease'
              }}
            >
              <rect
                x={box.x}
                y={y}
                width={box.width}
                height={100}
                rx="10"
                className={`${box.color} fill-current`}
                filter="url(#box-shadow)"
                stroke={isActive ? '#22d3ee' : isHovered ? '#cbd5e1' : '#1e293b'}
                strokeWidth={isActive ? 3 : isHovered ? 2.5 : 1.5}
                opacity={isHovered || isActive ? 1 : 0.85}
              />
              
              {/* Highlight effect */}
              <rect
                x={box.x}
                y={y}
                width={box.width}
                height={30}
                rx="10"
                fill="white"
                opacity="0.15"
                pointerEvents="none"
              />

              {isActive && (
                <rect
                  x={box.x}
                  y={y}
                  width={box.width}
                  height={100}
                  rx="10"
                  fill="none"
                  stroke="#22d3ee"
                  strokeWidth="2"
                  opacity="0.6"
                  filter="url(#glow-active)"
                />
              )}
              
              <text
                x={box.x + box.width / 2}
                y={y + 20}
                textAnchor="middle"
                fill="white"
                className="pointer-events-none select-none"
              >
                {box.title}
              </text>
              
              {box.items.map((item, idx) => (
                <text
                  key={idx}
                  x={box.x + 10}
                  y={y + 45 + idx * 16}
                  fill="white"
                  opacity="0.9"
                  className="pointer-events-none select-none"
                >
                  • {item}
                </text>
              ))}
            </g>
          );
        })}
      </svg>

      {/* Step Legend */}
      {isAnimating && animatedStep > 0 && (
        <div className="mt-6 bg-slate-700/80 rounded-xl p-4 border border-slate-600">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-cyan-500 rounded-full flex items-center justify-center animate-pulse">
              <span className="text-white">{animatedStep}</span>
            </div>
            <div className="text-slate-200">
              <p>
                Schritt {animatedStep}: {getStepDescription(animatedStep)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function getStepDescription(step: number): string {
  const descriptions: Record<number, string> = {
    1: 'Orchestrator sendet Anfrage an Context Builder',
    2: 'Context Builder holt Daten aus State & Memory',
    3: 'Orchestrator speichert Job in Job DB',
    4: 'Job DB sendet Job zur Queue',
    5: 'Queue verteilt Job an Worker',
    6: 'Worker aktualisiert Job DB Status',
    7: 'Worker speichert große Daten im Artifact Store',
    8: 'Worker sendet Kontext an Prompt Builder',
    9: 'Prompt Builder sendet Prompt an LLM Provider',
    10: 'LLM sendet Antwort an Action Executor',
    11: 'Action Executor speichert Ergebnis in Job DB',
    12: 'Artifact Store Retention/Cleanup',
    13: 'Job DB Feedback an Context Builder für nächste Iteration'
  };
  return descriptions[step] || 'Verarbeitung läuft...';
}
