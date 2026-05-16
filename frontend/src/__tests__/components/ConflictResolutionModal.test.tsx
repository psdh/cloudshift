/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ConflictResolutionModal from '@/components/transfers/ConflictResolutionModal';

// Mock fetch
global.fetch = vi.fn();

// Typed accessor for the mocked fetch. Resolved values are partial Response
// objects (only the fields the component uses), so they are cast accordingly.
const mockFetch = () =>
  vi.mocked(global.fetch) as unknown as {
    mockResolvedValueOnce: (value: { ok: boolean; json: () => Promise<unknown> }) => void;
  };

describe('ConflictResolutionModal Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem('access_token', 'fake-token');
  });

  it('does not render when isOpen is false', () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    const { container } = render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={false}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('renders modal when isOpen is true', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    // Mock conflicts API response
    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'document.pdf',
            dest_path: 'document.pdf',
            source_size: 1024000,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    expect(screen.getByText('Resolve File Conflicts')).toBeInTheDocument();
  });

  it('fetches and displays conflict details', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'test-file.pdf',
            dest_path: 'test-file.pdf',
            source_size: 2048000,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/test-file\.pdf/)).toBeInTheDocument();
    });
  });

  it('displays resolution options', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'file.pdf',
            dest_path: 'file.pdf',
            source_size: 1024,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Skip This File')).toBeInTheDocument();
      expect(screen.getByText('Rename & Keep Both')).toBeInTheDocument();
      expect(screen.getByText('Overwrite Destination File')).toBeInTheDocument();
    });
  });

  it('shows rename preview', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'document.pdf',
            dest_path: 'document.pdf',
            source_size: 1024,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Rename Preview:')).toBeInTheDocument();
    });

    // Should show a timestamped version of the filename
    const preview = screen.getByText(/document_.*\.pdf/);
    expect(preview).toBeInTheDocument();
  });

  it('resolves single conflict when resolution button clicked', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    // Mock conflicts fetch
    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'file.pdf',
            dest_path: 'file.pdf',
            source_size: 1024,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Skip This File')).toBeInTheDocument();
    });

    // Mock resolve conflict API call
    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    const skipButton = screen.getByText('Skip This File');
    fireEvent.click(skipButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/conflicts/1/resolve'),
        expect.objectContaining({
          method: 'POST'
        })
      );
    });
  });

  it('shows apply to all checkbox when multiple conflicts exist', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'file1.pdf',
            dest_path: 'file1.pdf',
            source_size: 1024,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          },
          {
            id: 2,
            item_id: 2,
            source_path: 'file2.pdf',
            dest_path: 'file2.pdf',
            source_size: 2048,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Apply this choice to all remaining/)).toBeInTheDocument();
    });
  });

  it('calls onResolved and onClose when all conflicts are resolved', async () => {
    const mockOnClose = vi.fn();
    const mockOnResolved = vi.fn();

    // Mock conflicts fetch with only one conflict
    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        conflicts: [
          {
            id: 1,
            item_id: 1,
            source_path: 'file.pdf',
            dest_path: 'file.pdf',
            source_size: 1024,
            dest_file_exists: true,
            resolution: null,
            resolved_at: null
          }
        ]
      })
    });

    render(
      <ConflictResolutionModal
        jobId={1}
        isOpen={true}
        onClose={mockOnClose}
        onResolved={mockOnResolved}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Skip This File')).toBeInTheDocument();
    });

    // Mock resolve conflict - this should close the modal
    mockFetch().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });

    const skipButton = screen.getByText('Skip This File');
    fireEvent.click(skipButton);

    await waitFor(() => {
      expect(mockOnResolved).toHaveBeenCalled();
      expect(mockOnClose).toHaveBeenCalled();
    });
  });
});
