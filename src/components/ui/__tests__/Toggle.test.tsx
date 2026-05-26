import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Toggle } from '../Toggle';

describe('Toggle', () => {
  it('reflects checked state on the switch role', () => {
    render(<Toggle checked label="On" onChange={() => {}} />);
    const sw = screen.getByRole('switch');
    expect(sw).toHaveAttribute('aria-checked', 'true');
  });

  it('toggles when clicked', () => {
    const onChange = vi.fn();
    render(<Toggle checked={false} label="Open" onChange={onChange} />);
    fireEvent.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it('does not call onChange when disabled', () => {
    const onChange = vi.fn();
    render(<Toggle checked={false} label="X" disabled onChange={onChange} />);
    fireEvent.click(screen.getByRole('switch'));
    expect(onChange).not.toHaveBeenCalled();
  });
});
