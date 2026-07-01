import { useRef, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Field, Input } from '@/components/ui/Input';
import { useAuth } from './AuthContext';
import { AuthLayout } from './AuthLayout';
import { validateLogin } from './validateAuth';
import type { ValidationError } from '@/lib/types';

export function LoginPage() {
  const { login, isAuthenticated, isRootSetup } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state && typeof location.state === 'object' && 'from' in location.state
    ? (location.state as { from?: string }).from
    : undefined) || '/admin';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  // If root is not set up yet, redirect to root setup
  if (!isRootSetup) {
    return <Navigate to="/setup" replace />;
  }

  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/admin" replace />;
  }

  function getError(field: string) {
    return errors.find((e) => e.field === field)?.message ?? null;
  }

  function focusFirstError(errs: ValidationError[]) {
    const first = errs[0]?.field;
    if (first === 'email') emailRef.current?.focus();
    else if (first === 'password') passwordRef.current?.focus();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);

    const validationErrors = validateLogin({ email, password });
    setErrors(validationErrors);

    if (validationErrors.length > 0) {
      focusFirstError(validationErrors);
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
      setPassword('');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Sign in to your account"
      footer={
        <span>
          Don't have an account?{' '}
          <Link to="/signup" className="text-olive font-medium hover:underline">
            Request access
          </Link>
        </span>
      }
    >
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
              autoComplete="current-password"
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
            'Sign In'
          )}
        </Button>

        <div className="mt-3 text-center">
          <button type="button" className="text-sm text-text-muted hover:text-text transition-colors">
            Forgot password?
          </button>
        </div>
      </form>
    </AuthLayout>
  );
}
