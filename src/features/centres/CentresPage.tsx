import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { useStore } from '@/store/store';
import { AddCentreModal } from './AddCentreModal';
import { CentreCard, NewCentreCard } from './CentreCard';

export function CentresPage() {
  const { centres } = useStore();
  const navigate = useNavigate();
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
              onClick={() => navigate(`/admin/centres/${c.id}`)}
            />
          ))}
          <NewCentreCard onClick={() => setShowAdd(true)} />
        </div>
      )}

      <AddCentreModal open={showAdd} onClose={() => setShowAdd(false)} />
    </div>
  );
}
