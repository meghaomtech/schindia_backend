import { SchedulePage } from '@/features/schedule/SchedulePage';
import { useCentreOutlet } from './useCentreOutlet';

export function CentreTimetableRoute() {
  const { centre } = useCentreOutlet();
  return (
    <div className="card p-5">
      <SchedulePage centre={centre} />
    </div>
  );
}
