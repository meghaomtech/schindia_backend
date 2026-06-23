import { CalendarIcon, ClockIcon, UsersIcon } from '@/components/ui/icons';
import { initialsOf } from '@/lib/colors';
import type { Session } from '@/lib/types';

function durationLabel(s: Session): string {
  const h = s.durationHours;
  const m = s.durationMinutes;
  if (h > 0 && m > 0) return `${h}hr ${m}min`;
  if (h > 0) return `${h}hr`;
  return `${m}min`;
}

export function SessionCard({
  session,
  active,
  onClick,
}: {
  session: Session;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={`Edit session ${session.name}`}
      className={[
        'card p-4 text-left hover:shadow-md transition-shadow w-full',
        active ? 'border-2 border-info' : 'border border-border',
      ].join(' ')}
    >
      <div className="flex items-center gap-3">
        <span
          className="w-10 h-10 rounded-full inline-flex items-center justify-center font-semibold text-sm"
          style={{ background: session.colorBg, color: session.colorText }}
        >
          {initialsOf(session.name)}
        </span>
        <div className="font-semibold text-charcoal truncate">{session.name}</div>
      </div>
      <ul className="mt-3 space-y-1 text-xs text-text-muted">
        <li className="flex items-center gap-2">
          <UsersIcon width={14} height={14} className="shrink-0" />
          <span>Max {session.childLimit} children</span>
        </li>
        <li className="flex items-center gap-2">
          <CalendarIcon width={14} height={14} className="shrink-0" />
          <span>
            {session.ageFrom}–{session.ageTo} {session.ageUnit}
          </span>
        </li>
        <li className="flex items-center gap-2">
          <ClockIcon width={14} height={14} className="shrink-0" />
          <span>{durationLabel(session)}</span>
        </li>
      </ul>
    </button>
  );
}

export function NewSessionCard({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="card p-4 border-dashed border-2 hover:border-olive hover:bg-olive/5 transition-colors flex flex-col items-center justify-center min-h-[140px] text-text-muted hover:text-olive w-full"
    >
      <div className="text-3xl">+</div>
      <div className="text-sm font-medium mt-1">New session</div>
    </button>
  );
}
