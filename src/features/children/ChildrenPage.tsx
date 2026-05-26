import { useMemo, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { useStore } from '@/store/store';
import { ageString } from '@/lib/dates';
import { initialsOf, paletteFor } from '@/lib/colors';
import { RegisterChildModal } from './RegisterChildModal';
import { ChildProfile } from './ChildProfile';

export function ChildrenPage() {
  const { children: kids, centres, sessions } = useStore();
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(kids[0]?.id ?? null);
  const [showRegister, setShowRegister] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return kids;
    return kids.filter((c) =>
      `${c.firstName} ${c.lastName} ${c.systemId}`.toLowerCase().includes(q)
    );
  }, [kids, query]);

  const selected = kids.find((c) => c.id === selectedId) ?? null;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Children"
        subtitle="Register children, manage profiles and view bookings."
        right={
          <Button variant="purple" onClick={() => setShowRegister(true)}>
            + Register child
          </Button>
        }
      />

      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-4 space-y-3">
          <Input
            placeholder="Search by name or ID..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {filtered.length === 0 ? (
            <EmptyState
              title="No children found"
              description={query ? 'Try a different search.' : 'Register your first child.'}
            />
          ) : (
            <ul className="space-y-2">
              {filtered.map((c) => {
                const palette = paletteFor(c.firstName + ' ' + c.lastName);
                const centre = centres.find((x) => x.id === c.centreId);
                const session = sessions.find((s) => s.id === c.sessionId);
                const active = c.id === selectedId;
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
                          {ageString(c.dateOfBirth)} · {centre?.name ?? '—'}
                        </div>
                      </div>
                      {session && (
                        <Badge tone="beige">{session.name}</Badge>
                      )}
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
              title="Select a child"
              description="Choose a child from the list to view their profile."
            />
          )}
        </div>
      </div>

      <RegisterChildModal open={showRegister} onClose={() => setShowRegister(false)} />
    </div>
  );
}
