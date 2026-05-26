import type { ReactNode } from 'react';

export interface TabItem<K extends string> {
  key: K;
  label: ReactNode;
}

export interface TabsProps<K extends string> {
  items: TabItem<K>[];
  active: K;
  onChange: (k: K) => void;
  /** When true, active tab uses an underline (purple/gold) instead of pill style */
  underline?: boolean;
  variant?: 'olive' | 'gold' | 'purple';
}

export function Tabs<K extends string>({
  items,
  active,
  onChange,
  underline = true,
  variant = 'olive',
}: TabsProps<K>) {
  const accent =
    variant === 'gold'
      ? 'text-gold border-gold'
      : variant === 'purple'
      ? 'text-accent-purple border-accent-purple'
      : 'text-olive border-olive';

  return (
    <div role="tablist" className="flex items-center gap-1 border-b border-border overflow-x-auto">
      {items.map((it) => {
        const isActive = it.key === active;
        return (
          <button
            key={it.key}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(it.key)}
            className={[
              'px-4 py-2 text-sm font-medium whitespace-nowrap',
              underline ? 'border-b-2 -mb-px' : 'rounded-md',
              isActive
                ? underline
                  ? `${accent}`
                  : `${accent} bg-bg-elev`
                : 'border-transparent text-text-muted hover:text-text',
            ].join(' ')}
            type="button"
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}
