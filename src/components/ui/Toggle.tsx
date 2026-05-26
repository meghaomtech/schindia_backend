export interface ToggleProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  label?: string;
  disabled?: boolean;
  ariaLabel?: string;
}

export function Toggle({ checked, onChange, label, disabled, ariaLabel }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel ?? label}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={[
        'inline-flex items-center gap-2 select-none',
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
      ].join(' ')}
    >
      <span
        className={[
          'w-9 h-5 rounded-full p-0.5 transition-colors',
          checked ? 'bg-olive' : 'bg-sand',
        ].join(' ')}
      >
        <span
          className={[
            'block w-4 h-4 rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0',
          ].join(' ')}
        />
      </span>
      {label && <span className="text-sm">{label}</span>}
    </button>
  );
}
