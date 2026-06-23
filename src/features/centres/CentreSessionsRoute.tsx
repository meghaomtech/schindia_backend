import { SessionsPage } from '@/features/sessions/SessionsPage';
import { useCentreOutlet } from './useCentreOutlet';

export function CentreSessionsRoute() {
  const { centre } = useCentreOutlet();
  return (
    <div className="card p-5">
      <SessionsPage centre={centre} />
    </div>
  );
}
