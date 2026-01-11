import React, { useState, useEffect } from 'react';

interface Module {
  id: string;
  name: string;
  description: string;
  components: string[];
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
  depth: number;
  color: string;
  connections: string[];
}

export function IntegratedView() {
  const [rotation, setRotation] = useState({ x: 20, y: -20 });
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [flowActive, setFlowActive] = useState(false);
  const [flowStep, setFlowStep] = useState(0);

  const modules: Module[] = [
    {
      id: 'api-layer',
      name: 'API Layer',
      description: 'Entry point für alle Requests',
      components: ['WebRelay', 'API Gateway', 'Authentication', 'Rate Limiting'],
      x: 400,
      y: 50,
      z: 0,
      width: 300,
      height: 80,
      depth: 60,
      color: 'from-blue-500 to-blue-700',
      connections: ['orchestrator-layer']
    },
    {
      id: 'orchestrator-layer',
      name: 'Orchestration Layer',
      description: 'Zentrale Steuerung und Koordination',
      components: ['Core Orchestrator', 'Context Builder', 'Policy Engine', 'Job Generator'],
      x: 380,
      y: 180,
      z: 50,
      width: 340,
      height: 100,
      depth: 80,
      color: 'from-green-500 to-green-700',
      connections: ['message-layer', 'storage-layer']
    },
    {
      id: 'message-layer',
      name: 'Message & Queue Layer',
      description: 'Asynchrone Kommunikation',
      components: ['Message Bus', 'Job Queue', 'Event Router', 'Retry Handler'],
      x: 550,
      y: 330,
      z: 100,
      width: 280,
      height: 90,
      depth: 70,
      color: 'from-purple-500 to-purple-700',
      connections: ['worker-layer']
    },
    {
      id: 'worker-layer',
      name: 'Worker & Execution Layer',
      description: 'Job-Verarbeitung und LLM-Integration',
      components: ['Worker Pool', 'Prompt Builder', 'LLM Provider', 'Action Executor', 'Validator'],
      x: 800,
      y: 300,
      z: 50,
      width: 320,
      height: 120,
      depth: 90,
      color: 'from-orange-500 to-orange-700',
      connections: ['storage-layer', 'message-layer']
    },
    {
      id: 'storage-layer',
      name: 'Storage & Persistence Layer',
      description: 'Datenhaltung und Event Store',
      components: ['Job DB', 'Event Store', 'Artifact Store', 'State Storage', 'Memory Cache'],
      x: 150,
      y: 320,
      z: 100,
      width: 340,
      height: 110,
      depth: 85,
      color: 'from-cyan-500 to-cyan-700',
      connections: ['sync-layer']
    },
    {
      id: 'sync-layer',
      name: 'Sync & Distribution Layer',
      description: 'Verteilte Synchronisation',
      components: ['Mesh Sync Daemon', 'Replication', 'Conflict Resolution', 'Node Coordination'],
      x: 150,
      y: 480,
      z: 50,
      width: 300,
      height: 90,
      depth: 70,
      color: 'from-amber-600 to-amber-800',
      connections: []
    },
    {
      id: 'observability-layer',
      name: 'Observability & Security Layer',
      description: 'Monitoring und Sicherheit',
      components: ['Metrics', 'Logging', 'Tracing', 'Security Monitor', 'Audit Trail', 'Alerting'],
      x: 850,
      y: 480,
      z: 20,
      width: 280,
      height: 100,
      depth: 65,
      color: 'from-rose-500 to-rose-700',
      connections: ['orchestrator-layer', 'worker-layer', 'message-layer']
    }
  ];

  useEffect(() => {
    if (flowActive) {
      const timer = setInterval(() => {
        setFlowStep(prev => (prev + 1) % 8);
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [flowActive]);

  const flowPath = [
    'api-layer',
    'orchestrator-layer',
    'storage-layer',
    'message-layer',
    'worker-layer',
    'storage-layer',
    'orchestrator-layer',
    'api-layer'
  ];

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;
      setRotation({
        x: rotation.x + deltaY * 0.5,
        y: rotation.y + deltaX * 0.5
      });
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const project3D = (x: number, y: number, z: number) => {
    const scale = 0.8;
    const perspective = 1000;
    
    const radX = (rotation.x * Math.PI) / 180;
    const radY = (rotation.y * Math.PI) / 180;
    
    // Rotate around Y axis
    let newX = x * Math.cos(radY) + z * Math.sin(radY);
    let newZ = -x * Math.sin(radY) + z * Math.cos(radY);
    
    // Rotate around X axis
    let newY = y * Math.cos(radX) - newZ * Math.sin(radX);
    newZ = y * Math.sin(radX) + newZ * Math.cos(radX);
    
    // Apply perspective
    const scaleFactor = perspective / (perspective + newZ);
    
    return {
      x: newX * scaleFactor * scale,
      y: newY * scaleFactor * scale,
      scale: scaleFactor
    };
  };

  const drawModule = (module: Module) => {
    const topLeft = project3D(module.x, module.y, module.z);
    const topRight = project3D(module.x + module.width, module.y, module.z);
    const bottomLeft = project3D(module.x, module.y + module.height, module.z);
    const bottomRight = project3D(module.x + module.width, module.y + module.height, module.z);
    
    const topLeftBack = project3D(module.x, module.y, module.z + module.depth);
    const topRightBack = project3D(module.x + module.width, module.y, module.z + module.depth);
    const bottomRightBack = project3D(module.x + module.width, module.y + module.height, module.z + module.depth);
    
    const isSelected = selectedModule === module.id;
    const isActive = flowActive && flowPath[flowStep] === module.id;
    
    return (
      <g
        key={module.id}
        onClick={() => setSelectedModule(selectedModule === module.id ? null : module.id)}
        className="cursor-pointer transition-all duration-300"
        style={{ zIndex: Math.round(topLeft.scale * 100) }}
      >
        {/* Top face */}
        <path
          d={`M ${topLeft.x} ${topLeft.y} L ${topRight.x} ${topRight.y} L ${topRightBack.x} ${topRightBack.y} L ${topLeftBack.x} ${topLeftBack.y} Z`}
          className={`${module.color} fill-current opacity-80`}
          filter="url(#shadow3d)"
          stroke={isActive ? '#22d3ee' : isSelected ? '#fff' : '#1e293b'}
          strokeWidth={isActive ? 3 : isSelected ? 2.5 : 1}
        />
        
        {/* Right face */}
        <path
          d={`M ${topRight.x} ${topRight.y} L ${bottomRight.x} ${bottomRight.y} L ${bottomRightBack.x} ${bottomRightBack.y} L ${topRightBack.x} ${topRightBack.y} Z`}
          className={`${module.color} fill-current opacity-60`}
          filter="url(#shadow3d)"
          stroke={isActive ? '#22d3ee' : isSelected ? '#fff' : '#1e293b'}
          strokeWidth={isActive ? 3 : isSelected ? 2.5 : 1}
        />
        
        {/* Front face */}
        <path
          d={`M ${topLeft.x} ${topLeft.y} L ${topRight.x} ${topRight.y} L ${bottomRight.x} ${bottomRight.y} L ${bottomLeft.x} ${bottomLeft.y} Z`}
          className={`${module.color} fill-current`}
          filter="url(#shadow3d)"
          stroke={isActive ? '#22d3ee' : isSelected ? '#fff' : '#1e293b'}
          strokeWidth={isActive ? 3 : isSelected ? 2.5 : 1}
        />

        {/* Active glow */}
        {isActive && (
          <path
            d={`M ${topLeft.x} ${topLeft.y} L ${topRight.x} ${topRight.y} L ${bottomRight.x} ${bottomRight.y} L ${bottomLeft.x} ${bottomLeft.y} Z`}
            fill="none"
            stroke="#22d3ee"
            strokeWidth="4"
            opacity="0.6"
            filter="url(#glow)"
          >
            <animate
              attributeName="stroke-width"
              values="4;6;4"
              dur="1s"
              repeatCount="indefinite"
            />
          </path>
        )}
        
        {/* Text */}
        <text
          x={(topLeft.x + topRight.x) / 2}
          y={(topLeft.y + bottomLeft.y) / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="white"
          className="pointer-events-none select-none"
          style={{ fontSize: `${12 * topLeft.scale}px` }}
        >
          {module.name}
        </text>
      </g>
    );
  };

  const drawConnection = (fromId: string, toId: string, idx: number) => {
    const fromModule = modules.find(m => m.id === fromId);
    const toModule = modules.find(m => m.id === toId);
    if (!fromModule || !toModule) return null;

    const fromPos = project3D(
      fromModule.x + fromModule.width / 2,
      fromModule.y + fromModule.height / 2,
      fromModule.z + fromModule.depth / 2
    );
    const toPos = project3D(
      toModule.x + toModule.width / 2,
      toModule.y + toModule.height / 2,
      toModule.z + toModule.depth / 2
    );

    const isActiveConnection = flowActive && (
      (flowPath[flowStep] === fromId && flowPath[(flowStep + 1) % flowPath.length] === toId) ||
      (flowPath[flowStep] === toId && flowPath[(flowStep + 1) % flowPath.length] === fromId)
    );

    return (
      <line
        key={`conn-${idx}`}
        x1={fromPos.x}
        y1={fromPos.y}
        x2={toPos.x}
        y2={toPos.y}
        stroke={isActiveConnection ? '#22d3ee' : '#64748b'}
        strokeWidth={isActiveConnection ? 3 : 1.5}
        strokeDasharray={isActiveConnection ? '0' : '5,5'}
        opacity={isActiveConnection ? 1 : 0.4}
        markerEnd={isActiveConnection ? 'url(#arrow-active)' : 'url(#arrow-normal)'}
        className="transition-all duration-500"
      />
    );
  };

  const selectedModuleData = modules.find(m => m.id === selectedModule);

  return (
    <div className="relative">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-3">
          <button
            onClick={() => setRotation({ x: 20, y: -20 })}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Standard Ansicht
          </button>
          <button
            onClick={() => setRotation({ x: 0, y: 0 })}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Frontal
          </button>
          <button
            onClick={() => setRotation({ x: 60, y: 30 })}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Von oben
          </button>
        </div>
        <button
          onClick={() => {
            setFlowActive(!flowActive);
            setFlowStep(0);
          }}
          className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
            flowActive
              ? 'bg-cyan-600 hover:bg-cyan-700'
              : 'bg-blue-600 hover:bg-blue-700'
          } text-white`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {flowActive ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            )}
          </svg>
          {flowActive ? 'Flow stoppen' : 'Flow starten'}
        </button>
      </div>

      <div
        className="bg-slate-900/50 rounded-xl overflow-hidden border border-slate-700"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        <svg
          viewBox="-600 -400 2400 1400"
          className="w-full h-auto"
          style={{ minHeight: '700px' }}
        >
          <defs>
            <filter id="shadow3d" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur in="SourceAlpha" stdDeviation="8"/>
              <feOffset dx="6" dy="10" result="offsetblur"/>
              <feComponentTransfer>
                <feFuncA type="linear" slope="0.4"/>
              </feComponentTransfer>
              <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>

            <filter id="glow">
              <feGaussianBlur stdDeviation="5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>

            <marker
              id="arrow-normal"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#64748b" />
            </marker>

            <marker
              id="arrow-active"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="4"
              orient="auto"
            >
              <polygon points="0 0, 10 4, 0 8" fill="#22d3ee" />
            </marker>
          </defs>

          {/* Grid background */}
          <g opacity="0.1">
            {Array.from({ length: 20 }).map((_, i) => (
              <line
                key={`grid-h-${i}`}
                x1="-600"
                y1={i * 60 - 300}
                x2="1800"
                y2={i * 60 - 300}
                stroke="#fff"
                strokeWidth="0.5"
              />
            ))}
            {Array.from({ length: 40 }).map((_, i) => (
              <line
                key={`grid-v-${i}`}
                x1={i * 60 - 600}
                y1="-400"
                x2={i * 60 - 600}
                y2="1000"
                stroke="#fff"
                strokeWidth="0.5"
              />
            ))}
          </g>

          {/* Connections */}
          <g className="connections">
            {modules.flatMap((module, idx) =>
              module.connections.map((connId, connIdx) =>
                drawConnection(module.id, connId, idx * 100 + connIdx)
              )
            )}
          </g>

          {/* Modules - sorted by z-index for proper layering */}
          {modules
            .map(module => ({
              module,
              zIndex: project3D(module.x, module.y, module.z).scale
            }))
            .sort((a, b) => a.zIndex - b.zIndex)
            .map(({ module }) => drawModule(module))}
        </svg>
      </div>

      {/* Instructions */}
      <div className="mt-4 text-slate-400 text-center">
        Ziehen Sie mit der Maus, um die 3D-Ansicht zu drehen • Klicken Sie auf Module für Details
      </div>

      {/* Details Panel */}
      {selectedModuleData && (
        <div className="mt-6 bg-gradient-to-br from-slate-700/90 to-slate-800/90 rounded-xl p-6 border border-slate-600 backdrop-blur-sm">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-white mb-2">{selectedModuleData.name}</h3>
              <p className="text-slate-300">{selectedModuleData.description}</p>
            </div>
            <button
              onClick={() => setSelectedModule(null)}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-slate-400 mb-2">Komponenten:</h4>
              <div className="space-y-1">
                {selectedModuleData.components.map((comp, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-slate-200">
                    <svg className="w-4 h-4 mt-0.5 text-blue-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>{comp}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h4 className="text-slate-400 mb-2">Verbindungen:</h4>
              <div className="space-y-1">
                {selectedModuleData.connections.length > 0 ? (
                  selectedModuleData.connections.map((connId, idx) => {
                    const connModule = modules.find(m => m.id === connId);
                    return (
                      <div key={idx} className="flex items-start gap-2 text-slate-200">
                        <svg className="w-4 h-4 mt-0.5 text-green-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M12.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                        <span>{connModule?.name}</span>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-slate-400">Keine direkten Verbindungen</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Flow Status */}
      {flowActive && (
        <div className="mt-4 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 rounded-xl p-4 border border-cyan-500/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-cyan-500 rounded-full flex items-center justify-center animate-pulse">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <p className="text-white">Aktiver Datenfluss</p>
              <p className="text-slate-300">
                {modules.find(m => m.id === flowPath[flowStep])?.name}
                {' → '}
                {modules.find(m => m.id === flowPath[(flowStep + 1) % flowPath.length])?.name}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
