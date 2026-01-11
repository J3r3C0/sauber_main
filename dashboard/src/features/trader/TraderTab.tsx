import { TrendingUp, DollarSign, AlertTriangle, Target } from "lucide-react";
import { mockPositions, mockEquity } from "../../data/mockData";
import { StatCard } from "../../components/common/StatCard";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export function TraderTab() {
  const totalPnL = mockPositions.reduce((sum, p) => sum + p.pnl, 0);
  const currentEquity = mockEquity[mockEquity.length - 1]?.value || 0;
  const openPositions = mockPositions.length;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl">Trader Engine (Stub)</h1>
          <p className="text-sm text-slate-400 mt-1">
            Trading-Positionen, Equity-Verlauf und Strategy-Status.
          </p>
        </div>
        <div className="px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded text-xs text-amber-400">
          Preview Mode
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Current Equity"
          value={`$${currentEquity.toFixed(0)}`}
          icon={DollarSign}
          variant="success"
        />
        <StatCard
          label="Total P&L"
          value={`$${totalPnL.toFixed(2)}`}
          icon={TrendingUp}
          variant={totalPnL >= 0 ? "success" : "danger"}
          trend={totalPnL >= 0 ? { value: 2.3, direction: "up" } : { value: 1.2, direction: "down" }}
        />
        <StatCard
          label="Open Positions"
          value={openPositions}
          icon={Target}
        />
        <StatCard
          label="Risk Level"
          value="Medium"
          icon={AlertTriangle}
          variant="warning"
        />
      </div>

      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
        <h3 className="text-sm mb-4">Equity Curve (30 Days)</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={mockEquity}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(val) => new Date(val).toLocaleDateString()}
              stroke="#64748b"
              style={{ fontSize: 11 }}
            />
            <YAxis stroke="#64748b" style={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "6px",
                fontSize: 12,
              }}
              labelStyle={{ color: "#94a3b8" }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#00C3D4"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700">
          <h3 className="text-sm">Active Positions</h3>
          <p className="text-xs text-slate-400 mt-0.5">{mockPositions.length} open</p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/40 text-xs text-slate-400 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Symbol</th>
                <th className="px-4 py-3 text-left">Side</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Current</th>
                <th className="px-4 py-3 text-right">Size</th>
                <th className="px-4 py-3 text-right">P&L</th>
                <th className="px-4 py-3 text-right">%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {mockPositions.map((pos) => (
                <tr key={pos.id} className="hover:bg-slate-900/20 transition">
                  <td className="px-4 py-3 text-slate-200">{pos.symbol}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      pos.side === "long"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-red-500/10 text-red-400"
                    }`}>
                      {pos.side.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300">${pos.entry.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-slate-300">${pos.current.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{pos.size}</td>
                  <td className={`px-4 py-3 text-right ${
                    pos.pnl >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}>
                    ${pos.pnl.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 text-right ${
                    pos.pnlPercent >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}>
                    {pos.pnlPercent >= 0 ? "+" : ""}{pos.pnlPercent.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
        <h3 className="text-sm mb-3">Strategy Configuration</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-xs text-slate-400">Strategy</span>
            <div className="text-slate-200 mt-1">Mean Reversion v0.3</div>
          </div>
          <div>
            <span className="text-xs text-slate-400">Timeframe</span>
            <div className="text-slate-200 mt-1">15m / 1h</div>
          </div>
          <div>
            <span className="text-xs text-slate-400">Max Drawdown</span>
            <div className="text-slate-200 mt-1">12%</div>
          </div>
          <div>
            <span className="text-xs text-slate-400">Target CRV</span>
            <div className="text-slate-200 mt-1">2.5:1</div>
          </div>
        </div>
      </div>
    </div>
  );
}
