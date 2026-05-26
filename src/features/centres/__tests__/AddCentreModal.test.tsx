import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { StoreProvider } from '@/store/store';
import { AddCentreModal } from '../AddCentreModal';

function renderOpen() {
  return render(
    <StoreProvider>
      <AddCentreModal open={true} onClose={() => {}} />
    </StoreProvider>
  );
}

describe('AddCentreModal', () => {
  it('renders step 1 fields and an auto-generated system ID', () => {
    renderOpen();
    expect(screen.getByText(/System ID:/i)).toBeInTheDocument();
    expect(screen.getByText('Centre name')).toBeInTheDocument();
    expect(screen.getByText('Continue →')).toBeInTheDocument();
  });

  it('shows validation errors when continuing with empty fields', () => {
    renderOpen();
    fireEvent.click(screen.getByText('Continue →'));
    expect(screen.getByText('Centre name is required')).toBeInTheDocument();
    expect(screen.getByText('Street address is required')).toBeInTheDocument();
  });
});
