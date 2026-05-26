import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { StoreProvider } from '@/store/store';
import { SessionEditor } from '../SessionEditor';

describe('SessionEditor', () => {
  it('shows defaults for a new session', () => {
    render(
      <StoreProvider>
        <SessionEditor session={null} onClose={() => {}} />
      </StoreProvider>
    );
    expect(screen.getByText('New session')).toBeInTheDocument();
    expect(screen.getByDisplayValue('12')).toBeInTheDocument(); // childLimit
  });

  it('flags a blank name on save', () => {
    render(
      <StoreProvider>
        <SessionEditor session={null} onClose={() => {}} />
      </StoreProvider>
    );
    fireEvent.click(screen.getByText('Create session'));
    expect(screen.getByText('Session name is required')).toBeInTheDocument();
  });
});
