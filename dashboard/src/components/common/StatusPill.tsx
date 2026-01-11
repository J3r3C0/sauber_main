interface StatusPillProps {
  status: string;
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
}

export function StatusPill({ status, variant = "neutral" }: StatusPillProps) {
  const variants = {
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    danger: "bg-red-500/10 text-red-400 border-red-500/20",
    info: "bg-sheratan-accent/10 text-sheratan-accent border-sheratan-accent/20",
    neutral: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${variants[variant]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${variant === 'success' ? 'bg-emerald-400' : variant === 'warning' ? 'bg-amber-400' : variant === 'danger' ? 'bg-red-400' : variant === 'info' ? 'bg-sheratan-accent' : 'bg-slate-400'}`} />
      {status}
    </span>
  );
}
