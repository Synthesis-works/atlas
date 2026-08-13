

interface AtlasAvatarProps {
  src?: string;
  alt?: string;
  initials?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function AtlasAvatar({ src, alt, initials, size = 'md', className = '' }: AtlasAvatarProps) {
  const sizeClasses = {
    sm: 'w-6 h-6 text-[10px]',
    md: 'w-8 h-8 text-xs',
    lg: 'w-10 h-10 text-sm'
  };

  return (
    <div className={`relative flex shrink-0 overflow-hidden items-center justify-center rounded-full bg-white/10 border border-white/10 ${sizeClasses[size]} ${className}`}>
      {src ? (
        <img src={src} alt={alt || 'Avatar'} className="w-full h-full object-cover" />
      ) : (
        <span className="text-white/70 font-medium tracking-wider">{initials || '?'}</span>
      )}
    </div>
  );
}
