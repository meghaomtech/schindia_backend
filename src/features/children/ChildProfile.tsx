import { useState } from 'react';
import { Tabs } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { useStore } from '@/store/store';
import { ageString, formatLongDate, fromISODate } from '@/lib/dates';
import { initialsOf } from '@/lib/colors';
import { ActivityTab } from './tabs/ActivityTab';
import { AboutTab } from './tabs/AboutTab';
import { FamilyTab } from './tabs/FamilyTab';
import { ChildBookingsTab } from './ChildBookingsTab';
import { JourneyTab } from './tabs/JourneyTab';
import { NotesTab } from './tabs/NotesTab';
import { InvoicesTab } from './tabs/InvoicesTab';
import type { Child } from '@/lib/types';

type ProfileTab =
  | 'activity'
  | 'about'
  | 'family'
  | 'bookings'
  | 'journey'
  | 'notes'
  | 'invoices';

const TAB_ITEMS: { key: ProfileTab; label: string }[] = [
  { key: 'activity', label: 'Activity' },
  { key: 'about', label: 'About' },
  { key: 'family', label: 'Family' },
  { key: 'bookings', label: 'Bookings' },
  { key: 'journey', label: 'Journey' },
  { key: 'notes', label: 'Notes' },
  { key: 'invoices', label: 'Invoices' },
];

export function ChildProfile({ child }: { child: Child }) {
  const [tab, setTab] = useState<ProfileTab>('activity');
  const { centres, sessions } = useStore();

  const centre = centres.find((c) => c.id === child.centreId);
  const session = sessions.find((s) => s.id === child.sessionId);

  return (
    <div>
      <div className="card overflow-hidden">
        <div className="p-5 flex items-start gap-4">
          <span
            className="w-16 h-16 rounded-full inline-flex items-center justify-center font-bold text-xl bg-accent-purple-soft text-accent-purple shrink-0"
            aria-hidden="true"
          >
            {initialsOf(`${child.firstName} ${child.lastName}`)}
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-xl font-semibold leading-tight">
              {child.firstName} {child.middleName ? `${child.middleName} ` : ''}
              {child.lastName}
            </div>
            <div className="text-sm text-text-muted mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>
                DOB {formatLongDate(fromISODate(child.dateOfBirth))} ·{' '}
                {ageString(child.dateOfBirth)}
              </span>
              <span>·</span>
              <span>{centre?.name ?? '—'}</span>
              <span>·</span>
              <span>{child.gender}</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <Badge tone="green">● Active</Badge>
            {session && <Badge tone="purple">{session.name}</Badge>}
          </div>
        </div>

        <Tabs<ProfileTab>
          items={TAB_ITEMS}
          active={tab}
          onChange={setTab}
          variant="purple"
        />
      </div>

      <div className="bg-bg-elev rounded-b-xl border border-border border-t-0 p-5 -mt-px">
        {tab === 'activity' && <ActivityTab child={child} />}
        {tab === 'about' && <AboutTab child={child} />}
        {tab === 'family' && <FamilyTab child={child} />}
        {tab === 'bookings' && <ChildBookingsTab child={child} />}
        {tab === 'journey' && <JourneyTab child={child} />}
        {tab === 'notes' && <NotesTab child={child} />}
        {tab === 'invoices' && <InvoicesTab child={child} />}
      </div>
    </div>
  );
}
