import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Field, Textarea } from '@/components/ui/Input';
import { useStore } from '@/store/store';
import { formatLongDate, fromISODate } from '@/lib/dates';
import { uid } from '@/lib/ids';
import type { Child } from '@/lib/types';

export function NotesTab({ child }: { child: Child }) {
  const { notes, addNote } = useStore();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');

  const items = notes
    .filter((n) => n.childId === child.id)
    .sort((a, b) => (a.date < b.date ? 1 : -1));

  function add() {
    if (!text.trim()) return;
    addNote({
      id: uid('n'),
      childId: child.id,
      text: text.trim(),
      date: new Date().toISOString().slice(0, 10),
      staffName: 'You',
    });
    setText('');
    setOpen(false);
  }

  return (
    <div className="space-y-3">
      <button type="button" className="btn-dashed" onClick={() => setOpen(true)}>
        + Add note
      </button>

      {items.length === 0 ? (
        <div className="text-sm text-text-dim">No notes yet.</div>
      ) : (
        <ul className="space-y-2">
          {items.map((n) => (
            <li
              key={n.id}
              className="rounded-xl border border-border bg-bg-tertiary/60 p-4"
            >
              <div className="text-xs text-text-muted mb-1">
                {formatLongDate(fromISODate(n.date))} · {n.staffName}
              </div>
              <div className="text-sm">{n.text}</div>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        size="md"
        title="Add note"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="purple" onClick={add} disabled={!text.trim()}>
              Save note
            </Button>
          </div>
        }
      >
        <Field label="Note">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            placeholder="Daily note, observation, or info to share with staff..."
          />
        </Field>
      </Modal>
    </div>
  );
}
