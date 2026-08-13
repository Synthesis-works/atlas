

export type AtlasBadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'outline';

interface AtlasBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: AtlasBadgeVariant;
}

export function AtlasBadge({ variant = 'default', className = '', children, ...props }: AtlasBadgeProps) {
  const baseClasses = 'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium';
  
  const variantClasses = {
    default: 'bg-white/10 text-white/80',
    success: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
    error: 'bg-red-500/10 text-red-400 border border-red-500/20',
    info: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
    outline: 'border border-white/20 text-white/70'
  };

  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${className}`} {...props}>
      {children}
    </span>
  );
}
