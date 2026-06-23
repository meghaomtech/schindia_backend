import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { CloseIcon } from './icons';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  /** Whether to render a footer slot inside the modal */
  footer?: ReactNode;
  children: ReactNode;
  size?: 'sm' | 'md' | 'lg';
  /** Optional accent strip at the top, e.g. progress bar */
  topStrip?: ReactNode;
}

const sizeClass: Record<NonNullable<ModalProps['size']>, string> = {
  sm: 'max-w-md',
  md: 'max-w-2xl',
  lg: 'max-w-4xl',
};

export function Modal({
  open,
  onClose,
  title,
  footer,
  children,
  size = 'md',
  topStrip,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-charcoal/40 backdrop-blur-sm p-6"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className={`card w-full ${sizeClass[size]} my-10 overflow-hidden`}
        onClick={(e) => e.stopPropagation()}
      >
        {topStrip}
        {title !== undefined && (
          <header className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="font-semibold">{title}</div>
            <button
              className="btn btn-ghost"
              onClick={onClose}
              aria-label="Close"
              type="button"
            >
              <CloseIcon />
            </button>
          </header>
        )}
        <div className="p-5">{children}</div>
        {footer && (
          <footer className="px-5 py-4 border-t border-border bg-bg-elev flex items-center gap-2">
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}
