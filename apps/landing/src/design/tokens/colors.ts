export const ColorTokens = {
  // Base palette
  background: '#000000',
  foreground: '#FFFFFF',
  
  // Semantic UI colors
  card: {
    base: 'rgba(255, 255, 255, 0.03)',
    hover: 'rgba(255, 255, 255, 0.05)',
    border: 'rgba(255, 255, 255, 0.1)',
  },
  
  text: {
    primary: 'rgba(255, 255, 255, 1)',
    secondary: 'rgba(255, 255, 255, 0.7)',
    tertiary: 'rgba(255, 255, 255, 0.5)',
    disabled: 'rgba(255, 255, 255, 0.3)',
  },
  
  status: {
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
  },
  
  accent: {
    primary: '#3B82F6', // Blue
    glow: 'rgba(59, 130, 246, 0.5)',
  }
} as const;
