import { useState } from 'react';
import type { ComponentType, SVGProps } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Field, Select, Textarea } from '@/components/ui/Input';
import { ChartIcon, StarIcon } from '@/components/ui/icons';
import { useStore } from '@/store/store';
import { formatLongDate, fromISODate } from '@/lib/dates';
import { uid } from '@/lib/ids';
import type { Child, JourneyType } from '@/lib/types';

const ICON_FOR: Record<
  JourneyType,
  { bg: string; fg: string; Icon: ComponentType<SVGProps<SVGSVGElement>> }
> = {
  Milestone: { bg: '#ece6f8', fg: '#7c5fbf', Icon: StarIcon },
  Observation: { bg: '#dcfce7', fg: '#166534', Icon: ChartIcon },
};

export function JourneyTab({ child }: { child: Child }) {
  const { journeyEntries, addJourneyEntry } = useStore();
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<JourneyType>('Milestone');
  const [text, setText] = useState('');

  const items = journeyEntries
    .filter((e) => e.childId === child.id)
    .sort((a, b) => (a.date < b.date ? 1 : -1));

  function add() {
    if (!text.trim()) return;
    addJourneyEntry({
      id: uid('je'),
      childId: child.id,
      type,
      text: text.trim(),
      date: new Date().toISOString().slice(0, 10),
      staffName: 'You',
    });
    setText('');
    setType('Milestone');
    setOpen(false);
  }

  return (
    <div className="space-y-3">
      <button type="button" className="btn-dashed" onClick={() => setOpen(true)}>
        + Add journey entry
      </button>

      {items.length === 0 ? (
        <div className="text-sm text-text-dim">No journey entries yet.</div>
      ) : (
        <ul className="space-y-3">
          {items.map((e) => {
            const { bg, fg, Icon } = ICON_FOR[e.type];
            return (
              <li key={e.id} className="flex items-start gap-3">
                <span
                  className="w-9 h-9 rounded-full inline-flex items-center justify-center shrink-0"
                  style={{ background: bg, color: fg }}
                  aria-hidden="true"
                >
                  <Icon width={16} height={16} />
                </span>
                <div className="flex-1 card p-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <Badge tone={e.type === 'Milestone' ? 'purple' : 'green'}>
                      {e.type}
                    </Badge>
                    <span className="text-xs text-text-muted">
                      {formatLongDate(fromISODate(e.date))}
                    </span>
                  </div>
                  <div className="text-sm">{e.text}</div>
                  <div className="text-xs text-text-muted mt-1.5">
                    Logged by {e.staffName}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        size="md"
        title="Add journey entry"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button variant="purple" onClick={add} disabled={!text.trim()}>
              Save entry
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <Field label="Type">
            <Select
              value={type}
              onChange={(e) => setType(e.target.value as JourneyType)}
            >
              <option>Milestone</option>
              <option>Observation</option>
            </Select>
          </Field>
          <Field label="Description">
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              placeholder="What happened?"
            />
          </Field>
        </div>
      </Modal>
    </div>
  );
}
