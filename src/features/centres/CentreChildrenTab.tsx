import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { useStore } from '@/store/store';
import { ageString } from '@/lib/dates';
import { initialsOf, paletteFor } from '@/lib/colors';
import { RegisterChildModal } from '@/features/children/RegisterChildModal';
import { ChildProfile } from '@/features/children/ChildProfile';
import type { Centre } from '@/lib/types';

export function CentreChildrenTab({ centre }: { centre: Centre }) {
  const { children: kids, sessions } = useStore();
  const [query, setQuery] = useState('');
  const centreKids = useMemo(
    () => kids.filter((c) => c.centreId === centre.id),
    [kids, centre.id]
  );
  const [selectedId, setSelectedId] = useState<string | null>(
    centreKids[0]?.id ?? null
  );
  const [showRegister, setShowRegister] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return centreKids;
    return centreKids.filter((c) =>
      `${c.firstName} ${c.lastName} ${c.systemId}`.toLowerCase().includes(q)
    );
  }, [centreKids, query]);

  const selected =
    centreKids.find((c) => c.id === selectedId) ?? centreKids[0] ?? null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-base font-semibold text-charcoal">
            Children at {centre.name}
          </div>
          <div className="text-sm text-text-muted">
            Register and manage children enrolled at this centre.
          </div>
        </div>
        <Button variant="purple" onClick={() => setShowRegister(true)}>
          + Register child
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-4 space-y-3">
          <Input
            placeholder="Search by name or ID..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {filtered.length === 0 ? (
            <EmptyState
              title="No children at this centre"
              description={
                query ? 'Try a different search.' : 'Register a child to get started.'
              }
            />
          ) : (
            <ul className="space-y-2">
              {filtered.map((c) => {
                const palette = paletteFor(c.firstName + ' ' + c.lastName);
                const session = sessions.find((s) => s.id === c.sessionId);
                const active = c.id === selected?.id;
                return (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(c.id)}
                      aria-pressed={active}
                      className={[
                        'card w-full p-3 text-left flex items-center gap-3 transition-shadow',
                        active ? 'ring-2 ring-olive' : 'hover:shadow-md',
                      ].join(' ')}
                    >
                      <span
                        className="w-10 h-10 rounded-full inline-flex items-center justify-center font-semibold text-sm"
                        style={{ background: palette.bg, color: palette.text }}
                      >
                        {initialsOf(`${c.firstName} ${c.lastName}`)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold truncate">
                          {c.firstName} {c.lastName}
                        </div>
                        <div className="text-xs text-text-muted truncate">
                          {ageString(c.dateOfBirth)}
                        </div>
                      </div>
                      {session && <Badge tone="beige">{session.name}</Badge>}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="col-span-8">
          {selected ? (
            <ChildProfile child={selected} />
          ) : (
            <EmptyState
              title="No child selected"
              description="Register a child or select one from the list."
            />
          )}
        </div>
      </div>

      <RegisterChildModal
        open={showRegister}
        onClose={() => setShowRegister(false)}
        defaultCentreId={centre.id}
      />
    </div>
  );
}
