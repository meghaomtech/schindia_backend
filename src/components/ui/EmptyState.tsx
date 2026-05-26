import type { ReactNode } from 'react';

export function EmptyState({
  title,
  description,
  action,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center justify-center text-center p-10 border-dashed">
      <div className="font-medium text-charcoal">{title}</div>
      {description && <div className="text-sm text-text-muted mt-1">{description}</div>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
