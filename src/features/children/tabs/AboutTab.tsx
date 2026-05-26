import { useStore } from '@/store/store';
import { Badge } from '@/components/ui/Badge';
import { ageString, formatLongDate, fromISODate } from '@/lib/dates';
import { progressForWeek } from '@/lib/recurrence';
import type { Child } from '@/lib/types';

export function AboutTab({ child }: { child: Child }) {
  const { centres, sessions, slots, children: kids } = useStore();
  const centre = centres.find((c) => c.id === child.centreId);
  const session = sessions.find((s) => s.id === child.sessionId);

  const childSlots = slots.filter((s) => s.childIds.includes(child.id));
  let progressLabel = '—';
  if (childSlots.length > 0) {
    const main = childSlots[0]!;
    const p = progressForWeek(main, new Date());
    progressLabel = `M${p.month} W${p.week}`;
  }

  const sibling = child.siblingId ? kids.find((c) => c.id === child.siblingId) : null;

  return (
    <div className="space-y-5">
      <Section title="Personal details">
        <Row label="Full name">
          {child.firstName} {child.middleName ? `${child.middleName} ` : ''}
          {child.lastName}
        </Row>
        <Row label="Date of birth">
          {formatLongDate(fromISODate(child.dateOfBirth))}
        </Row>
        <Row label="Gender">{child.gender}</Row>
        <Row label="Age">{ageString(child.dateOfBirth)}</Row>
        <Row label="Start date">
          {formatLongDate(fromISODate(child.startDate))}
        </Row>
        <Row label="Child ID">
          <span className="font-mono">{child.systemId}</span>
        </Row>
      </Section>

      <hr className="border-border" />

      <Section title="Centre &amp; session">
        <Row label="Centre">{centre?.name ?? '—'}</Row>
        <Row label="Session">{session?.name ?? '—'}</Row>
        <Row label="Age range">
          {session
            ? `${session.ageFrom}–${session.ageTo} ${session.ageUnit}`
            : '—'}
        </Row>
        <Row label="Course progress">{progressLabel}</Row>
      </Section>

      {sibling && (
        <>
          <hr className="border-border" />
          <Section title="Sibling connection">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold">
                  {sibling.firstName} {sibling.lastName}
                </div>
                <div className="text-xs text-text-muted font-mono">
                  {sibling.systemId}
                </div>
              </div>
              <Badge tone="purple">Sibling</Badge>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-sm font-semibold mb-3">{title}</div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3">{children}</dl>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-text-muted">{label}</dt>
      <dd className="text-sm mt-0.5">{children}</dd>
    </div>
  );
}
