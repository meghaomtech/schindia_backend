import { useMemo, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { Tabs } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { useStore } from '@/store/store';
import { initialsOf, paletteFor } from '@/lib/colors';
import { AddCentreModal } from './AddCentreModal';
import { CentreCard, NewCentreCard } from './CentreCard';
import { CentreDetailsTab } from './CentreDetailsTab';
import { ClosureDatesTab } from './ClosureDatesTab';
import { OpeningTimesTab } from './OpeningTimesTab';

type CentreTab = 'details' | 'closure' | 'opening';

const TAB_ITEMS: { key: CentreTab; label: string }[] = [
  { key: 'details', label: 'Centre details' },
  { key: 'closure', label: 'Closure dates' },
  { key: 'opening', label: 'Opening times' },
];

export function CentresPage() {
  const { centres } = useStore();
  const [openId, setOpenId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<CentreTab>('details');
  const [showAdd, setShowAdd] = useState(false);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return centres;
    return centres.filter((c) =>
      `${c.name} ${c.systemId} ${c.city} ${c.managerName}`
        .toLowerCase()
        .includes(q)
    );
  }, [centres, query]);

  const open = centres.find((c) => c.id === openId) ?? null;

  if (open) {
    const palette = paletteFor(open.name);
    return (
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <Button onClick={() => setOpenId(null)} aria-label="Back to centres">
            ← Back to centres
          </Button>
        </div>

        <div className="card p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <span
                className="w-14 h-14 rounded-full inline-flex items-center justify-center font-bold text-lg"
                style={{ background: palette.bg, color: palette.text }}
              >
                {initialsOf(open.name)}
              </span>
              <div>
                <div className="text-xl font-semibold">{open.name}</div>
                <div className="text-sm text-text-muted">
                  {open.streetAddress}, {open.city}, {open.postcode}
                </div>
                <div className="text-xs text-text-dim font-mono mt-0.5">
                  {open.systemId}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone="beige">{open.rooms.length} rooms</Badge>
              <Badge tone="olive">{open.closureDates.length} closure days</Badge>
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-5">
          <Tabs<CentreTab>
            items={TAB_ITEMS}
            active={activeTab}
            onChange={setActiveTab}
          />
          <div className="pt-2">
            {activeTab === 'details' && <CentreDetailsTab centre={open} />}
            {activeTab === 'closure' && <ClosureDatesTab centre={open} />}
            {activeTab === 'opening' && <OpeningTimesTab centre={open} />}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Centres"
        subtitle="Browse your centres. Open a card to view or edit details."
        right={
          <Button variant="primary" onClick={() => setShowAdd(true)}>
            + Add centre
          </Button>
        }
      />

      {centres.length > 0 && (
        <div className="max-w-sm">
          <Input
            placeholder="Search centres by name, ID, city or manager..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      )}

      {centres.length === 0 ? (
        <EmptyState
          title="No centres yet"
          description="Add your first centre to get started."
          action={
            <Button variant="primary" onClick={() => setShowAdd(true)}>
              + Add centre
            </Button>
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No centres match your search"
          description="Try a different keyword or clear the search."
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((c) => (
            <CentreCard
              key={c.id}
              centre={c}
              onClick={() => {
                setOpenId(c.id);
                setActiveTab('details');
              }}
            />
          ))}
          <NewCentreCard onClick={() => setShowAdd(true)} />
        </div>
      )}

      <AddCentreModal open={showAdd} onClose={() => setShowAdd(false)} />
    </div>
  );
}
