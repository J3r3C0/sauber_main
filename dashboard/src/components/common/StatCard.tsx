import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  trend?: {
    value: number;
    direction: "up" | "down";
  };
  variant?: "default" | "success" | "warning" | "danger";
}

export function StatCard({ label, value, icon: Icon, trend, variant = "default" }: StatCardProps) {
  const variantColors = {
    default: "border-slate-700",
    success: "border-sheratan-success/40",
    warning: "border-sheratan-warning/40",
    danger: "border-sheratan-danger/40",
  };

  const trendColor = trend?.direction === "up" ? "text-emerald-400" : "text-red-400";

  return (
    <div className={`bg-sheratan-card border ${variantColors[variant]} rounded-lg p-4`}>
      <div className="flex items-start justify-between mb-2">
        <span className="text-xs text-slate-400 uppercase tracking-wide">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-slate-500" />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl text-slate-50">{value}</span>
        {trend && (
          <span className={`text-xs ${trendColor}`}>
            {trend.direction === "up" ? "↑" : "↓"} {Math.abs(trend.value)}%
          </span>
        )}
      </div>
    </div>
  );
}
