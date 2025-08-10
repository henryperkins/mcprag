# Claude Code Frontend Remediation Plan

This document translates the UI-redesigner audit into concrete, code-level changes your React frontend can implement. It prioritizes critical fixes first, then high-value improvements and quick wins. Each section includes ready-to-use examples.

---

## Priorities Overview

- P0 (Immediate):
  - Virtualize terminal output rendering
  - Fix ARIA roles and keyboard nav in FileTree
  - Add React.memo and stabilize props/callbacks

- P1 (High Priority):
  - Move ANSI parsing to a Web Worker
  - Add accessibility landmarks + skip links
  - Unify duplicated components
  - Add skeleton/loading states
  - Lazy-load Monaco/editor and other heavy bundles

- Quick Wins (< 1 day):
  - Wrap components in `React.memo`
  - Implement skip links
  - Correct FileTree ARIA tree roles
  - Persist theme to `localStorage`
  - Improve focus indicators and touch targets

---

## P0 Fixes

### 1) Terminal Virtualization

Use `react-window` or `react-virtualized` to render only visible lines. This eliminates O(N) DOM growth for transcripts > 2,000 lines.

Install:

```bash
npm i react-window
```

Example (Fixed line height):

```tsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FixedSizeList as List, ListOnScrollProps } from 'react-window';

type TerminalProps = {
  lines: string[];          // pre-split or tokenized lines
  lineHeight?: number;      // px
  width?: number | string;
  height?: number;          // px viewport height
  autoScroll?: boolean;     // keeps stick-to-bottom behavior when true
};

export const VirtualizedTerminal: React.FC<TerminalProps> = ({
  lines,
  lineHeight = 18,
  width = '100%',
  height = 360,
  autoScroll = true,
}) => {
  const listRef = useRef<List>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);

  const itemCount = lines.length;

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style} className="term-row">
      {lines[index]}
    </div>
  );

  const onScroll = ({ scrollDirection, scrollOffset, scrollUpdateWasRequested }: ListOnScrollProps) => {
    if (!autoScroll) return;
    // If user scrolled up, pause sticky; if scroll was programmatic, keep it.
    setIsUserScrolling(!scrollUpdateWasRequested);
  };

  useEffect(() => {
    if (!autoScroll || isUserScrolling) return;
    // Stick to bottom on new content
    listRef.current?.scrollToItem(itemCount - 1);
  }, [itemCount, autoScroll, isUserScrolling]);

  return (
    <List
      ref={listRef}
      height={height}
      itemCount={itemCount}
      itemSize={lineHeight}
      width={width}
      onScroll={onScroll}
    >
      {Row}
    </List>
  );
};
```

For variable-height rows (e.g., wrapped lines), use `react-virtualized`’s `CellMeasurer` or `react-window` with `VariableSizeList` and a line-height cache.

Key tips:
- Maintain a “stick-to-bottom unless user scrolled up” rule.
- Keep terminal state outside the component or behind a store to reduce re-renders.
- Avoid `dangerouslySetInnerHTML`; render tokens safely (see Web Worker section).

### 2) FileTree ARIA Roles + Keyboard Navigation

Implement a proper ARIA tree pattern with roving `tabindex`. Use `role="tree"`, `role="treeitem"`, `role="group"`, `aria-expanded`, and `aria-selected`.

```tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type Node = {
  id: string;
  name: string;
  children?: Node[];
};

type FileTreeProps = {
  root: Node;
  onOpen?: (id: string) => void;
};

export const FileTree: React.FC<FileTreeProps> = ({ root, onOpen }) => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const treeRef = useRef<HTMLDivElement>(null);

  const flatList = useMemo(() => {
    const out: { node: Node; level: number; parentId?: string }[] = [];
    const walk = (n: Node, level: number) => {
      out.push({ node: n, level });
      if (n.children && expanded.has(n.id)) {
        for (const c of n.children) walk(c, level + 1);
      }
    };
    walk(root, 1);
    return out;
  }, [root, expanded]);

  const indexById = useMemo(() => {
    const idx = new Map<string, number>();
    flatList.forEach((x, i) => idx.set(x.node.id, i));
    return idx;
  }, [flatList]);

  const focusItem = useCallback((id: string | null) => setActiveId(id), []);

  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!flatList.length) return;
    const currentIdx = activeId ? indexById.get(activeId) ?? 0 : 0;
    const current = flatList[currentIdx];
    const isFolder = !!current?.node.children?.length;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        focusItem(flatList[Math.min(currentIdx + 1, flatList.length - 1)].node.id);
        break;
      case 'ArrowUp':
        e.preventDefault();
        focusItem(flatList[Math.max(currentIdx - 1, 0)].node.id);
        break;
      case 'ArrowRight':
        if (isFolder && !expanded.has(current.node.id)) {
          e.preventDefault();
          setExpanded(new Set(expanded).add(current.node.id));
        }
        break;
      case 'ArrowLeft':
        if (isFolder && expanded.has(current.node.id)) {
          e.preventDefault();
          const next = new Set(expanded);
          next.delete(current.node.id);
          setExpanded(next);
        }
        break;
      case 'Home':
        e.preventDefault();
        focusItem(flatList[0].node.id);
        break;
      case 'End':
        e.preventDefault();
        focusItem(flatList[flatList.length - 1].node.id);
        break;
      case 'Enter':
      case ' ': {
        e.preventDefault();
        if (isFolder) {
          const next = new Set(expanded);
          next.has(current.node.id) ? next.delete(current.node.id) : next.add(current.node.id);
          setExpanded(next);
        } else {
          onOpen?.(current.node.id);
        }
        break;
      }
    }
  }, [activeId, expanded, focusItem, flatList, indexById, onOpen]);

  return (
    <div
      ref={treeRef}
      role="tree"
      aria-label="File explorer"
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="file-tree"
    >
      {flatList.map(({ node, level }) => {
        const isFolder = !!node.children?.length;
        const isExpanded = expanded.has(node.id);
        const isActive = activeId === node.id;
        return (
          <div
            key={node.id}
            role="treeitem"
            aria-level={level}
            aria-expanded={isFolder ? isExpanded : undefined}
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            onFocus={() => setActiveId(node.id)}
            className={`treeitem ${isActive ? 'active' : ''}`}
            style={{ paddingLeft: (level - 1) * 12 }}
          >
            {isFolder && (
              <button
                aria-label={isExpanded ? 'Collapse folder' : 'Expand folder'}
                onClick={() => {
                  const next = new Set(expanded);
                  next.has(node.id) ? next.delete(node.id) : next.add(node.id);
                  setExpanded(next);
                }}
              >
                {isExpanded ? '▾' : '▸'}
              </button>
            )}
            <span className="name">{node.name}</span>
          </div>
        );
      })}
    </div>
  );
};
```

Checklist:
- Wrap tree in `role="tree"` with label.
- Each item has `role="treeitem"` and `aria-level`.
- Folders expose `aria-expanded` and toggles.
- Roving `tabindex` with keyboard handling for Arrow/Enter/Space/Home/End.

### 3) React.memo + Stable Inputs

- Wrap list-like and presentational components in `React.memo`.
- Provide stable callbacks via `useCallback` and memoize derived props with `useMemo`.
- Split contexts to minimize unrelated consumer re-renders.

```tsx
import React, { memo, useCallback, useMemo } from 'react';

type Item = { id: string; label: string; selected?: boolean };

const ItemRow = memo(function ItemRow({ item, onSelect }: { item: Item; onSelect: (id: string) => void }) {
  return (
    <button className={`row ${item.selected ? 'sel' : ''}`} onClick={() => onSelect(item.id)}>
      {item.label}
    </button>
  );
});

export function ItemList({ items, onSelect }: { items: Item[]; onSelect: (id: string) => void }) {
  const stableOnSelect = useCallback((id: string) => onSelect(id), [onSelect]);
  const rows = useMemo(() => items.map((i) => <ItemRow key={i.id} item={i} onSelect={stableOnSelect} />), [items, stableOnSelect]);
  return <div>{rows}</div>;
}
```

---

## P1 Improvements

### 4) Move ANSI Parsing to a Web Worker

Avoid blocking the main thread. Parse incoming chunks off-thread and send tokens/lines back to the UI.

Install an ANSI library (example):

```bash
npm i ansi-up
```

Worker (e.g., `ansiWorker.ts`):

```ts
import ANSIUp from 'ansi-up';

const ansi = new ANSIUp();
self.onmessage = (e: MessageEvent<string[]>) => {
  const lines = e.data;
  const htmlLines = lines.map((l) => ansi.ansi_to_html(l));
  // Or return structured tokens if your renderer expects it
  // const tokens = tokenize(l)
  (self as unknown as Worker).postMessage(htmlLines);
};
```

Main thread hook:

```ts
import { useEffect, useRef, useState } from 'react';

export function useAnsiWorker() {
  const workerRef = useRef<Worker>();
  const [parsed, setParsed] = useState<string[]>([]);

  useEffect(() => {
    workerRef.current = new Worker(new URL('./ansiWorker.ts', import.meta.url), { type: 'module' });
    workerRef.current.onmessage = (e) => setParsed(e.data as string[]);
    return () => workerRef.current?.terminate();
  }, []);

  const parse = (lines: string[]) => workerRef.current?.postMessage(lines);
  return { parsed, parse };
}
```

Render with sanitized HTML or convert to safe spans. Prefer token arrays over raw HTML when possible.

### 5) Accessibility Landmarks + Skip Links

Add semantic landmarks and a skip link to the main content.

```tsx
// App shell
export function AppShell() {
  return (
    <>
      <a href="#main" className="skip-link">Skip to main content</a>
      <header role="banner">…</header>
      <nav aria-label="Primary">…</nav>
      <main id="main" tabIndex={-1}>…</main>
      <aside aria-label="Secondary">…</aside>
      <footer role="contentinfo">…</footer>
    </>
  );
}
```

CSS:

```css
.skip-link {
  position: absolute;
  left: -999px;
  top: -999px;
}
.skip-link:focus {
  left: 8px;
  top: 8px;
  background: #fff;
  color: #000;
  padding: 8px 12px;
  border-radius: 6px;
}
```

### 6) Unify Duplicated Components

- Consolidate Terminal and FileTree to one implementation each with prop-driven variations.
- Extract shared primitives: Button, Icon, SplitPane, Panel, Toolbar.
- Use a design system or tokens to ensure consistent spacing, color, and state styles.

### 7) Skeleton/Loading States

```tsx
export const Skeleton: React.FC<{ width?: number | string; height?: number | string }> = ({ width = '100%', height = 16 }) => (
  <div className="skeleton" style={{ width, height }} aria-hidden="true" />
);
```

```css
.skeleton {
  background: linear-gradient(90deg, #eee, #f6f6f6, #eee);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
```

Use as fallbacks for Terminal, FileTree, and Editor while data or heavy bundles load.

### 8) Lazy-load Monaco and Heavy Bundles

```tsx
import React, { Suspense } from 'react';
const MonacoEditor = React.lazy(() => import('@monaco-editor/react'));

export function EditorArea(props: any) {
  return (
    <Suspense fallback={<div style={{ height: 300 }}><Skeleton height={300} /></div>}>
      <MonacoEditor {...props} />
    </Suspense>
  );
}
```

Preload on demand:

```ts
export function preloadMonaco() {
  import('@monaco-editor/react');
}
```

Bundle tips:
- Prefer route- and panel-level code splitting with dynamic `import()`.
- Avoid bundling optional features until used.

---

## Quick Wins

### Theme Persistence

```ts
// theme.ts
export type Theme = 'light' | 'dark' | 'system';
const KEY = 'app-theme';

export function getInitialTheme(): Theme {
  const saved = localStorage.getItem(KEY) as Theme | null;
  return saved ?? 'system';
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.dataset.theme = theme;
  localStorage.setItem(KEY, theme);
}
```

Apply early in app bootstrap to avoid flash of incorrect theme.

### Focus Indicators and Touch Targets

```css
button, [role="button"], .clickable {
  min-width: 44px;
  min-height: 44px;
}

*:focus-visible {
  outline: 2px solid #2563eb; /* ensure 3:1 contrast */
  outline-offset: 2px;
}
```

### Contrast Validation

- Use tokens and check with automated tooling (e.g., axe or jest-axe in CI).
- Target at least 4.5:1 for text < 18pt; 3:1 for UI components and large text.

---

## Performance Notes

- Memoize derived data and stabilize callback identities to prevent re-render cascades.
- Segment context providers so that updates don’t fan out unnecessarily.
- Consider `useSyncExternalStore` for log/terminal feeds to minimize React reconciliation.
- Offload heavy parsing (ANSI, diff rendering) to Workers; debounce updates.

---

## Implementation Sequence (Suggested)

1) Terminal virtualization (P0) + stick-to-bottom behavior.
2) FileTree ARIA roles + keyboard navigation (P0).
3) React.memo + stable props/callbacks across hot paths (P0/QW).
4) ANSI parsing to Worker (P1).
5) Accessibility landmarks and skip links (P1/QW).
6) Skeleton states and lazy-load Monaco (P1).
7) Theme persistence + focus/touch improvements (QW).
8) Unify components and remove duplicates.

---

## Verification Checklist

- Terminal renders >100k lines smoothly and stays responsive.
- FileTree is fully navigable via keyboard and announced by screen readers.
- No long tasks >50 ms on main thread during ANSI-heavy updates.
- Axe and Lighthouse audits pass A11y checks; color contrast meets WCAG.
- Bundle analysis shows Monaco and other heavy modules in async chunks.

---

If you share the correct frontend repository, we can turn these snippets into precise patches/PRs in context.

