import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { useAuth } from './AuthContext';
import { AuthLayout } from './AuthLayout';
import { validateSignup } from './validateAuth';
import type { ValidationError } from '@/lib/types';

export function RootSetupPage() {
  const { setupRoot, isRootSetup } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);

  // If root is already set up, redirect to login
  if (isRootSetup) {
    navigate('/login', { replace: true });
    return null;
  }

  function getError(field: string) {
    return errors.find((e) => e.field === field)?.message ?? null;
  }

  function focusFirstError(errs: ValidationError[]) {
    const first = errs[0]?.field;
    if (first === 'name') nameRef.current?.focus();
    else if (first === 'email') emailRef.current?.focus();
    else if (first === 'password') passwordRef.current?.focus();
    else if (first === 'confirmPassword') confirmRef.current?.focus();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    const validationErrors = validateSignup({ name, email, password, confirmPassword });
    setErrors(validationErrors);

    if (validationErrors.length > 0) {
      focusFirstError(validationErrors);
      return;
    }

    setLoading(true);
    try {
      await setupRoot(name, email, password);
      navigate('/admin', { replace: true });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Set up Root Admin"
      footer={
        <span className="text-text-dim text-xs">
          This is a one-time setup. The root admin will manage all access approvals.
        </span>
      }
    >
      <div className="mb-4 p-3 rounded-lg bg-olive/5 border border-olive/20">
        <p className="text-sm text-text-muted">
          <span className="font-medium text-olive">First-time setup:</span>{' '}
          Create the root admin account. This account will have full access and will approve
          all future admin access requests.
        </p>
      </div>

      <form onSubmit={handleSubmit} noValidate aria-busy={loading}>
        {formError && (
          <div
            role="alert"
            className="bg-danger/10 border border-danger/30 text-danger rounded-lg p-3 text-sm mb-4"
          >
            {formError}
          </div>
        )}

        <div className="space-y-4">
          <Field label="Full Name" error={getError('name')} required>
            <Input
              ref={nameRef}
              id="name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (getError('name')) setErrors((prev) => prev.filter((er) => er.field !== 'name'));
                if (formError) setFormError(null);
              }}
              invalid={!!getError('name')}
              aria-invalid={!!getError('name')}
              aria-describedby={getError('name') ? 'name-error' : undefined}
              disabled={loading}
              placeholder="Root Admin Name"
              autoComplete="name"
            />
          </Field>

          <Field label="Email" error={getError('email')} required>
            <Input
              ref={emailRef}
              id="email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (getError('email')) setErrors((prev) => prev.filter((er) => er.field !== 'email'));
                if (formError) setFormError(null);
              }}
              invalid={!!getError('email')}
              aria-invalid={!!getError('email')}
              aria-describedby={getError('email') ? 'email-error' : undefined}
              disabled={loading}
              placeholder="admin@shichida.in"
              autoComplete="email"
            />
          </Field>

          <Field label="Password" error={getError('password')} required>
            <Input
              ref={passwordRef}
              id="password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (getError('password')) setErrors((prev) => prev.filter((er) => er.field !== 'password'));
                if (formError) setFormError(null);
              }}
              invalid={!!getError('password')}
              aria-invalid={!!getError('password')}
              aria-describedby={getError('password') ? 'password-error' : undefined}
              disabled={loading}
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </Field>

          <Field label="Confirm Password" error={getError('confirmPassword')} required>
            <Input
              ref={confirmRef}
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (getError('confirmPassword')) setErrors((prev) => prev.filter((er) => er.field !== 'confirmPassword'));
                if (formError) setFormError(null);
              }}
              invalid={!!getError('confirmPassword')}
              aria-invalid={!!getError('confirmPassword')}
              aria-describedby={getError('confirmPassword') ? 'confirmPassword-error' : undefined}
              disabled={loading}
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </Field>
        </div>

        <Button
          type="submit"
          variant="primary"
          disabled={loading}
          className="w-full mt-6"
        >
          {loading ? (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            'Create Root Admin'
          )}
        </Button>
      </form>
    </AuthLayout>
  );
}
