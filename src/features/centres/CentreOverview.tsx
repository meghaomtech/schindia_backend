import { useState } from 'react';
import { Tabs } from '@/components/ui/Tabs';
import { CentreDetailsTab } from './CentreDetailsTab';
import { ClosureDatesTab } from './ClosureDatesTab';
import { OpeningTimesTab } from './OpeningTimesTab';
import { useCentreOutlet } from './useCentreOutlet';

type OverviewTab = 'details' | 'closure' | 'opening';

const TAB_ITEMS: { key: OverviewTab; label: string }[] = [
  { key: 'details', label: 'Centre details' },
  { key: 'closure', label: 'Closure dates' },
  { key: 'opening', label: 'Opening times' },
];

export function CentreOverview() {
  const { centre } = useCentreOutlet();
  const [activeTab, setActiveTab] = useState<OverviewTab>('details');

  return (
    <div className="card p-5 space-y-5">
      <Tabs<OverviewTab>
        items={TAB_ITEMS}
        active={activeTab}
        onChange={setActiveTab}
      />
      <div className="pt-2">
        {activeTab === 'details' && <CentreDetailsTab centre={centre} />}
        {activeTab === 'closure' && <ClosureDatesTab centre={centre} />}
        {activeTab === 'opening' && <OpeningTimesTab centre={centre} />}
      </div>
    </div>
  );
}
