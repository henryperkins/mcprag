import { useState, useEffect, useRef, useId } from 'react'
import { usePerformanceMonitor } from '../store/unified.adapter'

export interface SlashCommand {
  command: string
  description: string
  args?: string
}

const commands: SlashCommand[] = [
  { command: '/add-dir', description: 'Add a new working directory' },
  { command: '/agents', description: 'Manage agent configurations' },
  { command: '/bug', description: 'Submit feedback about Claude Code' },
  { command: '/clear', description: 'Clear conversation history and free up context', args: '(reset)' },
  { command: '/compact', description: 'Clear conversation history but keep a summary in context. Optional: /compact [instructions for summarization]' },
  { command: '/config', description: 'Open config panel', args: '(theme)' },
  { command: '/cost', description: 'Show the total cost and duration of the current session' },
  { command: '/doctor', description: 'Diagnose and verify your Claude Code installation and settings' },
  { command: '/exit', description: 'Exit the REPL', args: '(quit)' },
  { command: '/export', description: 'Export the current conversation to a file or clipboard' },
]

interface SlashMenuProps {
  isOpen: boolean
  filter: string
  onSelect: (command: string) => void
  onClose: () => void
  selectedIndex: number
  onSelectedIndexChange: (index: number) => void
}

export function SlashMenu({ 
  isOpen, 
  filter, 
  onSelect, 
  onClose,
  selectedIndex,
  onSelectedIndexChange
}: SlashMenuProps) {
  const [filteredCommands, setFilteredCommands] = useState(commands)
  const listboxRef = useRef<HTMLDivElement>(null)
  const optionRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const listboxId = useId()
  const { markInteraction } = usePerformanceMonitor()

  useEffect(() => {
    if (filter) {
      const filtered = commands.filter(cmd => 
        cmd.command.toLowerCase().includes(filter.toLowerCase()) ||
        cmd.description.toLowerCase().includes(filter.toLowerCase())
      )
      setFilteredCommands(filtered)
      // Reset selection when filter changes
      if (filtered.length > 0 && selectedIndex >= filtered.length) {
        onSelectedIndexChange(0)
      }
    } else {
      setFilteredCommands(commands)
    }
  }, [filter, selectedIndex, onSelectedIndexChange])

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      let handled = false
      
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          onSelectedIndexChange(Math.min(selectedIndex + 1, filteredCommands.length - 1))
          handled = true
          break
          
        case 'ArrowUp':
          e.preventDefault()
          onSelectedIndexChange(Math.max(selectedIndex - 1, 0))
          handled = true
          break
          
        case 'Home':
          e.preventDefault()
          onSelectedIndexChange(0)
          handled = true
          break
          
        case 'End':
          e.preventDefault()
          onSelectedIndexChange(filteredCommands.length - 1)
          handled = true
          break
          
        case 'Enter':
          e.preventDefault()
          if (filteredCommands[selectedIndex]) {
            onSelect(filteredCommands[selectedIndex].command)
            markInteraction('slashmenu:select', { command: filteredCommands[selectedIndex].command })
          }
          handled = true
          break
          
        case 'Escape':
          e.preventDefault()
          onClose()
          markInteraction('slashmenu:close')
          handled = true
          break
      }
      
      if (handled) {
        e.stopPropagation()
      }
    }

    // Use capture phase to ensure we handle events first
    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [isOpen, selectedIndex, filteredCommands, onSelect, onClose, onSelectedIndexChange, markInteraction])

  // Scroll selected item into view
  useEffect(() => {
    if (isOpen && selectedIndex >= 0) {
      const selectedOption = optionRefs.current.get(selectedIndex)
      if (selectedOption) {
        selectedOption.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
      }
    }
  }, [selectedIndex, isOpen])

  // Announce changes to screen readers
  useEffect(() => {
    if (isOpen && filteredCommands[selectedIndex]) {
      const cmd = filteredCommands[selectedIndex]
      const announcement = `${cmd.command}. ${cmd.description}`
      
      // Create temporary live region for announcement
      const liveRegion = document.createElement('div')
      liveRegion.setAttribute('role', 'status')
      liveRegion.setAttribute('aria-live', 'polite')
      liveRegion.setAttribute('aria-atomic', 'true')
      liveRegion.style.position = 'absolute'
      liveRegion.style.left = '-10000px'
      liveRegion.textContent = announcement
      document.body.appendChild(liveRegion)
      
      setTimeout(() => {
        document.body.removeChild(liveRegion)
      }, 100)
    }
  }, [selectedIndex, filteredCommands, isOpen])

  if (!isOpen) return null

  const activeDescendantId = selectedIndex >= 0 ? `${listboxId}-option-${selectedIndex}` : undefined

  return (
    <div 
      ref={listboxRef}
      className="slash-menu"
      role="listbox"
      aria-label="Slash commands"
      aria-activedescendant={activeDescendantId}
      id={listboxId}
      tabIndex={-1}
    >
      {filteredCommands.length === 0 ? (
        <div className="slash-menu-empty text-muted" role="option" aria-selected="false">
          No commands match "{filter}"
        </div>
      ) : (
        filteredCommands.map((cmd, index) => (
          <div 
            key={cmd.command}
            ref={el => {
              if (el) optionRefs.current.set(index, el)
              else optionRefs.current.delete(index)
            }}
            id={`${listboxId}-option-${index}`}
            className={`slash-menu-item ${index === selectedIndex ? 'selected' : ''}`}
            onClick={() => {
              onSelect(cmd.command)
              markInteraction('slashmenu:click-select', { command: cmd.command })
            }}
            role="option"
            aria-selected={index === selectedIndex}
            aria-describedby={`${listboxId}-desc-${index}`}
          >
            <span className="slash-command text-info" aria-label={`Command: ${cmd.command}`}>
              {cmd.command}
            </span>
            {cmd.args && (
              <span className="slash-args text-muted" aria-label={`Arguments: ${cmd.args}`}>
                {' '}{cmd.args}
              </span>
            )}
            <span 
              id={`${listboxId}-desc-${index}`}
              className="slash-description text-secondary"
            >
              {cmd.description}
            </span>
          </div>
        ))
      )}
      
      {/* Instructions for screen reader users */}
      <div className="sr-only" role="status" aria-live="polite">
        {filteredCommands.length} commands available. Use arrow keys to navigate, Enter to select, Escape to close.
      </div>
    </div>
  )
}