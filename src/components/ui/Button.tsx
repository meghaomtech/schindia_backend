import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'default' | 'primary' | 'purple' | 'danger' | 'ghost';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

const variantClass: Record<Variant, string> = {
  default: 'btn',
  primary: 'btn btn-primary',
  purple: 'btn btn-purple',
  danger: 'btn btn-danger',
  ghost: 'btn btn-ghost',
};

export function Button({
  variant = 'default',
  leftIcon,
  rightIcon,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button {...rest} className={`${variantClass[variant]} ${className}`}>
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}
