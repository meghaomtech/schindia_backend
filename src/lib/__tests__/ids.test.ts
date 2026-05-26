import { beforeEach, describe, expect, it } from 'vitest';
import {
  _resetIdsForTests,
  nextCentreSystemId,
  nextChildSystemId,
  uid,
} from '../ids';

describe('id generators', () => {
  beforeEach(() => _resetIdsForTests());

  it('produces sequential centre system IDs', () => {
    expect(nextCentreSystemId()).toBe('CTR-001');
    expect(nextCentreSystemId()).toBe('CTR-002');
    expect(nextCentreSystemId()).toBe('CTR-003');
  });

  it('produces sequential child system IDs', () => {
    expect(nextChildSystemId()).toBe('CHD-00001');
    expect(nextChildSystemId()).toBe('CHD-00002');
  });

  it('uid returns prefixed unique strings', () => {
    const a = uid('x');
    const b = uid('x');
    expect(a).toMatch(/^x_/);
    expect(b).toMatch(/^x_/);
    expect(a).not.toBe(b);
  });
});
