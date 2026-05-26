export interface AvatarProps {
  initials: string;
  size?: 'sm' | 'md' | 'lg';
  bg?: string;
  text?: string;
}

const sizeClass = {
  sm: 'w-7 h-7 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-14 h-14 text-lg',
} as const;

export function Avatar({ initials, size = 'md', bg, text }: AvatarProps) {
  return (
    <span
      className={[
        'inline-flex items-center justify-center rounded-full font-semibold',
        sizeClass[size],
      ].join(' ')}
      style={{
        background: bg ?? 'var(--avatar-bg, #E7DDD0)',
        color: text ?? 'var(--avatar-text, #2F2F2B)',
      }}
    >
      {initials}
    </span>
  );
}
