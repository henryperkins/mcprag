import React, { useState, useRef, useEffect, useCallback, memo } from 'react';
import { usePerformanceMonitor } from '../store/unified.adapter';

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  children?: FileNode[];
  path: string;
}

const mockFileTree: FileNode[] = [
  {
    name: 'src',
    type: 'folder',
    path: '/src',
    children: [
      {
        name: 'components',
        type: 'folder',
        path: '/src/components',
        children: [
          { name: 'Terminal.tsx', type: 'file', path: '/src/components/Terminal.tsx' },
          { name: 'FileTree.tsx', type: 'file', path: '/src/components/FileTree.tsx' },
          { name: 'ChatPane.tsx', type: 'file', path: '/src/components/ChatPane.tsx' },
        ],
      },
      {
        name: 'utils',
        type: 'folder',
        path: '/src/utils',
        children: [
          { name: 'ansi.ts', type: 'file', path: '/src/utils/ansi.ts' },
          { name: 'crypto.ts', type: 'file', path: '/src/utils/crypto.ts' },
        ],
      },
      { name: 'App.tsx', type: 'file', path: '/src/App.tsx' },
      { name: 'main.tsx', type: 'file', path: '/src/main.tsx' },
    ],
  },
  {
    name: 'public',
    type: 'folder',
    path: '/public',
    children: [
      { name: 'manifest.webmanifest', type: 'file', path: '/public/manifest.webmanifest' },
    ],
  },
  { name: 'package.json', type: 'file', path: '/package.json' },
  { name: 'tsconfig.json', type: 'file', path: '/tsconfig.json' },
];


export const FileTree: React.FC<{ loading?: boolean }> = memo(function FileTree({ loading = false }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['/src', '/src/components']));
  const [selected, setSelected] = useState<string | null>(null);
  const [focusedPath, setFocusedPath] = useState<string | null>(null);
  
  const treeRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const { markInteraction } = usePerformanceMonitor();
  
  // Flatten tree for keyboard navigation
  const flatNodes = React.useMemo(() => {
    const flat: Array<FileNode & { level: number; visible: boolean }> = [];
    
    function traverse(nodes: FileNode[], level = 0) {
      nodes.forEach(node => {
        flat.push({ ...node, level, visible: true });
        if (node.type === 'folder' && expanded.has(node.path) && node.children) {
          traverse(node.children, level + 1);
        }
      });
    }
    
    traverse(mockFileTree);
    return flat;
  }, [expanded]);
  
  // Find visible nodes for keyboard navigation
  const visibleNodes = flatNodes.filter(n => n.visible);
  
  const toggleExpand = useCallback((path: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
        markInteraction('filetree:collapse', { path });
      } else {
        next.add(path);
        markInteraction('filetree:expand', { path });
      }
      return next;
    });
  }, [markInteraction]);
  
  const selectNode = useCallback((path: string, type: 'file' | 'folder') => {
    if (type === 'file') {
      setSelected(path);
      markInteraction('filetree:select-file', { path });
    }
  }, [markInteraction]);
  
  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = visibleNodes.findIndex(n => n.path === focusedPath);
    let newIndex = currentIndex;
    let handled = false;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        newIndex = Math.min(currentIndex + 1, visibleNodes.length - 1);
        if (newIndex === -1) newIndex = 0;
        handled = true;
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        newIndex = Math.max(currentIndex - 1, 0);
        if (newIndex === -1 && visibleNodes.length > 0) {
          newIndex = visibleNodes.length - 1;
        }
        handled = true;
        break;
        
      case 'ArrowRight':
        e.preventDefault();
        if (currentIndex >= 0) {
          const node = visibleNodes[currentIndex];
          if (node.type === 'folder') {
            if (!expanded.has(node.path)) {
              toggleExpand(node.path);
            } else if (node.children && node.children.length > 0) {
              // Move to first child
              newIndex = currentIndex + 1;
            }
          }
        }
        handled = true;
        break;
        
      case 'ArrowLeft':
        e.preventDefault();
        if (currentIndex >= 0) {
          const node = visibleNodes[currentIndex];
          if (node.type === 'folder' && expanded.has(node.path)) {
            toggleExpand(node.path);
          } else if (node.level > 0) {
            // Move to parent
            const parentPath = node.path.substring(0, node.path.lastIndexOf('/'));
            const parentIndex = visibleNodes.findIndex(n => n.path === parentPath);
            if (parentIndex >= 0) {
              newIndex = parentIndex;
            }
          }
        }
        handled = true;
        break;
        
      case 'Enter':
      case ' ':
        e.preventDefault();
        if (currentIndex >= 0) {
          const node = visibleNodes[currentIndex];
          if (node.type === 'folder') {
            toggleExpand(node.path);
          } else {
            selectNode(node.path, node.type);
          }
        }
        handled = true;
        break;
        
      case 'Home':
        e.preventDefault();
        newIndex = 0;
        handled = true;
        break;
        
      case 'End':
        e.preventDefault();
        newIndex = visibleNodes.length - 1;
        handled = true;
        break;
    }
    
    if (handled && newIndex !== currentIndex && newIndex >= 0 && newIndex < visibleNodes.length) {
      const newNode = visibleNodes[newIndex];
      setFocusedPath(newNode.path);
      
      // Focus the element
      const element = itemRefs.current.get(newNode.path);
      if (element) {
        element.focus();
        element.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [visibleNodes, focusedPath, expanded, toggleExpand, selectNode]);
  
  const renderNode = (node: FileNode, depth = 0, posInSet?: number, setSize?: number): React.ReactNode => {
    const isExpanded = expanded.has(node.path);
    const isSelected = selected === node.path;
    const isFocused = focusedPath === node.path;
    const indent = depth * 16;
    const nodeId = `tree-item-${node.path.replace(/\//g, '-')}`;
    
    return (
      <div key={node.path}>
        <div
          ref={el => {
            if (el) itemRefs.current.set(node.path, el);
            else itemRefs.current.delete(node.path);
          }}
          id={nodeId}
          className={`file-tree-item ${isSelected ? 'selected' : ''} ${isFocused ? 'focused' : ''}`}
          style={{ paddingLeft: `${indent}px` }}
          onClick={() => {
            setFocusedPath(node.path);
            if (node.type === 'folder') {
              toggleExpand(node.path);
            } else {
              selectNode(node.path, node.type);
            }
          }}
          onFocus={() => setFocusedPath(node.path)}
          role="treeitem"
          aria-expanded={node.type === 'folder' ? isExpanded : undefined}
          aria-selected={isSelected}
          aria-level={depth + 1}
          aria-setsize={setSize}
          aria-posinset={posInSet}
          tabIndex={isFocused ? 0 : -1}
        >
          <span className="file-tree-icon text-muted" aria-hidden="true">
            {node.type === 'folder' ? (isExpanded ? '▼' : '▶') : '○'}{' '}
          </span>
          <span className={node.type === 'folder' ? 'text-info' : 'text-secondary'}>
            {node.name}
          </span>
        </div>
        {node.type === 'folder' && isExpanded && node.children && (
          <div role="group">
            {node.children.map((child, i, arr) => renderNode(child, depth + 1, i + 1, arr.length))}
          </div>
        )}
      </div>
    );
  };
  
  // Set initial focus
  useEffect(() => {
    if (!focusedPath && visibleNodes.length > 0) {
      setFocusedPath(visibleNodes[0].path);
    }
  }, [focusedPath, visibleNodes]);
  
  // Announce selection changes to screen readers
  useEffect(() => {
    if (selected) {
      const announcement = `Selected file: ${selected}`;
      const liveRegion = document.createElement('div');
      liveRegion.setAttribute('role', 'status');
      liveRegion.setAttribute('aria-live', 'polite');
      liveRegion.setAttribute('aria-atomic', 'true');
      liveRegion.style.position = 'absolute';
      liveRegion.style.left = '-10000px';
      liveRegion.textContent = announcement;
      document.body.appendChild(liveRegion);
      
      setTimeout(() => {
        document.body.removeChild(liveRegion);
      }, 1000);
    }
  }, [selected]);
  
  return (
    <div className="file-tree">
      <div className="file-tree-header">
        <h2 className="file-tree-title text-brand">Files</h2>
      </div>
      <div
        ref={treeRef}
        className="file-tree-content"
        role="tree"
        aria-label="File explorer"
        aria-multiselectable="false"
        aria-describedby="filetree-instructions"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {loading ? (
          <div className="p-2" aria-busy="true">
            {/* basic skeleton lines to indicate loading the tree */}
            <div className="skeleton" style={{ height: 12, width: '70%', borderRadius: 6, marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 12, width: '55%', borderRadius: 6, marginBottom: 8, marginLeft: 16 }} />
            <div className="skeleton" style={{ height: 12, width: '62%', borderRadius: 6, marginBottom: 8, marginLeft: 16 }} />
            <div className="skeleton" style={{ height: 12, width: '78%', borderRadius: 6, marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 12, width: '48%', borderRadius: 6 }} />
          </div>
        ) : (
          mockFileTree.map((node, i, arr) => renderNode(node, 0, i + 1, arr.length))
        )}
      </div>
      
      {/* Instructions for screen reader users */}
      <div id="filetree-instructions" className="sr-only" aria-live="polite">
        Use arrow keys to navigate, Enter or Space to select or expand folders
      </div>
    </div>
  );
});
