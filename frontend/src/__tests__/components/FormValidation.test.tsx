/**
 * @vitest-environment jsdom
 */

import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock ReviewConfirm component for testing form validation
const MockScheduleForm = ({ onSubmit }: { onSubmit: (data: any) => void }) => {
  const [date, setDate] = React.useState('');
  const [time, setTime] = React.useState('');
  const [error, setError] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!date || !time) {
      setError('Both date and time are required');
      return;
    }

    const selectedDateTime = new Date(`${date}T${time}:00`);
    const now = new Date();

    if (selectedDateTime < now) {
      setError('Scheduled time must be in the future');
      return;
    }

    setError('');
    onSubmit({ date, time });
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div>
        <label htmlFor="date">Date</label>
        <input
          id="date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          min={new Date().toISOString().split('T')[0]}
        />
      </div>
      <div>
        <label htmlFor="time">Time</label>
        <input
          id="time"
          type="time"
          value={time}
          onChange={(e) => setTime(e.target.value)}
        />
      </div>
      {error && <div role="alert">{error}</div>}
      <button type="submit">Schedule</button>
    </form>
  );
};

import React from 'react';

describe('Form Validation', () => {
  it('validates required fields', () => {
    const mockOnSubmit = vi.fn();

    render(<MockScheduleForm onSubmit={mockOnSubmit} />);

    const submitButton = screen.getByText('Schedule');
    fireEvent.click(submitButton);

    expect(screen.getByRole('alert')).toHaveTextContent('Both date and time are required');
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('validates minimum date (prevents past dates)', () => {
    const mockOnSubmit = vi.fn();

    render(<MockScheduleForm onSubmit={mockOnSubmit} />);

    const dateInput = screen.getByLabelText('Date') as HTMLInputElement;

    // Check that min attribute is set to today
    const today = new Date().toISOString().split('T')[0];
    expect(dateInput.getAttribute('min')).toBe(today);
  });

  it('validates future date/time', () => {
    const mockOnSubmit = vi.fn();

    render(<MockScheduleForm onSubmit={mockOnSubmit} />);

    const dateInput = screen.getByLabelText('Date');
    const timeInput = screen.getByLabelText('Time');
    const submitButton = screen.getByText('Schedule');

    // Try to submit a past date
    fireEvent.change(dateInput, { target: { value: '2020-01-01' } });
    fireEvent.change(timeInput, { target: { value: '12:00' } });
    fireEvent.click(submitButton);

    expect(screen.getByRole('alert')).toHaveTextContent('Scheduled time must be in the future');
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('submits valid data', () => {
    const mockOnSubmit = vi.fn();

    render(<MockScheduleForm onSubmit={mockOnSubmit} />);

    const dateInput = screen.getByLabelText('Date');
    const timeInput = screen.getByLabelText('Time');
    const submitButton = screen.getByText('Schedule');

    // Submit a future date
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];

    fireEvent.change(dateInput, { target: { value: tomorrowStr } });
    fireEvent.change(timeInput, { target: { value: '14:00' } });
    fireEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith({
      date: tomorrowStr,
      time: '14:00'
    });
  });
});

// Phone number validation tests
describe('Phone Number Validation', () => {
  const MockPhoneInput = ({ onChange }: { onChange: (value: string) => void }) => {
    const [phone, setPhone] = React.useState('');
    const [error, setError] = React.useState('');

    const validatePhone = (value: string) => {
      const digits = value.replace(/\D/g, '');

      if (digits.length === 0) {
        setError('');
        return true;
      }

      if (digits.length === 10 || digits.length === 11) {
        setError('');
        return true;
      }

      setError('Please enter a valid phone number (10 digits)');
      return false;
    };

    const handleChange = (value: string) => {
      // Format phone number
      const digits = value.replace(/\D/g, '');
      let formatted = digits;

      if (digits.length > 0) {
        if (digits.length <= 3) {
          formatted = `(${digits}`;
        } else if (digits.length <= 6) {
          formatted = `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
        } else {
          formatted = `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6, 10)}`;
        }
      }

      setPhone(formatted);
      validatePhone(formatted);
      onChange(formatted);
    };

    return (
      <div>
        <label htmlFor="phone">Phone Number</label>
        <input
          id="phone"
          type="tel"
          value={phone}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="(555) 123-4567"
          maxLength={14}
        />
        {error && <div role="alert">{error}</div>}
      </div>
    );
  };

  it('formats phone number as user types', () => {
    const mockOnChange = vi.fn();

    render(<MockPhoneInput onChange={mockOnChange} />);

    const input = screen.getByLabelText('Phone Number') as HTMLInputElement;

    fireEvent.change(input, { target: { value: '5551234567' } });

    expect(input.value).toBe('(555) 123-4567');
  });

  it('validates phone number length', () => {
    const mockOnChange = vi.fn();

    render(<MockPhoneInput onChange={mockOnChange} />);

    const input = screen.getByLabelText('Phone Number');

    // Invalid: too few digits
    fireEvent.change(input, { target: { value: '123' } });
    expect(screen.getByRole('alert')).toHaveTextContent('Please enter a valid phone number (10 digits)');

    // Valid: 10 digits
    fireEvent.change(input, { target: { value: '5551234567' } });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('accepts empty phone number', () => {
    const mockOnChange = vi.fn();

    render(<MockPhoneInput onChange={mockOnChange} />);

    const input = screen.getByLabelText('Phone Number');

    fireEvent.change(input, { target: { value: '' } });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
