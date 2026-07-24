import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InvoiceForm } from '../InvoiceForm';

const mockData = {
  centerCode: '',
  centerLocation: '',
  fullAddress: '',
  centerEmail: '',
  centerPhone: '',
  gstNumber: '',
  website: '',
  bankName: '',
  accountNumber: '',
  ifscCode: '',
  upiId: '',
  studentName: '',
  parentName: '',
  city: '',
  contact: '',
  email: '',
  invoiceNumber: '',
  invoiceDate: '',
  dueDate: '',
  gstPercent: 18,
  debitBroughtForward: 0,
  registrationFee: 0,
  sessionFeeStart: '',
  sessionFeeEnd: '',
  sessionFeeAmount: 0,
  extraItems: [],
  deductions: [],
};

describe('InvoiceForm', () => {
  it('renders Preview Invoice button', () => {
    render(
      <InvoiceForm
        data={mockData}
        onChange={vi.fn()}
        onGenerate={vi.fn()}
      />
    );

    expect(
      screen.getByRole('button', { name: /Preview Invoice/i })
    ).toBeInTheDocument();
  });

it('allows entering student name', () => {
  const onChange = vi.fn();

  render(
    <InvoiceForm
      data={mockData}
      onChange={onChange}
      onGenerate={vi.fn()}
    />
  );

  const studentNameInput = screen.getByPlaceholderText('Testing 1');

  fireEvent.change(studentNameInput, {
    target: { value: 'Rahul Sharma' },
  });
    expect(onChange).toHaveBeenCalled();
   });
});