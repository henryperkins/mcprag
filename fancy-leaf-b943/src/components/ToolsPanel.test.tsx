import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolsPanel } from './ToolsPanel';
import { claudeService } from '../services/claude';

// Mock the claude service
vi.mock('../services/claude', () => ({
  claudeService: {
    on: vi.fn(),
    emit: vi.fn()
  }
}));

describe('ToolsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the tools panel with header', () => {
    // Setup mock
    const mockUnsubscribe = vi.fn();
    vi.mocked(claudeService.on).mockReturnValue(mockUnsubscribe);

    // Render component
    const { container } = render(<ToolsPanel />);

    // Check header is rendered
    expect(screen.getByText('Available Tools')).toBeInTheDocument();
    expect(container.querySelector('.tools-panel')).toBeInTheDocument();
  });

  it('displays filter tabs for tool categories', () => {
    const mockUnsubscribe = vi.fn();
    vi.mocked(claudeService.on).mockReturnValue(mockUnsubscribe);

    render(<ToolsPanel />);

    // Check filter tabs
    expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /file/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /system/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /web/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /mcp/i })).toBeInTheDocument();
  });

  it('toggles expanded state when clicking expand/collapse button', () => {
    const mockUnsubscribe = vi.fn();
    vi.mocked(claudeService.on).mockReturnValue(mockUnsubscribe);

    render(<ToolsPanel />);

    const toggleButton = screen.getByText('Expand');
    expect(toggleButton).toBeInTheDocument();

    // Click to expand
    fireEvent.click(toggleButton);
    expect(screen.getByText('Collapse')).toBeInTheDocument();

    // Click to collapse
    fireEvent.click(screen.getByText('Collapse'));
    expect(screen.getByText('Expand')).toBeInTheDocument();
  });

  it('subscribes to tools updates on mount', () => {
    const mockUnsubscribe = vi.fn();
    vi.mocked(claudeService.on).mockReturnValue(mockUnsubscribe);

    render(<ToolsPanel />);

    // Verify subscription
    expect(claudeService.on).toHaveBeenCalledWith('tools-update', expect.any(Function));
    expect(claudeService.emit).toHaveBeenCalledWith('request-tools-info', {});
  });

  it('handles tools update event with categorization', () => {
    const mockUnsubscribe = vi.fn();
    let toolsUpdateCallback: any;

    vi.mocked(claudeService.on).mockImplementation((event, callback) => {
      if (event === 'tools-update') {
        toolsUpdateCallback = callback;
      }
      return mockUnsubscribe;
    });

    const { rerender } = render(<ToolsPanel />);

    // Simulate tools update
    const mockToolsData = {
      tools: ['Read', 'Write', 'Edit', 'Grep', 'Bash', 'mcp__test'],
      mcpServers: [
        {
          name: 'test-server',
          status: 'connected',
          tools: ['tool1', 'tool2']
        }
      ]
    };

    // Trigger the callback
    toolsUpdateCallback(mockToolsData);

    // Force a re-render to see the updates
    rerender(<ToolsPanel />);

    // Expand to see tools
    fireEvent.click(screen.getByText('Expand'));

    // Check that tools are categorized properly
    expect(screen.getByText('file Tools')).toBeInTheDocument();
    expect(screen.getByText('edit Tools')).toBeInTheDocument();
    expect(screen.getByText('system Tools')).toBeInTheDocument();
  });

  it('displays MCP servers when available', () => {
    const mockUnsubscribe = vi.fn();
    let toolsUpdateCallback: any;

    vi.mocked(claudeService.on).mockImplementation((event, callback) => {
      if (event === 'tools-update') {
        toolsUpdateCallback = callback;
      }
      return mockUnsubscribe;
    });

    render(<ToolsPanel />);

    // Simulate tools update with MCP servers
    const mockToolsData = {
      tools: [],
      mcpServers: [
        {
          name: 'test-server',
          status: 'connected',
          tools: ['tool1', 'tool2']
        }
      ]
    };

    toolsUpdateCallback(mockToolsData);

    // Check MCP servers section
    expect(screen.getByText('MCP Servers')).toBeInTheDocument();
    expect(screen.getByText('test-server')).toBeInTheDocument();
    expect(screen.getByText('2 tools')).toBeInTheDocument();
  });

  it('filters tools when clicking category tabs', () => {
    const mockUnsubscribe = vi.fn();
    let toolsUpdateCallback: any;

    vi.mocked(claudeService.on).mockImplementation((event, callback) => {
      if (event === 'tools-update') {
        toolsUpdateCallback = callback;
      }
      return mockUnsubscribe;
    });

    render(<ToolsPanel />);

    // Add tools
    toolsUpdateCallback({
      tools: ['Read', 'Write', 'Edit', 'Grep', 'Bash'],
      mcpServers: []
    });

    // Expand panel
    fireEvent.click(screen.getByText('Expand'));

    // Click file category filter
    fireEvent.click(screen.getByRole('button', { name: /📁 file/i }));

    // Should show only file tools
    expect(screen.getByText('file Tools')).toBeInTheDocument();
    expect(screen.queryByText('system Tools')).not.toBeInTheDocument();
  });

  it('unsubscribes from events on unmount', () => {
    const mockUnsubscribe = vi.fn();
    vi.mocked(claudeService.on).mockReturnValue(mockUnsubscribe);

    const { unmount } = render(<ToolsPanel />);

    expect(mockUnsubscribe).not.toHaveBeenCalled();

    unmount();

    expect(mockUnsubscribe).toHaveBeenCalled();
  });
});