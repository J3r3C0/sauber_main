import React, { useState } from 'react';

interface Component {
  id: string;
  name: string;
  subtitle?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  shape: 'rect' | 'ellipse';
  details: string[];
}

interface Connection {
  from: string;
  to: string;
  type: 'solid' | 'dashed';
  label?: string;
  path?: string;
}

export function SystemArchitecture() {
  const [hoveredComponent, setHoveredComponent] = useState<string | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);

  const components: Component[] = [
    {
      id: 'api-gateway',
      name: 'WebRelay / API Gateway',
      x: 450,
      y: 50,
      width: 280,
      height: 80,
      color: 'from-blue-400 to-blue-600',
      shape: 'rect',
      details: ['REST/GraphQL Endpoints', 'Request Validation', 'Rate Limiting', 'Authentication']
    },
    {
      id: 'orchestrator',
      name: 'Core Orchestrator',
      x: 450,
      y: 170,
      width: 280,
      height: 80,
      color: 'from-green-400 to-green-600',
      shape: 'rect',
      details: ['Mission/Task Management', 'Job Generator', 'Policy Enforcement', 'State Coordination']
    },
    {
      id: 'message-bus',
      name: 'Message Bus',
      x: 590,
      y: 300,
      width: 200,
      height: 70,
      color: 'from-red-400 to-red-600',
      shape: 'ellipse',
      details: ['Event Distribution', 'Pub/Sub Pattern', 'Message Routing', 'Async Communication']
    },
    {
      id: 'worker-pool',
      name: 'Worker Pool',
      x: 900,
      y: 280,
      width: 280,
      height: 90,
      color: 'from-teal-400 to-teal-600',
      shape: 'rect',
      details: ['Job Execution', 'LLM Integration', 'Prompt Processing', 'Action Execution', 'Parallel Processing']
    },
    {
      id: 'event-store',
      name: 'Unified Event Store',
      subtitle: '(SQLite + Chunks)',
      x: 80,
      y: 280,
      width: 300,
      height: 90,
      color: 'from-orange-400 to-orange-600',
      shape: 'rect',
      details: ['Event Sourcing', 'Job State Persistence', 'Chunk Storage', 'Query Interface', 'Transaction Log']
    },
    {
      id: 'mesh-sync',
      name: 'Mesh Sync Daemon',
      x: 80,
      y: 420,
      width: 300,
      height: 90,
      color: 'from-amber-500 to-amber-700',
      shape: 'rect',
      details: ['Distributed Sync', 'Node Coordination', 'Conflict Resolution', 'Replication']
    },
    {
      id: 'observability',
      name: 'Observability & Security',
      x: 900,
      y: 420,
      width: 280,
      height: 90,
      color: 'from-yellow-400 to-yellow-600',
      shape: 'rect',
      details: ['Metrics Collection', 'Logging & Tracing', 'Security Monitoring', 'Audit Trail', 'Alerting']
    }
  ];

  const connections: Connection[] = [
    { from: 'api-gateway', to: 'orchestrator', type: 'solid', label: 'Requests' },
    { from: 'orchestrator', to: 'message-bus', type: 'solid', label: 'Events' },
    { from: 'message-bus', to: 'worker-pool', type: 'solid', label: 'Jobs' },
    { from: 'worker-pool', to: 'message-bus', type: 'solid', label: 'Results' },
    { from: 'orchestrator', to: 'event-store', type: 'solid', label: 'Store' },
    { from: 'event-store', to: 'mesh-sync', type: 'solid', label: 'Sync' },
    { from: 'mesh-sync', to: 'event-store', type: 'solid', label: 'Replicate' },
    { from: 'observability', to: 'orchestrator', type: 'dashed' },
    { from: 'observability', to: 'worker-pool', type: 'dashed' },
    { from: 'observability', to: 'message-bus', type: 'dashed' },
    { from: 'observability', to: 'mesh-sync', type: 'dashed' }
  ];

  const getConnectionPath = (conn: Connection): string => {
    const fromComp = components.find(c => c.id === conn.from);
    const toComp = components.find(c => c.id === conn.to);
    if (!fromComp || !toComp) return '';

    const fromX = fromComp.x + fromComp.width / 2;
    const fromY = fromComp.y + fromComp.height;
    const toX = toComp.x + toComp.width / 2;
    const toY = toComp.y;

    // Simple path for now
    if (conn.from === 'orchestrator' && conn.to === 'event-store') {
      return `M ${fromComp.x},${fromComp.y + fromComp.height/2} L ${toComp.x + toComp.width},${toComp.y + toComp.height/2}`;
    }
    if (conn.from === 'event-store' && conn.to === 'mesh-sync') {
      return `M ${fromComp.x + fromComp.width/2},${fromComp.y + fromComp.height} L ${toComp.x + toComp.width/2},${toComp.y}`;
    }
    if (conn.from === 'mesh-sync' && conn.to === 'event-store') {
      const offset = 40;
      return `M ${fromComp.x + fromComp.width/2 + offset},${fromComp.y} L ${fromComp.x + fromComp.width/2 + offset},${fromComp.y - 30} L ${toComp.x + toComp.width/2 + offset},${toComp.y + toComp.height + 30} L ${toComp.x + toComp.width/2 + offset},${toComp.y + toComp.height}`;
    }
    if (conn.from === 'message-bus' && conn.to === 'worker-pool') {
      return `M ${fromComp.x + fromComp.width/2 + 50},${fromComp.y + fromComp.height/2} L ${toComp.x},${toComp.y + toComp.height/2}`;
    }
    if (conn.from === 'worker-pool' && conn.to === 'message-bus') {
      return `M ${toComp.x + toComp.width/2 + 50},${toComp.y + toComp.height/2 - 15} L ${fromComp.x},${fromComp.y + fromComp.height/2 - 15}`;
    }

    return `M ${fromX},${fromY} L ${toX},${toY}`;
  };

  const selectedComp = components.find(c => c.id === selectedComponent);

  return (
    <div className="relative">
      <svg
        viewBox="0 0 1280 600"
        className="w-full h-auto"
        style={{ minHeight: '600px' }}
      >
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#64748b" />
          </marker>
          <marker
            id="arrowhead-highlight"
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="3"
            orient="auto"
          >
            <polygon points="0 0, 10 3, 0 6" fill="#3b82f6" />
          </marker>
          
          {/* Filters for 3D effect */}
          <filter id="shadow3d" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="4"/>
            <feOffset dx="6" dy="8" result="offsetblur"/>
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.3"/>
            </feComponentTransfer>
            <feMerge>
              <feMergeNode/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Gradients for each component */}
          {components.map(comp => (
            <linearGradient key={`grad-${comp.id}`} id={`grad-${comp.id}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" className={`${comp.color.split(' ')[0].replace('from-', 'text-')}`} stopColor="currentColor" />
              <stop offset="100%" className={`${comp.color.split(' ')[2].replace('to-', 'text-')}`} stopColor="currentColor" />
            </linearGradient>
          ))}
        </defs>

        {/* Connections */}
        <g className="connections">
          {connections.map((conn, idx) => {
            const isHighlighted = hoveredComponent === conn.from || hoveredComponent === conn.to;
            return (
              <g key={idx}>
                <path
                  d={getConnectionPath(conn)}
                  fill="none"
                  stroke={isHighlighted ? '#3b82f6' : '#64748b'}
                  strokeWidth={isHighlighted ? 3 : 2}
                  strokeDasharray={conn.type === 'dashed' ? '8,4' : '0'}
                  markerEnd={isHighlighted ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)'}
                  className="transition-all duration-300"
                  opacity={isHighlighted ? 1 : 0.5}
                />
              </g>
            );
          })}
        </g>

        {/* Components */}
        <g className="components">
          {components.map(comp => {
            const isHovered = hoveredComponent === comp.id;
            const isSelected = selectedComponent === comp.id;
            
            return (
              <g
                key={comp.id}
                transform={isHovered || isSelected ? 'scale(1.02)' : 'scale(1)'}
                style={{
                  transformOrigin: `${comp.x + comp.width / 2}px ${comp.y + comp.height / 2}px`,
                  transition: 'transform 0.2s ease-out',
                  cursor: 'pointer'
                }}
                onMouseEnter={() => setHoveredComponent(comp.id)}
                onMouseLeave={() => setHoveredComponent(null)}
                onClick={() => setSelectedComponent(selectedComponent === comp.id ? null : comp.id)}
              >
                {comp.shape === 'rect' ? (
                  <rect
                    x={comp.x}
                    y={comp.y}
                    width={comp.width}
                    height={comp.height}
                    rx="12"
                    ry="12"
                    fill={`url(#grad-${comp.id})`}
                    filter="url(#shadow3d)"
                    stroke={isSelected ? '#fff' : isHovered ? '#cbd5e1' : '#475569'}
                    strokeWidth={isSelected ? 3 : 2}
                    opacity={isHovered || isSelected ? 1 : 0.9}
                  />
                ) : (
                  <ellipse
                    cx={comp.x + comp.width / 2}
                    cy={comp.y + comp.height / 2}
                    rx={comp.width / 2}
                    ry={comp.height / 2}
                    fill={`url(#grad-${comp.id})`}
                    filter="url(#shadow3d)"
                    stroke={isSelected ? '#fff' : isHovered ? '#cbd5e1' : '#475569'}
                    strokeWidth={isSelected ? 3 : 2}
                    opacity={isHovered || isSelected ? 1 : 0.9}
                  />
                )}
                
                {/* Top edge highlight for 3D effect */}
                {comp.shape === 'rect' && (
                  <rect
                    x={comp.x}
                    y={comp.y}
                    width={comp.width}
                    height={comp.height / 3}
                    rx="12"
                    ry="12"
                    fill="white"
                    opacity="0.2"
                    pointerEvents="none"
                  />
                )}
                
                <text
                  x={comp.x + comp.width / 2}
                  y={comp.y + comp.height / 2 - (comp.subtitle ? 8 : 0)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="white"
                  className="pointer-events-none select-none"
                  style={{ textShadow: '0 2px 4px rgba(0,0,0,0.5)' }}
                >
                  {comp.name}
                </text>
                {comp.subtitle && (
                  <text
                    x={comp.x + comp.width / 2}
                    y={comp.y + comp.height / 2 + 12}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="white"
                    opacity="0.8"
                    className="pointer-events-none select-none"
                  >
                    {comp.subtitle}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Details Panel */}
      {selectedComp && (
        <div className="mt-6 bg-slate-700/80 rounded-xl p-6 border border-slate-600 backdrop-blur-sm">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-white mb-1">{selectedComp.name}</h3>
              {selectedComp.subtitle && (
                <p className="text-slate-400">{selectedComp.subtitle}</p>
              )}
            </div>
            <button
              onClick={() => setSelectedComponent(null)}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="space-y-2">
            {selectedComp.details.map((detail, idx) => (
              <div key={idx} className="flex items-start gap-2 text-slate-300">
                <svg className="w-5 h-5 mt-0.5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>{detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
