import { useMemo, useState } from 'react';
import { useStore } from '@/store/store';
import { NewSessionCard, SessionCard } from './SessionCard';
import { SessionEditor } from './SessionEditor';
import type { Centre, Session } from '@/lib/types';

type EditorState =
  | { open: false }
  | { open: true; session: Session | null };

export function SessionsPage({ centre }: { centre: Centre }) {
  const { sessions } = useStore();
  const [editor, setEditor] = useState<EditorState>({ open: false });

  const centreSessions = useMemo(
    () => sessions.filter((s) => s.centreId === centre.id),
    [sessions, centre.id]
  );

  return (
    <div className="space-y-5">
      <div>
        <div className="text-base font-semibold text-charcoal">
          Sessions for {centre.name}
        </div>
        <div className="text-sm text-text-muted">
          Sessions are used as resources across this centre.
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {centreSessions.map((s) => (
          <SessionCard
            key={s.id}
            session={s}
            active={editor.open && editor.session?.id === s.id}
            onClick={() => setEditor({ open: true, session: s })}
          />
        ))}
        <NewSessionCard onClick={() => setEditor({ open: true, session: null })} />
      </div>

      {editor.open && (
        <SessionEditor
          session={editor.session}
          centreId={centre.id}
          onClose={() => setEditor({ open: false })}
        />
      )}
    </div>
  );
}
