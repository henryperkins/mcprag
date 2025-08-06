import React, { useState } from 'react';

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

export const FileTree: React.FC = () => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['/src', '/src/components']));
  const [selected, setSelected] = useState<string | null>(null);
  
  const toggleExpand = (path: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };
  
  const renderNode = (node: FileNode, depth = 0): React.ReactNode => {
    const isExpanded = expanded.has(node.path);
    const isSelected = selected === node.path;
    const indent = depth * 16;
    
    return (
      <div key={node.path}>
        <div
          className={`file-tree-item ${isSelected ? 'selected' : ''}`}
          style={{ paddingLeft: `${indent}px` }}
          onClick={() => {
            if (node.type === 'folder') {
              toggleExpand(node.path);
            } else {
              setSelected(node.path);
            }
          }}
        >
          <span className="file-tree-icon fg-ansi-8">
            {node.type === 'folder' ? (isExpanded ? '▼' : '▶') : '○'}{' '}
          </span>
          <span className={node.type === 'folder' ? 'fg-ansi-12' : 'fg-ansi-7'}>
            {node.name}
          </span>
        </div>
        {node.type === 'folder' && isExpanded && node.children && (
          <div>
            {node.children.map(child => renderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };
  
  return (
    <div className="file-tree-container">
      <div className="file-tree-header fg-ansi-10">
        Files
      </div>
      <div className="file-tree-content">
        {mockFileTree.map(node => renderNode(node))}
      </div>
    </div>
  );
};
