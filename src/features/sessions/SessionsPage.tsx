import { useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { useStore } from '@/store/store';
import { NewSessionCard, SessionCard } from './SessionCard';
import { SessionEditor } from './SessionEditor';
import type { Session } from '@/lib/types';

type EditorState =
  | { open: false }
  | { open: true; session: Session | null };

export function SessionsPage() {
  const { sessions } = useStore();
  const [editor, setEditor] = useState<EditorState>({ open: false });

  return (
    <div className="space-y-5">
      <PageHeader
        title="Sessions"
        subtitle="Sessions are used as resources across the platform"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {sessions.map((s) => (
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
          onClose={() => setEditor({ open: false })}
        />
      )}
    </div>
  );
}
