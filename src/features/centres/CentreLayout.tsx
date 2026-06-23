import { Navigate, Outlet, useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useStore } from '@/store/store';
import { initialsOf, paletteFor } from '@/lib/colors';

export function CentreLayout() {
  const { centreId } = useParams<{ centreId: string }>();
  const { centres } = useStore();
  const navigate = useNavigate();
  const centre = centres.find((c) => c.id === centreId);

  if (!centre) {
    return <Navigate to="/admin/centres" replace />;
  }

  const palette = paletteFor(centre.name);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Button onClick={() => navigate('/admin/centres')} aria-label="Back to centres">
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
              {initialsOf(centre.name)}
            </span>
            <div>
              <div className="text-xl font-semibold">{centre.name}</div>
              <div className="text-sm text-text-muted">
                {centre.streetAddress}, {centre.city}, {centre.postcode}
              </div>
              <div className="text-xs text-text-dim font-mono mt-0.5">
                {centre.systemId}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="beige">{centre.rooms.length} rooms</Badge>
            <Badge tone="olive">{centre.closureDates.length} closure days</Badge>
          </div>
        </div>
      </div>

      <Outlet context={{ centre }} />
    </div>
  );
}
