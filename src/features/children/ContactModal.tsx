import { useEffect, useMemo, useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Input, Select } from '@/components/ui/Input';
import { Toggle } from '@/components/ui/Toggle';
import { uid } from '@/lib/ids';
import { validateContact } from '@/lib/validation';
import type { Contact, ContactInviteAs, ValidationError } from '@/lib/types';

const INVITE_OPTIONS: ContactInviteAs[] = [
  "Don't invite",
  'Parent',
  'Guardian',
  'Carer',
];

export function ContactModal({
  open,
  initial,
  forceMain,
  childName,
  onSave,
  onClose,
}: {
  open: boolean;
  initial: Contact | null;
  forceMain?: boolean;
  childName?: string;
  onSave: (c: Contact) => void;
  onClose: () => void;
}) {
  const [contact, setContact] = useState<Contact>(() =>
    initial ?? {
      id: uid('co'),
      name: '',
      relation: '',
      phone: '',
      email: '',
      inviteAs: "Don't invite",
      isMain: !!forceMain,
      isBillPayer: !!forceMain,
      isEmergency: !!forceMain,
    }
  );
  const [errors, setErrors] = useState<ValidationError[]>([]);

  useEffect(() => {
    if (!open) return;
    setContact(
      initial ?? {
        id: uid('co'),
        name: '',
        relation: '',
        phone: '',
        email: '',
        inviteAs: "Don't invite",
        isMain: !!forceMain,
        isBillPayer: !!forceMain,
        isEmergency: !!forceMain,
      }
    );
    setErrors([]);
  }, [open, initial?.id]);

  const errMap = useMemo(() => {
    const m: Record<string, string> = {};
    for (const e of errors) m[e.field] = e.message;
    return m;
  }, [errors]);

  const willInvite = contact.inviteAs !== "Don't invite";

  function setMain(v: boolean) {
    if (forceMain) return;
    if (v) {
      setContact({
        ...contact,
        isMain: true,
        isBillPayer: true,
        isEmergency: true,
      });
    } else {
      setContact({ ...contact, isMain: false });
    }
  }

  function save() {
    const errs = validateContact(contact);
    setErrors(errs);
    if (errs.length > 0) return;
    onSave(contact);
    onClose();
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={`Contact for ${childName || 'this child'}`}
      footer={
        <div className="flex items-center justify-between w-full">
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="purple" onClick={save}>
            Save contact
          </Button>
        </div>
      }
    >
      <div className="space-y-3">
        <Field label="Full name" required={contact.isMain} error={errMap.name}>
          <Input
            value={contact.name}
            onChange={(e) => setContact({ ...contact, name: e.target.value })}
            invalid={!!errMap.name}
          />
        </Field>

        <Field label="Email" required={contact.isMain || willInvite} error={errMap.email}>
          <div className="relative">
            <Input
              type="email"
              value={contact.email}
              onChange={(e) => setContact({ ...contact, email: e.target.value })}
              invalid={!!errMap.email}
              className="pr-9"
              placeholder="name@example.com"
            />
            <button
              type="button"
              aria-label="Scan email"
              title="Scan email from QR/business card"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-dim hover:text-accent-purple"
            >
              ⌖
            </button>
          </div>
        </Field>

        <Field label="Phone number" required={contact.isMain} error={errMap.phone}>
          <Input
            value={contact.phone}
            onChange={(e) => setContact({ ...contact, phone: e.target.value })}
            invalid={!!errMap.phone}
            placeholder="07700 900 000"
          />
        </Field>

        <Field label="Invite as">
          <Select
            value={contact.inviteAs}
            onChange={(e) =>
              setContact({ ...contact, inviteAs: e.target.value as ContactInviteAs })
            }
          >
            {INVITE_OPTIONS.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </Select>
        </Field>

        {willInvite && (
          <div className="rounded-md border border-accent-purple/40 bg-accent-purple-soft px-3 py-2 text-sm text-accent-purple">
            A login link will be sent to this contact's email once saved.
          </div>
        )}

        <Field label="Relation to child" required error={errMap.relation}>
          <Input
            value={contact.relation}
            placeholder="e.g. Mother, Father, Guardian"
            onChange={(e) => setContact({ ...contact, relation: e.target.value })}
            invalid={!!errMap.relation}
          />
        </Field>

        <hr className="border-border my-2" />

        <div className="space-y-3">
          <ToggleRow
            checked={contact.isMain}
            disabled={forceMain}
            onChange={setMain}
            title="Main contact"
            sub="Primary point of contact for this child"
          />
          <ToggleRow
            checked={contact.isBillPayer}
            onChange={(v) => setContact({ ...contact, isBillPayer: v })}
            title="Main bill payer"
            sub="Responsible for invoicing and payments"
          />
          <ToggleRow
            checked={contact.isEmergency}
            onChange={(v) => setContact({ ...contact, isEmergency: v })}
            title="Emergency contact"
            sub="Can be contacted in emergencies"
          />
        </div>
      </div>
    </Modal>
  );
}

function ToggleRow({
  checked,
  onChange,
  title,
  sub,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  title: string;
  sub: string;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <div className="text-sm font-medium">{title}</div>
        <div className="text-xs text-text-muted">{sub}</div>
      </div>
      <Toggle
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        ariaLabel={title}
      />
    </div>
  );
}
