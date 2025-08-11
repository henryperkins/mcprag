import { useState, useEffect, useRef, useCallback } from 'react';
import { Command, Search, ChevronRight, Code, Zap, FileText, Settings } from 'lucide-react';

interface SlashCommand {
  name: string;
  description: string;
  category: 'builtin' | 'custom' | 'mcp' | 'project';
  arguments?: string[];
  shortcut?: string;
}

interface CommandPaletteProps {
  onExecute: (command: SlashCommand, args?: string[]) => void;
}

export function CommandPalette({ onExecute }: CommandPaletteProps) {
  const [commands, setCommands] = useState<SlashCommand[]>([]);
  const [search, setSearch] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Fetch available commands
  useEffect(() => {
    if (isOpen && commands.length === 0) {
      fetchCommands();
    }
  }, [isOpen, commands.length]);

  const fetchCommands = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/commands');
      if (response.ok) {
        const data = await response.json();
        // Add default commands if not provided by API
        const defaultCommands: SlashCommand[] = [
          {
            name: '/clear',
            description: 'Clear the current conversation context',
            category: 'builtin',
            shortcut: '⌘K'
          },
          {
            name: '/init',
            description: 'Initialize CLAUDE.md for the project',
            category: 'builtin'
          },
          {
            name: '/permissions',
            description: 'Manage tool permissions',
            category: 'builtin'
          },
          {
            name: '/model',
            description: 'Switch Claude model',
            category: 'builtin',
            arguments: ['model']
          },
          {
            name: '/resume',
            description: 'Resume a previous session',
            category: 'builtin',
            arguments: ['session_id']
          },
          {
            name: '/help',
            description: 'Show available commands and usage',
            category: 'builtin'
          }
        ];
        
        // Merge API commands with defaults
        const apiCommands = Array.isArray(data) ? data : data.commands || [];
        const mergedCommands = [...defaultCommands, ...apiCommands];
        
        // Deduplicate by name
        const uniqueCommands = mergedCommands.reduce((acc, cmd) => {
          if (!acc.find((c: SlashCommand) => c.name === cmd.name)) {
            acc.push(cmd);
          }
          return acc;
        }, [] as SlashCommand[]);
        
        setCommands(uniqueCommands);
      }
    } catch (error) {
      console.error('Failed to fetch commands:', error);
      // Set default commands on error
      setCommands([
        {
          name: '/clear',
          description: 'Clear the current conversation context',
          category: 'builtin'
        },
        {
          name: '/help',
          description: 'Show available commands',
          category: 'builtin'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Filter commands based on search
  const filteredCommands = commands.filter(cmd => {
    const searchLower = search.toLowerCase();
    return cmd.name.toLowerCase().includes(searchLower) ||
           cmd.description.toLowerCase().includes(searchLower) ||
           cmd.category.toLowerCase().includes(searchLower);
  });

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => 
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => 
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          );
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            handleExecute(filteredCommands[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          setIsOpen(false);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands]);

  // Reset selected index when search changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [search]);

  // Focus search input when opening
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current && selectedIndex >= 0) {
      const items = listRef.current.querySelectorAll('[data-command-item]');
      const selectedItem = items[selectedIndex] as HTMLElement;
      if (selectedItem) {
        selectedItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex]);

  const handleExecute = useCallback((command: SlashCommand) => {
    // Parse arguments from search if present
    const args = search.split(' ').slice(1);
    onExecute(command, args.length > 0 ? args : undefined);
    setIsOpen(false);
    setSearch('');
  }, [search, onExecute]);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'builtin':
        return <Zap size={14} />;
      case 'custom':
        return <Code size={14} />;
      case 'mcp':
        return <Settings size={14} />;
      case 'project':
        return <FileText size={14} />;
      default:
        return <Command size={14} />;
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'builtin':
        return 'text-blue-500';
      case 'custom':
        return 'text-green-500';
      case 'mcp':
        return 'text-purple-500';
      case 'project':
        return 'text-orange-500';
      default:
        return 'text-gray-500';
    }
  };

  // Keyboard shortcut to open palette
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  return (
    <>
      {/* Trigger Button */}
      <button 
        className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-muted hover:bg-muted/80 rounded-md transition-colors"
        onClick={() => setIsOpen(true)}
        title="Open command palette (⌘K)"
      >
        <Command size={14} />
        <span className="hidden sm:inline">Commands</span>
        <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs bg-background rounded border border-border">
          <span className="text-[10px]">⌘</span>K
        </kbd>
      </button>
      
      {/* Command Palette Modal */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        >
          <div 
            className="fixed left-1/2 top-[20%] -translate-x-1/2 w-full max-w-2xl bg-background border border-border rounded-lg shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 p-4 border-b border-border">
              <Search size={18} className="text-muted-foreground flex-shrink-0" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder="Search commands..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted-foreground"
              />
              <kbd className="text-xs text-muted-foreground">ESC</kbd>
            </div>
            
            {/* Command List */}
            <div 
              ref={listRef}
              className="max-h-[400px] overflow-y-auto"
            >
              {loading ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  Loading commands...
                </div>
              ) : filteredCommands.length === 0 ? (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  No commands found
                </div>
              ) : (
                <div className="py-2">
                  {filteredCommands.map((cmd, index) => (
                    <button
                      key={cmd.name}
                      data-command-item
                      className={`w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-muted/50 transition-colors ${
                        index === selectedIndex ? 'bg-muted' : ''
                      }`}
                      onClick={() => handleExecute(cmd)}
                      onMouseEnter={() => setSelectedIndex(index)}
                    >
                      <span className={getCategoryColor(cmd.category)}>
                        {getCategoryIcon(cmd.category)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm">{cmd.name}</span>
                          {cmd.arguments && (
                            <span className="text-xs text-muted-foreground">
                              {cmd.arguments.map(arg => `<${arg}>`).join(' ')}
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground truncate">
                          {cmd.description}
                        </div>
                      </div>
                      {cmd.shortcut && (
                        <kbd className="text-xs px-1.5 py-0.5 bg-muted rounded">
                          {cmd.shortcut}
                        </kbd>
                      )}
                      {index === selectedIndex && (
                        <ChevronRight size={14} className="text-muted-foreground" />
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            
            {/* Footer */}
            <div className="flex items-center justify-between px-4 py-2 border-t border-border text-xs text-muted-foreground">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <kbd className="px-1 py-0.5 bg-muted rounded">↑↓</kbd> Navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1 py-0.5 bg-muted rounded">↵</kbd> Execute
                </span>
              </div>
              <div className="flex items-center gap-2">
                {Object.entries({builtin: 0, custom: 0, mcp: 0, project: 0}).map(([cat]) => {
                  const count = filteredCommands.filter((c: SlashCommand) => c.category === cat as SlashCommand['category']).length;
                  if (count === 0) return null;
                  return (
                    <span key={cat} className="flex items-center gap-1">
                      <span className={getCategoryColor(cat)}>
                        {getCategoryIcon(cat)}
                      </span>
                      {count}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}