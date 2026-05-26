import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';

export interface FieldProps {
  label?: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  children: React.ReactNode;
}

export function Field({ label, hint, error, required, children }: FieldProps) {
  return (
    <label className="block">
      {label && (
        <span className="label">
          {label} {required && <span className="text-danger">*</span>}
        </span>
      )}
      {children}
      {error ? (
        <span className="block text-xs text-danger mt-1">{error}</span>
      ) : hint ? (
        <span className="block text-xs text-text-dim mt-1">{hint}</span>
      ) : null}
    </label>
  );
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export function Input({ invalid, className = '', ...rest }: InputProps) {
  return (
    <input {...rest} className={`input ${invalid ? 'input-error' : ''} ${className}`} />
  );
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export function Select({ invalid, className = '', children, ...rest }: SelectProps) {
  return (
    <select {...rest} className={`input ${invalid ? 'input-error' : ''} ${className}`}>
      {children}
    </select>
  );
}

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export function Textarea({ invalid, className = '', ...rest }: TextareaProps) {
  return (
    <textarea {...rest} className={`input ${invalid ? 'input-error' : ''} ${className}`} />
  );
}
