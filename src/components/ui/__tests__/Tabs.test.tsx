import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Tabs } from '../Tabs';

describe('Tabs', () => {
  const items = [
    { key: 'a' as const, label: 'Alpha' },
    { key: 'b' as const, label: 'Beta' },
  ];

  it('marks the active tab via aria-selected', () => {
    render(<Tabs items={items} active="b" onChange={() => {}} />);
    expect(screen.getByRole('tab', { name: 'Beta' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByRole('tab', { name: 'Alpha' })).toHaveAttribute(
      'aria-selected',
      'false'
    );
  });

  it('calls onChange when a different tab is clicked', () => {
    const onChange = vi.fn();
    render(<Tabs items={items} active="a" onChange={onChange} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Beta' }));
    expect(onChange).toHaveBeenCalledWith('b');
  });
});
