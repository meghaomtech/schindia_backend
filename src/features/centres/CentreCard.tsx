import { Badge } from '@/components/ui/Badge';
import { initialsOf, paletteFor } from '@/lib/colors';
import type { Centre } from '@/lib/types';

export function CentreCard({
  centre,
  onClick,
}: {
  centre: Centre;
  onClick: () => void;
}) {
  const palette = paletteFor(centre.name);
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Open ${centre.name}`}
      className="card p-4 text-left hover:shadow-md transition-shadow w-full flex flex-col gap-3"
    >
      <div className="flex items-center gap-3">
        <span
          className="w-12 h-12 rounded-full inline-flex items-center justify-center font-bold"
          style={{ background: palette.bg, color: palette.text }}
        >
          {initialsOf(centre.name)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold truncate">{centre.name}</div>
          <div className="text-xs text-text-dim font-mono">{centre.systemId}</div>
        </div>
      </div>

      <div className="text-sm text-text-muted line-clamp-2">
        📍 {centre.streetAddress}, {centre.city}, {centre.postcode}
      </div>

      <div className="text-sm text-text-muted">
        👤 {centre.managerName}
      </div>

      <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-border mt-1">
        <Badge tone="beige">{centre.rooms.length} rooms</Badge>
        <Badge tone="olive">{centre.closureDates.length} closures</Badge>
      </div>
    </button>
  );
}

export function NewCentreCard({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="card p-4 border-dashed border-2 hover:border-olive hover:bg-olive/5 transition-colors flex flex-col items-center justify-center min-h-[180px] text-text-muted hover:text-olive w-full"
    >
      <div className="text-3xl">+</div>
      <div className="text-sm font-medium mt-1">Add centre</div>
    </button>
  );
}
