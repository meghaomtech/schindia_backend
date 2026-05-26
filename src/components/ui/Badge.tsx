import type { ReactNode } from 'react';

type Tone =
  | 'default'
  | 'olive'
  | 'gold'
  | 'danger'
  | 'sage'
  | 'beige'
  | 'purple'
  | 'blue'
  | 'coral'
  | 'green';

export function Badge({
  tone = 'default',
  children,
  className = '',
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  const toneClass: Record<Tone, string> = {
    default: 'badge',
    olive: 'badge badge-olive',
    gold: 'badge badge-gold',
    danger: 'badge badge-danger',
    sage: 'badge border-sage/40 bg-sage/15 text-olive',
    beige: 'badge border-beige bg-beige text-charcoal',
    purple: 'badge badge-purple',
    blue: 'badge badge-blue',
    coral: 'badge badge-coral',
    green: 'badge badge-green',
  };
  return <span className={`${toneClass[tone]} ${className}`}>{children}</span>;
}
