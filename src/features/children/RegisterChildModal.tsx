import { useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { useStore } from '@/store/store';
import { initialsOf } from '@/lib/colors';
import { nextChildSystemId, uid } from '@/lib/ids';
import { validateChild } from '@/lib/validation';
import { ContactModal } from './ContactModal';
import type {
  Child,
  Contact,
  Gender,
  ValidationError,
} from '@/lib/types';

interface FormState {
  firstName: string;
  middleName: string;
  lastName: string;
  gender: Gender | '';
  centreId: string;
  sessionId: string;
  dateOfBirth: string;
  startDate: string;
  siblingId: string;
  contacts: Contact[];
}

const initialContact = (): Contact => ({
  id: uid('co'),
  name: '',
  relation: '',
  phone: '',
  email: '',
  inviteAs: 'Parent',
  isMain: true,
  isBillPayer: true,
  isEmergency: true,
});

const emptyForm = (): FormState => ({
  firstName: '',
  middleName: '',
  lastName: '',
  gender: '',
  centreId: '',
  sessionId: '',
  dateOfBirth: '',
  startDate: '',
  siblingId: '',
  contacts: [initialContact()],
});

export function RegisterChildModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { centres, children: kids, addChild } = useStore();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [systemId] = useState(() => nextChildSystemId());
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [siblingQuery, setSiblingQuery] = useState('');
  const [contactModal, setContactModal] = useState<{
    open: boolean;
    initial: Contact | null;
  }>({ open: false, initial: null });

  const errMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const e of errors) m[e.field] = e.message;
    return m;
  }, [errors]);

  const siblingMatches = useMemo(() => {
    const q = siblingQuery.trim().toLowerCase();
    if (!q) return [];
    return kids
      .filter((c) =>
        `${c.firstName} ${c.lastName} ${c.systemId}`.toLowerCase().includes(q)
      )
      .slice(0, 5);
  }, [kids, siblingQuery]);

  const sibling = form.siblingId
    ? kids.find((c) => c.id === form.siblingId) ?? null
    : null;

  function reset() {
    setForm(emptyForm());
    setErrors([]);
    setSiblingQuery('');
  }

  function handleClose() {
    reset();
    onClose();
  }

  function save() {
    const errs = validateChild({
      firstName: form.firstName,
      middleName: form.middleName,
      lastName: form.lastName,
      gender: (form.gender || 'Female') as Gender,
      centreId: form.centreId,
      sessionId: form.sessionId || undefined,
      dateOfBirth: form.dateOfBirth,
      startDate: form.startDate,
      contacts: form.contacts,
    });
    if (!form.gender) {
      errs.unshift({ field: 'gender', message: 'Gender is required' });
    }
    setErrors(errs);
    if (errs.length > 0) return;

    const child: Child = {
      id: uid('ch'),
      systemId,
      firstName: form.firstName.trim(),
      middleName: form.middleName.trim() || undefined,
      lastName: form.lastName.trim(),
      gender: form.gender as Gender,
      centreId: form.centreId,
      sessionId: form.sessionId || undefined,
      dateOfBirth: form.dateOfBirth,
      startDate: form.startDate,
      siblingId: form.siblingId || undefined,
      contacts: form.contacts,
    };
    addChild(child);
    handleClose();
  }

  function upsertContact(c: Contact) {
    setForm((f) => {
      const existing = f.contacts.find((x) => x.id === c.id);
      if (existing) {
        return {
          ...f,
          contacts: f.contacts.map((x) => (x.id === c.id ? c : x)),
        };
      }
      return { ...f, contacts: [...f.contacts, c] };
    });
  }

  function removeContact(id: string) {
    setForm((f) => {
      const target = f.contacts.find((x) => x.id === id);
      if (!target || target.isMain) return f;
      return { ...f, contacts: f.contacts.filter((x) => x.id !== id) };
    });
  }

  function setAsMain(id: string) {
    setForm((f) => ({
      ...f,
      contacts: f.contacts.map((c) =>
        c.id === id
          ? { ...c, isMain: true, isBillPayer: true, isEmergency: true }
          : { ...c, isMain: false }
      ),
    }));
  }

  return (
    <>
      <Modal
        open={open}
        onClose={handleClose}
        size="lg"
        title={
          <div>
            <div className="text-base font-semibold">1. Child information</div>
            <div className="text-xs text-text-muted font-normal">
              # System ID: <span className="font-mono">{systemId}</span>
            </div>
          </div>
        }
        topStrip={
          <div className="h-1 bg-accent-purple-soft">
            <div className="h-1 bg-accent-purple" style={{ width: '33%' }} />
          </div>
        }
        footer={
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-1.5" aria-label="Step indicator">
              <span className="h-2 w-6 rounded-full bg-accent-purple" />
              <span className="h-2 w-2 rounded-full bg-border-strong" />
              <span className="h-2 w-2 rounded-full bg-border-strong" />
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleClose}>Cancel</Button>
              <Button variant="purple" onClick={save}>
                Register child
              </Button>
            </div>
          </div>
        }
      >
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3">
            <Field label="First name" required error={errMap.firstName}>
              <Input
                value={form.firstName}
                onChange={(e) => setForm({ ...form, firstName: e.target.value })}
                invalid={!!errMap.firstName}
              />
            </Field>
            <Field label="Middle name">
              <Input
                value={form.middleName}
                onChange={(e) => setForm({ ...form, middleName: e.target.value })}
              />
            </Field>
          </div>

          <Field label="Last name" required error={errMap.lastName}>
            <Input
              value={form.lastName}
              onChange={(e) => setForm({ ...form, lastName: e.target.value })}
              invalid={!!errMap.lastName}
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Gender" required error={errMap.gender}>
              <Select
                value={form.gender}
                onChange={(e) =>
                  setForm({ ...form, gender: e.target.value as Gender | '' })
                }
                invalid={!!errMap.gender}
              >
                <option value="">— Select gender —</option>
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
                <option>Prefer not to say</option>
              </Select>
            </Field>
            <Field label="Centre" required error={errMap.centreId}>
              <Select
                value={form.centreId}
                onChange={(e) => setForm({ ...form, centreId: e.target.value })}
                invalid={!!errMap.centreId}
              >
                <option value="">— Select centre —</option>
                {centres.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Date of birth">
              <div className="relative">
                <Input
                  type="date"
                  value={form.dateOfBirth}
                  onChange={(e) => setForm({ ...form, dateOfBirth: e.target.value })}
                  className="pr-9"
                />
                <span
                  aria-hidden="true"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-dim pointer-events-none"
                >
                  📅
                </span>
              </div>
            </Field>
            <Field label="Start date" required error={errMap.startDate}>
              <div className="relative">
                <Input
                  type="date"
                  value={form.startDate}
                  onChange={(e) => setForm({ ...form, startDate: e.target.value })}
                  invalid={!!errMap.startDate}
                  className="pr-9"
                />
                <span
                  aria-hidden="true"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-dim pointer-events-none"
                >
                  📅
                </span>
              </div>
            </Field>
          </div>

          <Field
            label="Connect to a sibling"
            hint="Search by name or system ID"
          >
            {sibling ? (
              <div className="flex items-center justify-between rounded-md border border-border bg-bg-elev px-3 py-2">
                <div className="text-sm">
                  <span className="font-semibold">
                    {sibling.firstName} {sibling.lastName}
                  </span>{' '}
                  <span className="text-text-muted font-mono">{sibling.systemId}</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setForm({ ...form, siblingId: '' });
                    setSiblingQuery('');
                  }}
                  className="text-xs text-accent-purple hover:underline"
                >
                  Clear
                </button>
              </div>
            ) : (
              <div className="relative">
                <Input
                  value={siblingQuery}
                  onChange={(e) => setSiblingQuery(e.target.value)}
                  placeholder="Search siblings..."
                />
                {siblingMatches.length > 0 && (
                  <ul className="absolute z-10 mt-1 w-full bg-white border border-border rounded-md shadow-card max-h-48 overflow-auto">
                    {siblingMatches.map((c) => (
                      <li key={c.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setForm({ ...form, siblingId: c.id });
                            setSiblingQuery('');
                          }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-bg-elev flex items-center justify-between"
                        >
                          <span>
                            {c.firstName} {c.lastName}
                          </span>
                          <span className="font-mono text-xs text-text-muted">
                            {c.systemId}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Field>

          <hr className="border-border" />

          <div>
            <div className="flex items-center justify-between mb-2">
              <div>
                <div className="text-base font-semibold">Contact details</div>
                <div className="text-xs text-text-muted">
                  At least one main contact is required.
                </div>
              </div>
            </div>
            {errMap.contacts && (
              <div className="text-xs text-danger mb-2">{errMap.contacts}</div>
            )}
            {(errMap['mainContact.name'] ||
              errMap['mainContact.email'] ||
              errMap['mainContact.phone'] ||
              errMap['mainContact.relation']) && (
              <div className="text-xs text-danger mb-2">
                Main contact is missing required fields.
              </div>
            )}

            <div className="space-y-3">
              {form.contacts.map((c) => (
                <ContactCard
                  key={c.id}
                  contact={c}
                  onEdit={() => setContactModal({ open: true, initial: c })}
                  onRemove={() => removeContact(c.id)}
                  onSetMain={() => setAsMain(c.id)}
                />
              ))}
            </div>

            <button
              type="button"
              className="btn-dashed mt-3"
              onClick={() => setContactModal({ open: true, initial: null })}
            >
              + Add another contact
            </button>
          </div>
        </div>
      </Modal>

      <ContactModal
        open={contactModal.open}
        initial={contactModal.initial}
        forceMain={contactModal.initial?.isMain ?? false}
        childName={
          form.firstName || form.lastName
            ? `${form.firstName} ${form.lastName}`.trim()
            : 'this child'
        }
        onSave={upsertContact}
        onClose={() => setContactModal({ open: false, initial: null })}
      />
    </>
  );
}

function ContactCard({
  contact,
  onEdit,
  onRemove,
  onSetMain,
}: {
  contact: Contact;
  onEdit: () => void;
  onRemove: () => void;
  onSetMain: () => void;
}) {
  const initials = initialsOf(contact.name || '?');
  return (
    <div
      className={[
        'rounded-xl border p-4',
        contact.isMain
          ? 'border-accent-purple bg-accent-purple/[0.04]'
          : 'border-border bg-white',
      ].join(' ')}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-full inline-flex items-center justify-center font-semibold text-sm bg-accent-purple-soft text-accent-purple">
            {initials}
          </span>
          <div>
            <div className="font-semibold leading-tight">
              {contact.name || '(unnamed)'}
            </div>
            <div className="text-xs text-text-muted">
              {contact.relation || '—'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {contact.isMain && (
            <Badge tone="purple">★ Main contact</Badge>
          )}
          {contact.isBillPayer && <Badge tone="blue">Bill payer</Badge>}
          {contact.isEmergency && <Badge tone="coral">Emergency</Badge>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm mb-3">
        <div>
          <div className="text-xs text-text-muted">Phone</div>
          <div>{contact.phone || '—'}</div>
        </div>
        <div>
          <div className="text-xs text-text-muted">Email</div>
          <div className="truncate">{contact.email || '—'}</div>
        </div>
      </div>

      <div className="flex items-center justify-end gap-2">
        {!contact.isMain && (
          <Button onClick={onSetMain}>Set as main</Button>
        )}
        <Button onClick={onEdit}>Edit</Button>
        {!contact.isMain && (
          <Button
            variant="ghost"
            aria-label={`Remove contact ${contact.name}`}
            onClick={onRemove}
            className="text-danger"
          >
            Remove
          </Button>
        )}
      </div>
    </div>
  );
}
