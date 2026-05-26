/**
 * Soft palette pairs (background + readable text) used for session avatars,
 * blocks on the schedule, etc. Cycled by string hash so the same name maps to
 * the same colour across renders.
 */
export interface ColorPair {
  bg: string;
  text: string;
}

export const SESSION_PALETTES: ColorPair[] = [
  { bg: '#dcfce7', text: '#166534' }, // green
  { bg: '#e0e7ff', text: '#3730a3' }, // indigo
  { bg: '#fde68a', text: '#7c2d12' }, // amber
  { bg: '#fee2e2', text: '#991b1b' }, // red
  { bg: '#f3e8ff', text: '#6b21a8' }, // purple
  { bg: '#cffafe', text: '#155e75' }, // cyan
  { bg: '#ffe4e6', text: '#9f1239' }, // rose
  { bg: '#fef3c7', text: '#92400e' }, // yellow
];

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h << 5) - h + s.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

export function paletteFor(name: string): ColorPair {
  const palette = SESSION_PALETTES[hashString(name) % SESSION_PALETTES.length];
  return palette ?? SESSION_PALETTES[0]!;
}

export function initialsOf(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 1) return (parts[0]?.[0] ?? '').toUpperCase();
  return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase();
}
