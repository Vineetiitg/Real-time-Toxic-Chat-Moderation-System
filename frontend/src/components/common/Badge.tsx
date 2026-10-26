import React from 'react';

interface BadgeProps {
  variant: 'safe' | 'low' | 'medium' | 'high' | 'info';
  children: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeProps['variant'], string> = {
  safe: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  low: 'bg-blue-50 text-blue-700 border-blue-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  high: 'bg-rose-50 text-rose-700 border-rose-200',
  info: 'bg-slate-100 text-slate-600 border-slate-200',
};

export default function Badge({ variant, children, icon, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${variantClasses[variant]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const s = severity?.toUpperCase() || 'SAFE';
  const variant: BadgeProps['variant'] =
    s === 'HIGH' ? 'high' :
    s === 'MEDIUM' ? 'medium' :
    s === 'LOW' ? 'low' :
    s === 'SAFE' ? 'safe' : 'info';

  const dot = (
    <span className={`w-1.5 h-1.5 rounded-full ${
      s === 'HIGH' ? 'bg-rose-500' :
      s === 'MEDIUM' ? 'bg-amber-500' :
      s === 'LOW' ? 'bg-blue-500' :
      'bg-emerald-500'
    }`} />
  );

  return <Badge variant={variant} icon={dot}>{s}</Badge>;
}

