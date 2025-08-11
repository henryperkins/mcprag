import { useEffect, useState } from 'react';
import { Shield, Wrench, Server, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { claudeService } from '../services/claude';

interface ToolInfo {
  name: string;
  category: 'file' | 'search' | 'edit' | 'system' | 'mcp' | 'web';
  enabled: boolean;
  description?: string;
}

interface MCPServer {
  name: string;
  status: 'connected' | 'disconnected' | 'error' | 'connecting';
  tools: string[];
  error?: string;
}

export function ToolsPanel() {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    // Subscribe to tools updates from Claude service
    const unsubscribe = claudeService.on('tools-update', (data: any) => {
      // Categorize tools
      const categorizedTools = (data.tools || []).map((name: string) => ({
        name,
        category: getCategoryForTool(name),
        enabled: true,
        description: getToolDescription(name)
      }));
      
      setTools(categorizedTools);
      
      // Process MCP servers if available
      if (data.mcpServers) {
        setMcpServers(data.mcpServers.map((server: any) => ({
          name: server.name,
          status: server.status || 'disconnected',
          tools: server.tools || [],
          error: server.error
        })));
      }
    });

    // Request initial tools if available
    claudeService.emit('request-tools-info', {});
    
    return unsubscribe;
  }, []);

  const getCategoryForTool = (name: string): ToolInfo['category'] => {
    if (name.startsWith('mcp__')) return 'mcp';
    if (['Read', 'Write', 'LS', 'Glob', 'MultiEdit'].includes(name)) return 'file';
    if (['Edit', 'NotebookEdit'].includes(name)) return 'edit';
    if (['Grep', 'WebSearch', 'WebFetch'].includes(name)) return 'search';
    if (['WebFetch', 'WebSearch'].includes(name)) return 'web';
    if (['Bash', 'Git', 'TodoWrite', 'ExitPlanMode'].includes(name)) return 'system';
    return 'system';
  };

  const getToolDescription = (name: string): string => {
    const descriptions: Record<string, string> = {
      'Read': 'Read file contents',
      'Write': 'Write to files',
      'Edit': 'Edit existing files',
      'MultiEdit': 'Make multiple edits to a file',
      'LS': 'List directory contents',
      'Glob': 'Search for files by pattern',
      'Grep': 'Search file contents',
      'WebSearch': 'Search the web',
      'WebFetch': 'Fetch web page content',
      'Bash': 'Execute shell commands',
      'Git': 'Git version control',
      'TodoWrite': 'Manage task lists',
      'NotebookEdit': 'Edit Jupyter notebooks',
      'ExitPlanMode': 'Exit planning mode'
    };
    return descriptions[name] || '';
  };

  const categoryColors: Record<string, string> = {
    file: 'text-blue-500',
    edit: 'text-green-500',
    search: 'text-purple-500',
    system: 'text-orange-500',
    mcp: 'text-pink-500',
    web: 'text-cyan-500'
  };

  const categoryIcons: Record<string, string> = {
    file: '📁',
    edit: '✏️',
    search: '🔍',
    system: '⚙️',
    mcp: '🔌',
    web: '🌐'
  };

  const filteredTools = filter === 'all' 
    ? tools 
    : tools.filter(t => t.category === filter);

  const toolsByCategory = filteredTools.reduce((acc, tool) => {
    if (!acc[tool.category]) acc[tool.category] = [];
    acc[tool.category].push(tool);
    return acc;
  }, {} as Record<string, ToolInfo[]>);

  const statusIcon = (status: MCPServer['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircle size={14} className="text-green-500" />;
      case 'connecting':
        return <AlertCircle size={14} className="text-yellow-500 animate-pulse" />;
      case 'error':
        return <XCircle size={14} className="text-red-500" />;
      default:
        return <XCircle size={14} className="text-gray-400" />;
    }
  };

  return (
    <div className="tools-panel bg-background border border-border rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench size={20} className="text-muted-foreground" />
          <h3 className="font-semibold">Available Tools</h3>
          <span className="text-sm text-muted-foreground">({tools.length})</span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {isExpanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-1">
        {['all', 'file', 'edit', 'search', 'system', 'web', 'mcp'].map(cat => (
          <button
            key={cat}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              filter === cat 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-muted hover:bg-muted/80 text-muted-foreground'
            }`}
            onClick={() => setFilter(cat)}
          >
            <span className="mr-1">{categoryIcons[cat as keyof typeof categoryIcons]}</span>
            {cat}
          </button>
        ))}
      </div>

      {/* Tools by category */}
      {isExpanded && (
        <div className="space-y-3">
          {Object.entries(toolsByCategory).map(([category, categoryTools]) => (
            <div key={category} className="space-y-1">
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {category} Tools
              </div>
              <div className="flex flex-wrap gap-1">
                {categoryTools.map(tool => (
                  <div 
                    key={tool.name}
                    className={`inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md border ${
                      tool.enabled 
                        ? 'bg-muted/50 border-border' 
                        : 'bg-muted/20 border-border/50 opacity-50'
                    }`}
                    title={tool.description || tool.name}
                  >
                    <Shield 
                      size={10} 
                      className={tool.enabled ? categoryColors[category] : 'text-gray-400'} 
                    />
                    <span className="font-mono">{tool.name}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* MCP Servers */}
      {mcpServers.length > 0 && (
        <div className="border-t border-border pt-3 space-y-2">
          <div className="flex items-center gap-2">
            <Server size={16} className="text-muted-foreground" />
            <h4 className="text-sm font-medium">MCP Servers</h4>
          </div>
          <div className="space-y-1">
            {mcpServers.map(server => (
              <div 
                key={server.name} 
                className="flex items-center justify-between p-2 rounded bg-muted/30"
              >
                <div className="flex items-center gap-2">
                  {statusIcon(server.status)}
                  <span className="text-sm font-mono">{server.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {server.tools.length} tools
                  </span>
                  {server.error && (
                    <span className="text-xs text-red-500" title={server.error}>
                      Error
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      {!isExpanded && tools.length > 0 && (
        <div className="text-xs text-muted-foreground">
          {Object.entries(toolsByCategory).map(([cat, tools]) => (
            <span key={cat} className="mr-3">
              {categoryIcons[cat as keyof typeof categoryIcons]} {tools.length}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}