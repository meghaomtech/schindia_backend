import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type {
  BillPayerBalance,
  Centre,
  Child,
  ChildEnrolment,
  ChildNote,
  ID,
  Invoice,
  JourneyEntry,
  Purchase,
  Role,
  RoleMember,
  RolePermission,
  Session,
  SessionSlot,
  Teacher,
} from '@/lib/types';
import {
  seedBillPayerBalances,
  seedCentres,
  seedChildren,
  seedEnrolments,
  seedPurchases,
  seedRoles,
  seedSessions,
  seedSlots,
  seedTeachers,
} from '@/lib/seed';
import { uid } from '@/lib/ids';

export interface StoreState {
  centres: Centre[];
  sessions: Session[];
  slots: SessionSlot[];
  teachers: Teacher[];
  children: Child[];
  journeyEntries: JourneyEntry[];
  notes: ChildNote[];
  enrolments: ChildEnrolment[];
  purchases: Purchase[];
  billPayerBalances: BillPayerBalance[];
  invoices: Invoice[];
  roles: Role[];
}

export interface StoreActions {
  // Centres
  addCentre: (c: Centre) => void;
  updateCentre: (id: ID, patch: Partial<Centre>) => void;
  // Sessions
  addSession: (s: Session) => void;
  updateSession: (id: ID, patch: Partial<Session>) => void;
  deleteSession: (id: ID) => void;
  // Slots
  addSlot: (s: SessionSlot) => void;
  updateSlot: (id: ID, patch: Partial<SessionSlot>) => void;
  deleteSlot: (id: ID) => void;
  // Children
  addChild: (c: Child) => void;
  updateChild: (id: ID, patch: Partial<Child>) => void;
  // Journey & notes
  addJourneyEntry: (e: JourneyEntry) => void;
  addNote: (n: ChildNote) => void;
  // Enrolments
  upsertEnrolment: (e: ChildEnrolment) => void;
  removeEnrolment: (id: ID) => void;
  // Purchases
  addPurchase: (p: Purchase) => void;
  // Invoices
  addInvoice: (i: Invoice) => void;
  updateInvoice: (id: ID, patch: Partial<Invoice>) => void;
  deleteInvoice: (id: ID) => void;
  // Roles
  addRole: (r: Role) => void;
  updateRole: (id: ID, patch: Partial<Role>) => void;
  deleteRole: (id: ID) => void;
  updateRolePermission: (roleId: ID, permissionKey: string, patch: Partial<RolePermission>) => void;
  addRoleMember: (roleId: ID, member: RoleMember) => void;
  removeRoleMember: (roleId: ID, memberId: ID) => void;
}

type StoreCtx = StoreState & StoreActions;

const Ctx = createContext<StoreCtx | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<StoreState>(() => ({
    centres: seedCentres,
    sessions: seedSessions,
    slots: seedSlots,
    teachers: seedTeachers,
    children: seedChildren,
    journeyEntries: [
      {
        id: uid('je'),
        childId: 'ch1',
        type: 'Milestone',
        text: 'First shapes recognition — Olivia correctly identified circle, square and triangle.',
        date: '2026-05-19',
        staffName: 'Ms. Johnson',
      },
      {
        id: uid('je'),
        childId: 'ch1',
        type: 'Observation',
        text: 'Olivia showed great enthusiasm during painting, helping peers with colour mixing.',
        date: '2026-05-12',
        staffName: 'Mr. Patel',
      },
    ],
    notes: [
      {
        id: uid('n'),
        childId: 'ch1',
        text: 'Parent mentioned Olivia had a difficult morning at home before drop-off. She settled well after 15 minutes.',
        date: '2026-05-19',
        staffName: 'Ms. Johnson',
      },
    ],
    enrolments: seedEnrolments,
    purchases: seedPurchases,
    billPayerBalances: seedBillPayerBalances,
    invoices: [],
    roles: seedRoles,
  }));

  const addCentre = useCallback(
    (c: Centre) => setState((s) => ({ ...s, centres: [...s.centres, c] })),
    []
  );
  const updateCentre = useCallback(
    (id: ID, patch: Partial<Centre>) =>
      setState((s) => ({
        ...s,
        centres: s.centres.map((c) => (c.id === id ? { ...c, ...patch } : c)),
      })),
    []
  );

  const addSession = useCallback(
    (sn: Session) => setState((s) => ({ ...s, sessions: [...s.sessions, sn] })),
    []
  );
  const updateSession = useCallback(
    (id: ID, patch: Partial<Session>) =>
      setState((s) => ({
        ...s,
        sessions: s.sessions.map((x) => (x.id === id ? { ...x, ...patch } : x)),
      })),
    []
  );
  const deleteSession = useCallback(
    (id: ID) => setState((s) => ({ ...s, sessions: s.sessions.filter((x) => x.id !== id) })),
    []
  );

  const addSlot = useCallback(
    (sl: SessionSlot) => setState((s) => ({ ...s, slots: [...s.slots, sl] })),
    []
  );
  const updateSlot = useCallback(
    (id: ID, patch: Partial<SessionSlot>) =>
      setState((s) => ({
        ...s,
        slots: s.slots.map((x) => (x.id === id ? { ...x, ...patch } : x)),
      })),
    []
  );
  const deleteSlot = useCallback(
    (id: ID) => setState((s) => ({ ...s, slots: s.slots.filter((x) => x.id !== id) })),
    []
  );

  const addChild = useCallback(
    (c: Child) => setState((s) => ({ ...s, children: [...s.children, c] })),
    []
  );
  const updateChild = useCallback(
    (id: ID, patch: Partial<Child>) =>
      setState((s) => ({
        ...s,
        children: s.children.map((x) => (x.id === id ? { ...x, ...patch } : x)),
      })),
    []
  );

  const addJourneyEntry = useCallback(
    (e: JourneyEntry) => setState((s) => ({ ...s, journeyEntries: [e, ...s.journeyEntries] })),
    []
  );
  const addNote = useCallback(
    (n: ChildNote) => setState((s) => ({ ...s, notes: [n, ...s.notes] })),
    []
  );

  const upsertEnrolment = useCallback(
    (e: ChildEnrolment) =>
      setState((s) => {
        const exists = s.enrolments.some((x) => x.id === e.id);
        const enrolments = exists
          ? s.enrolments.map((x) => (x.id === e.id ? e : x))
          : [...s.enrolments, e];
        const slot = s.slots.find((x) => x.id === e.slotId);
        if (!slot) return { ...s, enrolments };
        const slots = s.slots.map((x) =>
          x.id === e.slotId
            ? { ...x, childIds: x.childIds.includes(e.childId) ? x.childIds : [...x.childIds, e.childId] }
            : x
        );
        return { ...s, enrolments, slots };
      }),
    []
  );

  const removeEnrolment = useCallback(
    (id: ID) =>
      setState((s) => {
        const target = s.enrolments.find((x) => x.id === id);
        if (!target) return s;
        const enrolments = s.enrolments.filter((x) => x.id !== id);
        const stillEnrolledInSlot = enrolments.some(
          (x) => x.slotId === target.slotId && x.childId === target.childId
        );
        const slots = stillEnrolledInSlot
          ? s.slots
          : s.slots.map((x) =>
              x.id === target.slotId
                ? { ...x, childIds: x.childIds.filter((cid) => cid !== target.childId) }
                : x
            );
        return { ...s, enrolments, slots };
      }),
    []
  );

  const addPurchase = useCallback(
    (p: Purchase) =>
      setState((s) => ({ ...s, purchases: [p, ...s.purchases] })),
    []
  );

  const addInvoice = useCallback(
    (i: Invoice) =>
      setState((s) => ({ ...s, invoices: [i, ...s.invoices] })),
    []
  );
  const updateInvoice = useCallback(
    (id: ID, patch: Partial<Invoice>) =>
      setState((s) => ({
        ...s,
        invoices: s.invoices.map((x) => (x.id === id ? { ...x, ...patch } : x)),
      })),
    []
  );
  const deleteInvoice = useCallback(
    (id: ID) =>
      setState((s) => ({
        ...s,
        invoices: s.invoices.filter((x) => x.id !== id),
      })),
    []
  );

  const addRole = useCallback(
    (r: Role) => setState((s) => ({ ...s, roles: [...s.roles, r] })),
    []
  );
  const updateRole = useCallback(
    (id: ID, patch: Partial<Role>) =>
      setState((s) => ({
        ...s,
        roles: s.roles.map((r) => (r.id === id ? { ...r, ...patch } : r)),
      })),
    []
  );
  const deleteRole = useCallback(
    (id: ID) => setState((s) => ({ ...s, roles: s.roles.filter((r) => r.id !== id) })),
    []
  );
  const updateRolePermission = useCallback(
    (roleId: ID, permissionKey: string, patch: Partial<RolePermission>) =>
      setState((s) => ({
        ...s,
        roles: s.roles.map((r) =>
          r.id === roleId
            ? {
                ...r,
                permissions: r.permissions.map((p) =>
                  p.key === permissionKey ? { ...p, ...patch } : p
                ),
              }
            : r
        ),
      })),
    []
  );
  const addRoleMember = useCallback(
    (roleId: ID, member: RoleMember) =>
      setState((s) => ({
        ...s,
        roles: s.roles.map((r) =>
          r.id === roleId ? { ...r, members: [...r.members, member] } : r
        ),
      })),
    []
  );
  const removeRoleMember = useCallback(
    (roleId: ID, memberId: ID) =>
      setState((s) => ({
        ...s,
        roles: s.roles.map((r) =>
          r.id === roleId
            ? { ...r, members: r.members.filter((m) => m.id !== memberId) }
            : r
        ),
      })),
    []
  );

  const value = useMemo<StoreCtx>(
    () => ({
      ...state,
      addCentre,
      updateCentre,
      addSession,
      updateSession,
      deleteSession,
      addSlot,
      updateSlot,
      deleteSlot,
      addChild,
      updateChild,
      addJourneyEntry,
      addNote,
      upsertEnrolment,
      removeEnrolment,
      addPurchase,
      addInvoice,
      updateInvoice,
      deleteInvoice,
      addRole,
      updateRole,
      deleteRole,
      updateRolePermission,
      addRoleMember,
      removeRoleMember,
    }),
    [
      state,
      addCentre,
      updateCentre,
      addSession,
      updateSession,
      deleteSession,
      addSlot,
      updateSlot,
      deleteSlot,
      addChild,
      updateChild,
      addJourneyEntry,
      addNote,
      upsertEnrolment,
      removeEnrolment,
      addPurchase,
      addInvoice,
      updateInvoice,
      deleteInvoice,
      addRole,
      updateRole,
      deleteRole,
      updateRolePermission,
      addRoleMember,
      removeRoleMember,
    ]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore(): StoreCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useStore must be used inside a <StoreProvider>');
  return ctx;
}
