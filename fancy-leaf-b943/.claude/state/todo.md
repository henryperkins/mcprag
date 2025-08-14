# Migration Todo: Merging src/components/ and src/studio/

## Pre-Migration Checklist
- [ ] Create git tag: `git tag pre-merge-backup-$(date +%Y%m%d)`
- [ ] Run existing test suite and document baseline
- [ ] Create `.claude/state/migration-log.md` for tracking progress
- [ ] Backup current production build

## Phase 1: Directory Structure Setup (Low Risk)
**Owner:** dependency-mapper
**Timeline:** Day 1

- [ ] Create new subdirectories:
  ```bash
  mkdir -p src/components/{core,chat,input,layout,features,cards}
  ```
- [ ] Create index.ts files for each subdirectory for clean exports
- [ ] Update .gitignore if needed
- [ ] Document new structure in README

## Phase 2: Move Non-Conflicting Components (No Risk)
**Owner:** code-reviewer → implementation
**Timeline:** Day 1-2

### Core Components (shared utilities)
- [ ] Move `AnsiText.tsx` → `core/AnsiText.tsx`
- [ ] Move `Skeleton.tsx` → `core/Skeleton.tsx`
- [ ] Move `CopyChip.tsx` → `core/CopyChip.tsx`
- [ ] Move `Toasts.tsx` → `core/Toasts.tsx`
- [ ] Move `OfflineIndicator.tsx` → `core/OfflineIndicator.tsx`
- [ ] Move `PwaInstallPrompt.tsx` → `core/PwaInstallPrompt.tsx`
- [ ] Move `RunningRibbon.tsx` → `core/RunningRibbon.tsx`

### Studio-Unique Components
- [ ] Move `studio/SessionsPane.tsx` → `features/SessionsPane.tsx`
- [ ] Move `studio/CodeCard.tsx` → `cards/CodeCard.tsx`
- [ ] Move `studio/StatusBar.tsx` → `layout/StatusBar.tsx`
- [ ] Move `studio/Sidebar.tsx` → `layout/Sidebar.tsx`
- [ ] Move `studio/DesignPrinciples.tsx` → `features/DesignPrinciples.tsx`
- [ ] Move `studio/stream.ts` → `chat/stream.ts`

### Feature Components
- [ ] Move `CommandPalette.tsx` → `features/CommandPalette.tsx`
- [ ] Move `FileTree.tsx` → `features/FileTree.tsx`
- [ ] Move `ToolsPanel.tsx` → `features/ToolsPanel.tsx`
- [ ] Move `ToolsPanel.test.tsx` → `features/ToolsPanel.test.tsx`

### Update Imports for Moved Components
- [ ] Update imports in `src/studio/ChatPage.tsx`
- [ ] Update imports in `src/studio/MessageList.tsx`
- [ ] Update imports in `src/studio/Composer.tsx`
- [ ] Update imports in `src/App.tsx`
- [ ] Update imports in any other affected files

## Phase 3: Component Consolidation (Medium Risk)
**Owner:** code-reviewer → test-runner
**Timeline:** Day 3-5

### Chat Components Merge
- [ ] Analyze differences: `ChatPane.tsx` vs `ChatPage.tsx`
  - [ ] Document functional differences
  - [ ] Identify shared logic
  - [ ] Plan unified interface
- [ ] Create `chat/ChatInterface.tsx` combining both
- [ ] Move `Transcript.tsx` → `chat/Transcript.tsx`
- [ ] Move `studio/MessageList.tsx` → `chat/MessageList.tsx`
- [ ] Move `ToolCallLine.tsx` → `chat/ToolCallLine.tsx`
- [ ] Create compatibility layer for existing usage

### Input Components Merge
- [ ] Analyze differences: `PromptBar.tsx` vs `Composer.tsx`
  - [ ] Document feature differences
  - [ ] Identify shared behaviors
  - [ ] Plan unified API
- [ ] Create `input/UnifiedInput.tsx` with both modes
- [ ] Move `SlashMenu.tsx` → `input/SlashMenu.tsx`
- [ ] Update imports in dependent components
- [ ] Add feature flag for switching modes (optional)

### Layout Components Merge
- [ ] Analyze differences: `Header.tsx` vs `TopBar.tsx`
  - [ ] Document styling differences
  - [ ] Identify shared props
  - [ ] Plan consolidated component
- [ ] Create `layout/Header.tsx` with variant prop
- [ ] Add compatibility exports for backward compatibility
- [ ] Test both variants thoroughly

## Phase 4: Import Path Updates (Low Risk)
**Owner:** dependency-mapper → implementation
**Timeline:** Day 6

- [ ] Create codemod script for automated import updates
- [ ] Update all imports to new paths:
  ```typescript
  // Before: import { AnsiText } from '../components/AnsiText'
  // After: import { AnsiText } from '../components/core/AnsiText'
  ```
- [ ] Run ESLint to catch any missed imports
- [ ] Update any dynamic imports or lazy loading
- [ ] Update test file imports
- [ ] Update storybook imports (if applicable)

## Phase 5: Testing & Validation
**Owner:** test-runner → security-screener
**Timeline:** Day 6-7

### Unit Testing
- [ ] Run existing test suite
- [ ] Add tests for merged components
- [ ] Test backward compatibility layers
- [ ] Test new unified interfaces

### Integration Testing
- [ ] Test App.tsx with new structure
- [ ] Test studio/ChatPage with new structure
- [ ] Test all user flows
- [ ] Test theme switching
- [ ] Test session management

### Performance Testing
- [ ] Measure bundle size before/after
- [ ] Check for any lazy loading issues
- [ ] Verify no circular dependencies
- [ ] Profile render performance

## Phase 6: Documentation & Cleanup
**Owner:** doc-writer
**Timeline:** Day 7

- [ ] Update component documentation
- [ ] Create migration guide
- [ ] Update README with new structure
- [ ] Add JSDocs to new unified components
- [ ] Create architecture decision record (ADR)
- [ ] Remove empty `src/studio/` directory
- [ ] Clean up any temporary compatibility code

## Phase 7: Post-Migration
**Owner:** orchestrator
**Timeline:** Day 8+

- [ ] Monitor for any production issues
- [ ] Gather developer feedback
- [ ] Plan removal of compatibility layers (future)
- [ ] Consider extracting to component library
- [ ] Update CI/CD if needed

## Rollback Plan
If critical issues discovered:
```bash
# Immediate rollback
git reset --hard pre-merge-backup-$(date +%Y%m%d)

# OR selective revert
git revert <merge-commit-hash>
```

## Success Criteria
- [ ] All existing tests pass
- [ ] No console errors in development
- [ ] No console errors in production build
- [ ] Bundle size reduced or stable
- [ ] All imports resolved correctly
- [ ] Documentation updated
- [ ] Team sign-off received

## Risk Log
| Risk | Mitigation | Status |
|------|------------|--------|
| Breaking production app | Feature flags, gradual rollout | ⏳ |
| Lost git history | Using git mv instead of delete/create | ⏳ |
| Missing functionality | Comprehensive testing checklist | ⏳ |
| Import path errors | Automated codemod script | ⏳ |
| Performance regression | Before/after benchmarking | ⏳ |

## Notes
- Keep `migration-log.md` updated daily
- Run tests after each phase
- Commit after each successful phase
- Use conventional commits for clear history
- Tag important milestones