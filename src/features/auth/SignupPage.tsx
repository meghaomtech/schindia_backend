import { useRef, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { useAuth } from './AuthContext';
import { AuthLayout } from './AuthLayout';
import { validateSignup } from './validateAuth';
import type { ValidationError } from '@/lib/types';

export function SignupPage() {
  const { signup, isAuthenticated, isRootSetup } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);

  // If root is not set up yet, redirect to root setup
  if (!isRootSetup) {
    return <Navigate to="/setup" replace />;
  }

  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate('/admin', { replace: true });
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
      await signup(name, email, password);
    } catch (err) {
      if (err instanceof Error && err.message === 'PENDING_APPROVAL') {
        setSubmitted(true);
      } else {
        setFormError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  // Show success state after request is submitted
  if (submitted) {
    return (
      <AuthLayout
        title="Request Submitted"
        footer={
          <span>
            Back to{' '}
            <Link to="/login" className="text-olive font-medium hover:underline">
              Log in
            </Link>
          </span>
        }
      >
        <div className="text-center py-4">
          <div className="w-16 h-16 rounded-full bg-olive/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-olive" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-charcoal mb-2">Pending Approval</h2>
          <p className="text-sm text-text-muted">
            Your access request has been submitted successfully. The root admin will review
            and approve your request. You'll be able to log in once approved.
          </p>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Request Admin Access"
      footer={
        <span>
          Already have an account?{' '}
          <Link to="/login" className="text-olive font-medium hover:underline">
            Log in
          </Link>
        </span>
      }
    >
      <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200">
        <p className="text-sm text-amber-800">
          <span className="font-medium">Note:</span>{' '}
          Your request will need approval from the root admin before you can access the portal.
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
              placeholder="John Doe"
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
              placeholder="you@example.com"
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
            'Request Access'
          )}
        </Button>
      </form>
    </AuthLayout>
  );
}
