import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

export type UserRole = 'root' | 'admin';
export type ApprovalStatus = 'approved' | 'pending' | 'rejected';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

export interface AccessRequest {
  id: string;
  name: string;
  email: string;
  status: ApprovalStatus;
  requestedAt: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isRoot: boolean;
  login: (email: string, password: string) => Promise<void>;
  requestAccess: (name: string, email: string, password: string) => Promise<{ status: 'pending' }>;
  logout: () => Promise<void>;
  getAccessRequests: () => Promise<AccessRequest[]>;
  approveRequest: (userId: string) => Promise<void>;
  rejectRequest: (userId: string) => Promise<void>;
}

const AUTH_USER_KEY = 'shichida_auth_user';
const AUTH_TOKENS_KEY = 'shichida_auth_tokens';

const BASE_URL = import.meta.env.VITE_INVOICES_API_URL ?? 'http://127.0.0.1:8000';

async function apiFetch(path: string, options: RequestInit = {}) {
  const tokens = getStoredTokens();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };
  if (tokens?.access) {
    headers['Authorization'] = `Bearer ${tokens.access}`;
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const msg = data.detail
      ?? (data.email?.[0])
      ?? (data.password?.[0])
      ?? (data.name?.[0])
      ?? Object.values(data).flat()[0]
      ?? 'Something went wrong. Please try again.';
    throw new Error(msg as string);
  }
  return res.json();
}

function getStoredTokens(): { access: string; refresh: string } | null {
  try {
    const raw = localStorage.getItem(AUTH_TOKENS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function getPersistedUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

const AuthCtx = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => getPersistedUser());

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiFetch('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    const authUser: AuthUser = {
      id: data.user.id,
      name: data.user.name,
      email: data.user.email,
      role: data.user.role,
    };

    localStorage.setItem(AUTH_TOKENS_KEY, JSON.stringify({ access: data.access, refresh: data.refresh }));
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(authUser));
    setUser(authUser);
  }, []);

  const requestAccess = useCallback(async (name: string, email: string, password: string): Promise<{ status: 'pending' }> => {
    await apiFetch('/api/auth/request-access/', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });
    return { status: 'pending' };
  }, []);

  const logout = useCallback(async () => {
    const tokens = getStoredTokens();
    if (tokens?.refresh) {
      await apiFetch('/api/auth/logout/', {
        method: 'POST',
        body: JSON.stringify({ refresh: tokens.refresh }),
      }).catch(() => {});
    }
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem(AUTH_TOKENS_KEY);
    setUser(null);
  }, []);

  const getAccessRequests = useCallback(async (): Promise<AccessRequest[]> => {
    const data = await apiFetch('/api/auth/access-requests/');
    return data.map((r: { id: string; name: string; email: string; status: ApprovalStatus; requested_at: string }) => ({
      id: r.id,
      name: r.name,
      email: r.email,
      status: r.status,
      requestedAt: r.requested_at,
    }));
  }, []);

  const approveRequest = useCallback(async (userId: string) => {
    await apiFetch(`/api/auth/access-requests/${userId}/approve/`, { method: 'PATCH' });
  }, []);

  const rejectRequest = useCallback(async (userId: string) => {
    await apiFetch(`/api/auth/access-requests/${userId}/reject/`, { method: 'PATCH' });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isRoot: user?.role === 'root',
      login,
      requestAccess,
      logout,
      getAccessRequests,
      approveRequest,
      rejectRequest,
    }),
    [user, login, requestAccess, logout, getAccessRequests, approveRequest, rejectRequest]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used inside an <AuthProvider>');
  return ctx;
}
