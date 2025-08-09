import React from 'react';
import type { ReactNode } from 'react';

interface AnsiState {
  fg?: number;
  bg?: number;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
}

const ANSI_REGEX = /\x1b\[([0-9;]*)m/g;

export function renderAnsiToSpans(input: string): ReactNode {
  if (!input) return null;
  
  const segments: ReactNode[] = [];
  let lastIndex = 0;
  let currentState: AnsiState = {};
  let key = 0;
  
  const matches = Array.from(input.matchAll(ANSI_REGEX));
  
  for (const match of matches) {
    // Add text before the ANSI code
    if (match.index! > lastIndex) {
      const text = input.slice(lastIndex, match.index);
      segments.push(createSpan(text, currentState, key++));
    }
    
    // Parse ANSI codes
    const codes = match[1].split(';').map(c => parseInt(c, 10) || 0);
    currentState = processAnsiCodes(codes, currentState);
    
    lastIndex = match.index! + match[0].length;
  }
  
  // Add remaining text
  if (lastIndex < input.length) {
    const text = input.slice(lastIndex);
    segments.push(createSpan(text, currentState, key++));
  }
  
  return segments.length > 0 ? React.createElement(React.Fragment, null, ...segments) : null;
}

function processAnsiCodes(codes: number[], state: AnsiState): AnsiState {
  const newState = { ...state };
  
  for (let i = 0; i < codes.length; i++) {
    const code = codes[i];
    
    switch (code) {
      case 0: // Reset
        return {};
      case 1: // Bold
        newState.bold = true;
        break;
      case 3: // Italic
        newState.italic = true;
        break;
      case 4: // Underline
        newState.underline = true;
        break;
      case 22: // Not bold
        newState.bold = false;
        break;
      case 23: // Not italic
        newState.italic = false;
        break;
      case 24: // Not underline
        newState.underline = false;
        break;
      case 39: // Default foreground
        delete newState.fg;
        break;
      case 49: // Default background
        delete newState.bg;
        break;
      default:
        // Foreground colors 30-37, bright 90-97
        if (code >= 30 && code <= 37) {
          newState.fg = code - 30;
        } else if (code >= 90 && code <= 97) {
          newState.fg = code - 90 + 8;
        }
        // Background colors 40-47, bright 100-107
        else if (code >= 40 && code <= 47) {
          newState.bg = code - 40;
        } else if (code >= 100 && code <= 107) {
          newState.bg = code - 100 + 8;
        }
        // 256 color mode
        else if (code === 38 && codes[i + 1] === 5) {
          const colorIndex = codes[i + 2];
          if (colorIndex >= 0 && colorIndex <= 15) {
            newState.fg = colorIndex;
          }
          i += 2;
        } else if (code === 48 && codes[i + 1] === 5) {
          const colorIndex = codes[i + 2];
          if (colorIndex >= 0 && colorIndex <= 15) {
            newState.bg = colorIndex;
          }
          i += 2;
        }
        break;
    }
  }
  
  return newState;
}

function createSpan(text: string, state: AnsiState, key: number): ReactNode {
  if (!text) return null;
  
  const classes: string[] = [];
  
  if (state.fg !== undefined) {
    classes.push(`fg-ansi-${state.fg}`);
  }
  if (state.bg !== undefined) {
    classes.push(`bg-ansi-${state.bg}`);
  }
  if (state.bold) classes.push('ansi-bold');
  if (state.italic) classes.push('ansi-italic');
  if (state.underline) classes.push('ansi-underline');
  
  // Always wrap text in a span element for consistent rendering
  return React.createElement('span', {
    key,
    className: classes.length > 0 ? classes.join(' ') : undefined,
    style: { display: 'inline' }
  }, text);
}