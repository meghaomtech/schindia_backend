import { describe, expect, it } from 'vitest';
import { initialsOf, paletteFor } from '../colors';

describe('initialsOf', () => {
  it('returns first letter for one-name input', () => {
    expect(initialsOf('Olivia')).toBe('O');
  });

  it('returns first + last initials for two+ names', () => {
    expect(initialsOf('Olivia Lawson')).toBe('OL');
    expect(initialsOf('Olivia Grace Lawson')).toBe('OL');
  });

  it('handles whitespace', () => {
    expect(initialsOf('  Sarah   Lawson  ')).toBe('SL');
  });
});

describe('paletteFor', () => {
  it('is deterministic', () => {
    const a = paletteFor('Bears');
    const b = paletteFor('Bears');
    expect(a).toEqual(b);
  });

  it('returns a non-empty pair', () => {
    const p = paletteFor('Cubs');
    expect(p.bg).toBeTruthy();
    expect(p.text).toBeTruthy();
  });
});
