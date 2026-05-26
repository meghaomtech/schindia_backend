import { describe, expect, it } from 'vitest';
import {
  validateCentreDetails,
  validateContact,
  validateChild,
  validateSession,
} from '../validation';
import type { Contact } from '../types';

describe('validateCentreDetails', () => {
  const valid = {
    name: 'Sunshine',
    streetAddress: '12 Oak Lane',
    city: 'London',
    postcode: 'E1 4AB',
    phone: '020 7946',
    email: 'a@b.co',
    managerName: 'Helen',
  };

  it('passes for a complete record', () => {
    expect(validateCentreDetails(valid)).toEqual([]);
  });

  it('flags blank required fields', () => {
    const errs = validateCentreDetails({ ...valid, name: '', city: '' });
    const fields = errs.map((e) => e.field);
    expect(fields).toContain('name');
    expect(fields).toContain('city');
  });

  it('flags an invalid email', () => {
    const errs = validateCentreDetails({ ...valid, email: 'not-an-email' });
    expect(errs.find((e) => e.field === 'email')).toBeDefined();
  });
});

describe('validateSession', () => {
  const valid = {
    name: 'Cubs',
    childLimit: 8,
    ageFrom: 0,
    ageTo: 5,
    durationHours: 1,
    durationMinutes: 30,
  };

  it('passes when fields are valid', () => {
    expect(validateSession(valid)).toEqual([]);
  });

  it('flags childLimit out of range', () => {
    const errs = validateSession({ ...valid, childLimit: 0 });
    expect(errs.find((e) => e.field === 'childLimit')).toBeDefined();
  });

  it('flags ageTo < ageFrom', () => {
    const errs = validateSession({ ...valid, ageFrom: 5, ageTo: 2 });
    expect(errs.find((e) => e.field === 'ageTo')).toBeDefined();
  });

  it('flags zero duration', () => {
    const errs = validateSession({
      ...valid,
      durationHours: 0,
      durationMinutes: 0,
    });
    expect(errs.find((e) => e.field === 'duration')).toBeDefined();
  });
});

describe('validateContact', () => {
  const baseMain: Contact = {
    id: 'c',
    name: 'Sarah',
    relation: 'Mother',
    phone: '07700',
    email: 'sarah@x.com',
    inviteAs: 'Parent',
    isMain: true,
    isBillPayer: false,
    isEmergency: false,
  };

  it('passes for a valid main contact', () => {
    expect(validateContact(baseMain)).toEqual([]);
  });

  it('requires phone & email for main contact', () => {
    const errs = validateContact({ ...baseMain, phone: '', email: '' });
    expect(errs.find((e) => e.field === 'phone')).toBeDefined();
    expect(errs.find((e) => e.field === 'email')).toBeDefined();
  });

  it('requires email when invite is enabled', () => {
    const errs = validateContact({
      ...baseMain,
      isMain: false,
      email: '',
      inviteAs: 'Parent',
    });
    expect(errs.find((e) => e.field === 'email')).toBeDefined();
  });
});

describe('validateChild', () => {
  it('requires a main contact', () => {
    const errs = validateChild({
      firstName: 'A',
      lastName: 'B',
      gender: 'Female',
      centreId: 'c1',
      dateOfBirth: '2022-01-01',
      startDate: '2026-01-01',
      contacts: [],
    });
    expect(errs.find((e) => e.field === 'contacts')).toBeDefined();
  });
});
