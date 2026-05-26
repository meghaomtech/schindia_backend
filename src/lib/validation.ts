import type { Centre, Child, Contact, Session, ValidationError } from './types';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isBlank(s: string | undefined | null): boolean {
  return !s || s.trim().length === 0;
}

export function validateCentreDetails(
  c: Pick<
    Centre,
    'name' | 'streetAddress' | 'city' | 'postcode' | 'phone' | 'email' | 'managerName'
  >
): ValidationError[] {
  const errs: ValidationError[] = [];
  if (isBlank(c.name)) errs.push({ field: 'name', message: 'Centre name is required' });
  if (isBlank(c.streetAddress))
    errs.push({ field: 'streetAddress', message: 'Street address is required' });
  if (isBlank(c.city)) errs.push({ field: 'city', message: 'City is required' });
  if (isBlank(c.postcode)) errs.push({ field: 'postcode', message: 'Postcode is required' });
  if (isBlank(c.phone)) errs.push({ field: 'phone', message: 'Phone number is required' });
  if (isBlank(c.email)) errs.push({ field: 'email', message: 'Email is required' });
  else if (!EMAIL_RE.test(c.email))
    errs.push({ field: 'email', message: 'Email is not valid' });
  if (isBlank(c.managerName))
    errs.push({ field: 'managerName', message: 'Centre manager is required' });
  return errs;
}

export function validateSession(
  s: Pick<
    Session,
    'name' | 'childLimit' | 'ageFrom' | 'ageTo' | 'durationHours' | 'durationMinutes'
  >
): ValidationError[] {
  const errs: ValidationError[] = [];
  if (isBlank(s.name)) errs.push({ field: 'name', message: 'Session name is required' });
  if (!Number.isFinite(s.childLimit) || s.childLimit < 1 || s.childLimit > 99)
    errs.push({ field: 'childLimit', message: 'Child limit must be 1–99' });
  if (!Number.isFinite(s.ageFrom) || s.ageFrom < 0)
    errs.push({ field: 'ageFrom', message: 'Age from must be 0 or greater' });
  if (!Number.isFinite(s.ageTo) || s.ageTo < s.ageFrom)
    errs.push({ field: 'ageTo', message: 'Age to must be ≥ age from' });
  const totalMinutes = s.durationHours * 60 + s.durationMinutes;
  if (totalMinutes <= 0)
    errs.push({ field: 'duration', message: 'Duration must be greater than zero' });
  return errs;
}

export function validateContact(c: Contact): ValidationError[] {
  const errs: ValidationError[] = [];
  const required = c.isMain;
  if (isBlank(c.name)) errs.push({ field: 'name', message: 'Name is required' });
  if (isBlank(c.relation)) errs.push({ field: 'relation', message: 'Relation is required' });
  if (required) {
    if (isBlank(c.phone)) errs.push({ field: 'phone', message: 'Phone is required' });
    if (isBlank(c.email)) errs.push({ field: 'email', message: 'Email is required' });
    else if (!EMAIL_RE.test(c.email))
      errs.push({ field: 'email', message: 'Email is not valid' });
  } else if (c.email && !EMAIL_RE.test(c.email)) {
    errs.push({ field: 'email', message: 'Email is not valid' });
  }
  if (c.inviteAs !== "Don't invite" && isBlank(c.email))
    errs.push({ field: 'email', message: 'Email is required to invite this contact' });
  return errs;
}

export function validateChild(child: Omit<Child, 'id' | 'systemId'>): ValidationError[] {
  const errs: ValidationError[] = [];
  if (isBlank(child.firstName))
    errs.push({ field: 'firstName', message: 'First name is required' });
  if (isBlank(child.lastName))
    errs.push({ field: 'lastName', message: 'Last name is required' });
  if (isBlank(child.gender)) errs.push({ field: 'gender', message: 'Gender is required' });
  if (isBlank(child.centreId)) errs.push({ field: 'centreId', message: 'Centre is required' });
  if (isBlank(child.startDate))
    errs.push({ field: 'startDate', message: 'Start date is required' });

  const main = child.contacts.find((c) => c.isMain);
  if (!main) {
    errs.push({ field: 'contacts', message: 'A main contact is required' });
  } else {
    for (const e of validateContact(main)) {
      errs.push({ field: `mainContact.${e.field}`, message: e.message });
    }
  }
  return errs;
}

export const _testHelpers = { isBlank, EMAIL_RE };
