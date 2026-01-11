import { Settings as SettingsIcon, Server, Network, Cpu, Database } from "lucide-react";

export function SettingsTab() {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl flex items-center gap-2">
          <SettingsIcon className="w-5 h-5" />
          System Configuration
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Port configuration, model routing, logging levels and system limits.
        </p>
      </header>

      {/* Port Configuration */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
          <Server className="w-4 h-4 text-sheratan-accent" />
          <h3 className="text-sm">Port Configuration</h3>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-2">Core API Port</label>
              <input
                type="number"
                defaultValue={7007}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Mesh Discovery Port (UDP)</label>
              <input
                type="number"
                defaultValue={9001}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Trader Engine Port</label>
              <input
                type="number"
                defaultValue={8080}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Relay Inbound Port</label>
              <input
                type="number"
                defaultValue={9100}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Relay Outbound Port</label>
              <input
                type="number"
                defaultValue={9101}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">GGUF Worker Port</label>
              <input
                type="number"
                defaultValue={8888}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Model Routing */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
          <Network className="w-4 h-4 text-sheratan-accent" />
          <h3 className="text-sm">Model Routing</h3>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="text-xs text-slate-400 block mb-2">Primary Model</label>
            <select className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent">
              <option>llama-3-8b-instruct (GGUF)</option>
              <option>mistral-7b-instruct (GGUF)</option>
              <option>gpt-4-turbo (Relay)</option>
              <option>claude-3-opus (Relay)</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-2">Fallback Model</label>
            <select className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent">
              <option>None</option>
              <option>llama-3-8b-instruct (GGUF)</option>
              <option>mistral-7b-instruct (GGUF)</option>
              <option>gpt-3.5-turbo (Relay)</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-2">Temperature</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="2"
                defaultValue={0.7}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Context Size</label>
              <input
                type="number"
                defaultValue={8192}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Logging Configuration */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-sheratan-accent" />
          <h3 className="text-sm">Logging & Monitoring</h3>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="text-xs text-slate-400 block mb-2">Log Level</label>
            <select className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent">
              <option>debug</option>
              <option>info</option>
              <option>warn</option>
              <option>error</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="verbose-logging"
              defaultChecked
              className="w-4 h-4 bg-slate-900 border-slate-700 rounded"
            />
            <label htmlFor="verbose-logging" className="text-sm text-slate-300">
              Enable verbose logging
            </label>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="metrics-collection"
              defaultChecked
              className="w-4 h-4 bg-slate-900 border-slate-700 rounded"
            />
            <label htmlFor="metrics-collection" className="text-sm text-slate-300">
              Enable metrics collection
            </label>
          </div>
        </div>
      </div>

      {/* System Limits */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
          <Database className="w-4 h-4 text-sheratan-accent" />
          <h3 className="text-sm">System Limits</h3>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-2">Max Memory (MB)</label>
              <input
                type="number"
                defaultValue={4096}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Cache Size (MB)</label>
              <input
                type="number"
                defaultValue={512}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Max Concurrent Jobs</label>
              <input
                type="number"
                defaultValue={10}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-2">Job Timeout (seconds)</label>
              <input
                type="number"
                defaultValue={300}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sheratan-accent"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-3">
        <button className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition">
          Reset to Defaults
        </button>
        <button className="px-4 py-2 bg-sheratan-accent/10 border border-sheratan-accent/40 text-sheratan-accent hover:bg-sheratan-accent/20 rounded-lg text-sm transition">
          Save Configuration
        </button>
      </div>
    </div>
  );
}
