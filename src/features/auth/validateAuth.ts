import type { ValidationError } from '@/lib/types';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isBlank(s: string | undefined | null): boolean {
  return !s || s.trim().length === 0;
}

export interface SignupFormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface LoginFormData {
  email: string;
  password: string;
}

export function validateSignup(data: SignupFormData): ValidationError[] {
  const errs: ValidationError[] = [];

  if (isBlank(data.name)) errs.push({ field: 'name', message: 'Required' });
  if (isBlank(data.email)) errs.push({ field: 'email', message: 'Required' });
  else if (!EMAIL_RE.test(data.email))
    errs.push({ field: 'email', message: 'Enter a valid email address' });

  if (isBlank(data.password)) errs.push({ field: 'password', message: 'Required' });
  else if (data.password.length < 8)
    errs.push({ field: 'password', message: 'Password must be at least 8 characters' });

  if (isBlank(data.confirmPassword))
    errs.push({ field: 'confirmPassword', message: 'Required' });
  else if (data.confirmPassword !== data.password)
    errs.push({ field: 'confirmPassword', message: 'Passwords do not match' });

  return errs;
}

export function validateLogin(data: LoginFormData): ValidationError[] {
  const errs: ValidationError[] = [];

  if (isBlank(data.email)) errs.push({ field: 'email', message: 'Required' });
  else if (!EMAIL_RE.test(data.email))
    errs.push({ field: 'email', message: 'Enter a valid email address' });

  if (isBlank(data.password)) errs.push({ field: 'password', message: 'Required' });

  return errs;
}
