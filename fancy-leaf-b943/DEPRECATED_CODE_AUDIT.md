# Deprecated and Unused Code Audit

## Overview
This document identifies deprecated, replaced, and unused code in the fancy-leaf-b943 codebase as of the current implementation state.

## 1. Backup Files (Should be removed)

### Component Backups
- **Location**: `/src/components.backup/`
- **Status**: UNUSED - Entire directory is a backup
- **Files**: 
  - ChatPane.tsx
  - CopyChip.tsx
  - FileTree.tsx
  - Header.tsx
  - OfflineIndicator.tsx
  - PromptBar.tsx
  - PwaInstallPrompt.tsx
  - RunningRibbon.tsx
  - SlashMenu.tsx
  - Terminal.tsx
  - Toasts.tsx
  - ToolCallLine.tsx
  - Transcript.tsx
- **Action**: Delete entire `components.backup/` directory

### CSS Backups
- **Files**:
  - `/src/index.css.backup`
  - `/src/index.css.backup.full`
- **Status**: UNUSED - Backup files
- **Action**: Delete both files

### Main Application Backups
- **Files**:
  - `/src/App.tsx.backup`
  - `/src/main.tsx.backup`
- **Status**: UNUSED - Backup files
- **Action**: Delete both files

## 2. Unused Alternative Implementations

### Simple App Version
- **File**: `/src/App.simple.tsx`
- **Status**: UNUSED - Alternative simpler implementation
- **Description**: Simplified version of the main App component, not imported anywhere
- **Action**: Delete or move to examples directory

### Simple Worker
- **File**: `/src/simple-worker.ts`
- **Status**: UNUSED - Alternative worker implementation
- **Description**: Simplified worker implementation, not referenced in build
- **Action**: Delete or move to examples directory

## 3. Potentially Unused Store Files

### Session Store (Duplicate)
- **File**: `/src/store/session.ts`
- **Status**: POTENTIALLY UNUSED
- **Description**: Appears to be an older session store implementation. The app uses `session.state.ts` instead
- **Imports**: Only imported by `/src/studio/ChatPage.tsx`
- **Action**: Verify if `studio/` components are still needed, if not, delete both

## 4. Studio Components (Verify Usage)

### Studio Directory
- **Location**: `/src/studio/`
- **Status**: ACTIVE BUT VERIFY NECESSITY
- **Current Usage**: Only `ChatPage.tsx` is imported in `main.tsx`
- **Files**:
  - ChatPage.tsx (USED - main entry point)
  - CodeCard.tsx (Check if used by ChatPage)
  - Composer.tsx (Check if used by ChatPage)
  - DesignPrinciples.tsx (Check if used by ChatPage)
  - MessageList.tsx (Check if used by ChatPage)
  - SessionsPane.tsx (Check if used by ChatPage)
  - Sidebar.tsx (Check if used by ChatPage)
  - StatusBar.tsx (Check if used by ChatPage)
  - TopBar.tsx (Check if used by ChatPage)
  - stream.ts (Check if used by ChatPage)
- **Action**: Audit which studio components are actually used

## 5. Legacy Code Patterns

### Legacy Message Handling
- **File**: `/src/services/claude.ts`
- **Location**: Lines 372-415 (handleLegacyMessage method)
- **Status**: DEPRECATED BUT ACTIVE
- **Description**: Handles old message format for backward compatibility
- **Code**:
  ```typescript
  // Legacy tool-call and tool-output handling
  if (message.type === 'tool-call' && message.toolName && message.toolId) {
    // ... legacy handling
  }
  ```
- **Action**: Add deprecation timeline and migration plan

## 6. TODO Comments

### Worker Gateway
- **File**: `/src/worker-gateway.ts`
- **TODOs**:
  - Line 961: `// TODO: implement indexing/analytics; placeholder no-op`
  - Line 964: `// TODO: generate thumbnails/scan/etc.; placeholder no-op`
- **Status**: Incomplete features
- **Action**: Create tickets for implementation or remove if not needed

## 7. Commented/Placeholder Code

### Durable Object Storage
- **File**: `/src/worker-gateway.ts`
- **Lines**: 246-248
- **Description**: Placeholder comment about message key tracking
  ```typescript
  // Clear all message keys - we'll track them separately if needed
  // For now, just clear the main collections
  // In production, you'd want to track message keys or use a different storage pattern
  ```
- **Action**: Implement proper message key tracking or document current approach

## 8. Unused Imports and Variables

### ESLint Disabled Warning
- **File**: `/src/store/toolCalls.state.ts`
- **Line**: 109
- **Code**: `// eslint-disable-next-line @typescript-eslint/no-unused-vars`
- **Action**: Review and fix the unused variable or remove if not needed

## Recommended Cleanup Actions

### Immediate (Safe to Delete)
1. Delete `/src/components.backup/` directory
2. Delete all `.backup` files in `/src/`
3. Delete `/src/App.simple.tsx`
4. Delete `/src/simple-worker.ts`

### After Verification
1. Audit `/src/studio/` component usage
2. If studio components are minimal, consider merging necessary parts into main components
3. Delete `/src/store/session.ts` if confirmed unused
4. Remove legacy message handling after migration period

### Technical Debt
1. Implement or remove TODO items in worker-gateway.ts
2. Add proper message key tracking in Durable Objects
3. Document or implement deprecation timeline for legacy code

## File Size Impact
Removing all identified unused files would reduce the codebase by approximately:
- ~15 component files (components.backup/)
- ~3 backup files
- ~2 alternative implementations
- Potentially ~10 studio files if unused

This cleanup would improve:
- Build times
- Code clarity
- Maintenance burden
- Bundle size (if any unused code is being bundled)

## Migration Notes
Before deleting any files:
1. Ensure no dynamic imports reference them
2. Check git history for any valuable code that might need preserving
3. Consider creating a final backup branch before cleanup
4. Update any documentation that might reference deleted files