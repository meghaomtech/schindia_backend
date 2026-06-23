import { CentreChildrenTab } from './CentreChildrenTab';
import { useCentreOutlet } from './useCentreOutlet';

export function CentreChildrenRoute() {
  const { centre } = useCentreOutlet();
  return (
    <div className="card p-5">
      <CentreChildrenTab centre={centre} />
    </div>
  );
}
