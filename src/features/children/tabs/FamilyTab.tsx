import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { StarIcon } from '@/components/ui/icons';
import { useStore } from '@/store/store';
import { initialsOf } from '@/lib/colors';
import { ContactModal } from '../ContactModal';
import type { Child, Contact } from '@/lib/types';

export function FamilyTab({ child }: { child: Child }) {
  const { updateChild } = useStore();
  const [modal, setModal] = useState<{ open: boolean; initial: Contact | null }>({
    open: false,
    initial: null,
  });

  function upsertContact(c: Contact) {
    if (c.isMain) {
      const contacts = child.contacts.map((x) =>
        x.id === c.id ? c : { ...x, isMain: false }
      );
      const exists = contacts.some((x) => x.id === c.id);
      updateChild(child.id, {
        contacts: exists ? contacts : [...contacts, c],
      });
      return;
    }
    const exists = child.contacts.some((x) => x.id === c.id);
    const contacts = exists
      ? child.contacts.map((x) => (x.id === c.id ? c : x))
      : [...child.contacts, c];
    updateChild(child.id, { contacts });
  }

  function removeContact(id: string) {
    const target = child.contacts.find((c) => c.id === id);
    if (!target || target.isMain) return;
    updateChild(child.id, {
      contacts: child.contacts.filter((c) => c.id !== id),
    });
  }

  function setAsMain(id: string) {
    const contacts = child.contacts.map((c) =>
      c.id === id
        ? { ...c, isMain: true, isBillPayer: true, isEmergency: true }
        : { ...c, isMain: false }
    );
    updateChild(child.id, { contacts });
  }

  return (
    <div className="space-y-3">
      <div className="space-y-3">
        {child.contacts.map((c) => (
          <ContactDisplayCard
            key={c.id}
            contact={c}
            onEdit={() => setModal({ open: true, initial: c })}
            onRemove={() => removeContact(c.id)}
            onSetMain={() => setAsMain(c.id)}
          />
        ))}
      </div>

      <button
        type="button"
        className="btn-dashed"
        onClick={() => setModal({ open: true, initial: null })}
      >
        + Add contact
      </button>

      <ContactModal
        open={modal.open}
        initial={modal.initial}
        forceMain={modal.initial?.isMain ?? false}
        childName={`${child.firstName} ${child.lastName}`}
        onSave={upsertContact}
        onClose={() => setModal({ open: false, initial: null })}
      />
    </div>
  );
}

function ContactDisplayCard({
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
  return (
    <div
      className={[
        'rounded-xl border p-4 bg-bg-card',
        contact.isMain ? 'border-accent-purple' : 'border-border',
      ].join(' ')}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="w-10 h-10 rounded-full inline-flex items-center justify-center font-semibold text-sm bg-accent-purple-soft text-accent-purple">
            {initialsOf(contact.name || '?')}
          </span>
          <div>
            <div className="font-semibold leading-tight">{contact.name}</div>
            <div className="text-xs text-text-muted">{contact.relation}</div>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap justify-end">
          {contact.isMain && (
            <Badge tone="purple">
              <StarIcon width={11} height={11} className="mr-1" />
              Main contact
            </Badge>
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
        {!contact.isMain && <Button onClick={onSetMain}>Set as main</Button>}
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
