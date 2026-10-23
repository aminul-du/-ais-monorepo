export const colors = {
  bg: '#0A0B10', surface: '#1A1C23', accent: '#D0BCFF', accentFg: '#381E72',
  textPrimary: '#FFFFFF', textSecondary: '#A0A3B1',
  statusOk: '#3DDC97', statusError: '#FF5C5C', statusWarn: '#FFB020',
} as const;
export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 40 } as const;
export const radius = { sm: 8, md: 12, lg: 16, pill: 9999 } as const;
export const font = {
  sans: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  mono: 'ui-monospace, "JetBrains Mono", monospace',
} as const;
export type ColorToken = keyof typeof colors;
export type RadiusToken = keyof typeof radius;
