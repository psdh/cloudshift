/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterConfiguration from '@/components/transfers/FilterConfiguration';

describe('FilterConfiguration Component', () => {
  it('renders filter configuration heading', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    expect(screen.getByText('Filter Configuration')).toBeInTheDocument();
    expect(screen.getByText(/Optionally filter which files to transfer/i)).toBeInTheDocument();
  });

  it('displays file type categories', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Spreadsheets')).toBeInTheDocument();
    expect(screen.getByText('Images')).toBeInTheDocument();
    expect(screen.getByText('Videos')).toBeInTheDocument();
  });

  it('calls onFiltersChange when file type is selected', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    // Find and click Documents checkbox
    const documentsCheckbox = screen.getByRole('checkbox', { name: /Documents/ });
    fireEvent.click(documentsCheckbox);

    // Should have been called with selected file types
    expect(mockOnFiltersChange).toHaveBeenCalled();
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    expect(lastCall.fileTypes).toContain('.pdf');
    expect(lastCall.fileTypes).toContain('.doc');
  });

  it('shows date range inputs', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    expect(screen.getByText('Date Range (Modified Date)')).toBeInTheDocument();
    expect(screen.getByLabelText('From')).toBeInTheDocument();
    expect(screen.getByLabelText('To')).toBeInTheDocument();
  });

  it('validates date range - shows error when start date is after end date', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    const startDateInput = screen.getByLabelText('From') as HTMLInputElement;
    const endDateInput = screen.getByLabelText('To') as HTMLInputElement;

    fireEvent.change(startDateInput, { target: { value: '2024-12-31' } });
    fireEvent.change(endDateInput, { target: { value: '2024-01-01' } });

    expect(screen.getByText('Start date must be before end date')).toBeInTheDocument();
  });

  it('shows advanced folder filters when button clicked', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    const advancedButton = screen.getByText('Advanced Folder Filters');
    fireEvent.click(advancedButton);

    expect(screen.getByText('Include Only These Folders')).toBeInTheDocument();
    expect(screen.getByText('Exclude These Folders')).toBeInTheDocument();
  });

  it('shows active filters summary when filters are applied', () => {
    const mockOnFiltersChange = vi.fn();

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
      />
    );

    // Select Documents
    const documentsCheckbox = screen.getByRole('checkbox', { name: /Documents/ });
    fireEvent.click(documentsCheckbox);

    // Should show active filters summary
    expect(screen.getByText('Active Filters:')).toBeInTheDocument();
  });

  it('clears all filters when Clear All Filters button clicked', () => {
    const mockOnFiltersChange = vi.fn();

    const initialFilters = {
      fileTypes: ['.pdf'],
      dateRange: { startDate: '2024-01-01', endDate: '2024-12-31' },
      folderInclude: ['Work'],
      folderExclude: []
    };

    render(
      <FilterConfiguration
        onFiltersChange={mockOnFiltersChange}
        initialFilters={initialFilters}
      />
    );

    const clearButton = screen.getByText('Clear All Filters');
    fireEvent.click(clearButton);

    // Should have called with empty filters
    const lastCall = mockOnFiltersChange.mock.calls[mockOnFiltersChange.mock.calls.length - 1][0];
    expect(lastCall.fileTypes).toHaveLength(0);
    expect(lastCall.dateRange.startDate).toBe('');
    expect(lastCall.folderInclude).toHaveLength(0);
  });
});
