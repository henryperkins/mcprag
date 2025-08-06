import { useState, useEffect } from 'react'

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

  useEffect(() => {
    if (filter) {
      const filtered = commands.filter(cmd => 
        cmd.command.toLowerCase().includes(filter.toLowerCase()) ||
        cmd.description.toLowerCase().includes(filter.toLowerCase())
      )
      setFilteredCommands(filtered)
    } else {
      setFilteredCommands(commands)
    }
  }, [filter])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        onSelectedIndexChange(Math.min(selectedIndex + 1, filteredCommands.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        onSelectedIndexChange(Math.max(selectedIndex - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filteredCommands[selectedIndex]) {
          onSelect(filteredCommands[selectedIndex].command)
        }
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, filteredCommands, onSelect, onClose, onSelectedIndexChange])

  if (!isOpen) return null

  return (
    <div className="slash-menu">
      {filteredCommands.map((cmd, index) => (
        <div 
          key={cmd.command}
          className={`slash-menu-item ${index === selectedIndex ? 'selected' : ''}`}
          onClick={() => onSelect(cmd.command)}
        >
          <span className="slash-command">{cmd.command}</span>
          {cmd.args && <span className="slash-args"> {cmd.args}</span>}
          <span className="slash-description">{cmd.description}</span>
        </div>
      ))}
    </div>
  )
}