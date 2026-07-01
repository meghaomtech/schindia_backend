import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { uid } from '@/lib/ids';

export type UserRole = 'root' | 'admin';
export type ApprovalStatus = 'approved' | 'pending' | 'rejected';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
}

interface StoredUser extends AuthUser {
  passwordHash: string;
  status: ApprovalStatus;
  requestedAt: string;
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
  register: (name: string, email: string, password: string) => Promise<void>;
  requestAccess: (name: string, email: string, password: string) => Promise<{ status: 'pending' }>;
  logout: () => void;
  getAccessRequests: () => AccessRequest[];
  approveRequest: (userId: string) => void;
  rejectRequest: (userId: string) => void;
}

const AUTH_USER_KEY = 'shichida_auth_user';
const AUTH_USERS_KEY = 'shichida_auth_users';

// WARNING: Java-style hashCode — not one-way and has massive collision risk.
// This is only acceptable for localStorage-only demo purposes.
// Passwords stored this way are plaintext-equivalent (visible via DevTools).
// If this ever moves to a real backend, replace with bcrypt or argon2 server-side.
function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash + char) | 0;
  }
  return hash.toString(36);
}

function getStoredUsers(): StoredUser[] {
  try {
    const raw = localStorage.getItem(AUTH_USERS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveStoredUsers(users: StoredUser[]) {
  localStorage.setItem(AUTH_USERS_KEY, JSON.stringify(users));
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
    // Simulate network delay
    await new Promise((r) => setTimeout(r, 500));

    const users = getStoredUsers();
    const found = users.find(
      (u) => u.email.toLowerCase() === email.toLowerCase() && u.passwordHash === simpleHash(password)
    );

    if (!found) {
      throw new Error('Invalid email or password');
    }

    if (found.status === 'pending') {
      throw new Error('Your access request is pending approval from the root admin.');
    }

    if (found.status === 'rejected') {
      throw new Error('Your access request has been rejected. Please contact the administrator.');
    }

    const authUser: AuthUser = { id: found.id, name: found.name, email: found.email, role: found.role };
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(authUser));
    setUser(authUser);
  }, []);

  const register = useCallback(async (name: string, email: string, password: string): Promise<void> => {
    // Simulate network delay
    await new Promise((r) => setTimeout(r, 500));

    const users = getStoredUsers();
    const exists = users.some((u) => u.email.toLowerCase() === email.toLowerCase());

    if (exists) {
      throw new Error('An account with this email already exists');
    }

    const newUser: StoredUser = {
      id: uid('usr'),
      name,
      email,
      passwordHash: simpleHash(password),
      role: 'admin',
      status: 'approved',
      requestedAt: new Date().toISOString(),
    };

    saveStoredUsers([...users, newUser]);

    // Auto-login after registration
    const authUser: AuthUser = { id: newUser.id, name: newUser.name, email: newUser.email, role: newUser.role };
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(authUser));
    setUser(authUser);
  }, []);

  const requestAccess = useCallback(async (name: string, email: string, password: string): Promise<{ status: 'pending' }> => {
    // Simulate network delay
    await new Promise((r) => setTimeout(r, 500));

    const users = getStoredUsers();
    const exists = users.some((u) => u.email.toLowerCase() === email.toLowerCase());

    if (exists) {
      throw new Error('An account with this email already exists');
    }

    const newUser: StoredUser = {
      id: uid('usr'),
      name,
      email,
      passwordHash: simpleHash(password),
      role: 'admin',
      status: 'pending',
      requestedAt: new Date().toISOString(),
    };

    saveStoredUsers([...users, newUser]);

    // Don't auto-login — user must wait for root approval
    return { status: 'pending' };
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_USER_KEY);
    setUser(null);
  }, []);

  const getAccessRequests = useCallback((): AccessRequest[] => {
    const users = getStoredUsers();
    return users
      .filter((u) => u.role !== 'root')
      .map((u) => ({
        id: u.id,
        name: u.name,
        email: u.email,
        status: u.status,
        requestedAt: u.requestedAt,
      }));
  }, []);

  const approveRequest = useCallback((userId: string) => {
    const users = getStoredUsers();
    const updated = users.map((u) =>
      u.id === userId ? { ...u, status: 'approved' as ApprovalStatus } : u
    );
    saveStoredUsers(updated);
  }, []);

  const rejectRequest = useCallback((userId: string) => {
    const users = getStoredUsers();
    const updated = users.map((u) =>
      u.id === userId ? { ...u, status: 'rejected' as ApprovalStatus } : u
    );
    saveStoredUsers(updated);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isRoot: user?.role === 'root',
      login,
      register,
      requestAccess,
      logout,
      getAccessRequests,
      approveRequest,
      rejectRequest,
    }),
    [user, login, register, requestAccess, logout, getAccessRequests, approveRequest, rejectRequest]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be used inside an <AuthProvider>');
  return ctx;
}
