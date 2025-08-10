// ANSI parsing worker: converts ANSI strings to token arrays with CSS classes

export type AnsiToken = { text: string; classes: string[] };

type State = { fg?: number; bg?: number; bold?: boolean; italic?: boolean; underline?: boolean };

// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1b\[([0-9;]*)m/g;

function processAnsiCodes(codes: number[], state: State): State {
  const s: State = { ...state };
  for (let i = 0; i < codes.length; i++) {
    const code = codes[i];
    switch (code) {
      case 0: // reset
        return {};
      case 1:
        s.bold = true; break;
      case 3:
        s.italic = true; break;
      case 4:
        s.underline = true; break;
      case 22:
        s.bold = false; break;
      case 23:
        s.italic = false; break;
      case 24:
        s.underline = false; break;
      case 39:
        delete s.fg; break;
      case 49:
        delete s.bg; break;
      default:
        if (code >= 30 && code <= 37) s.fg = code - 30;
        else if (code >= 90 && code <= 97) s.fg = code - 90 + 8;
        else if (code >= 40 && code <= 47) s.bg = code - 40;
        else if (code >= 100 && code <= 107) s.bg = code - 100 + 8;
        else if (code === 38 && codes[i + 1] === 5) { s.fg = codes[i + 2]; i += 2; }
        else if (code === 48 && codes[i + 1] === 5) { s.bg = codes[i + 2]; i += 2; }
        break;
    }
  }
  return s;
}

function classesFor(state: State): string[] {
  const classes: string[] = [];
  if (state.fg !== undefined && state.fg >= 0 && state.fg <= 15) classes.push(`fg-ansi-${state.fg}`);
  if (state.bg !== undefined && state.bg >= 0 && state.bg <= 15) classes.push(`bg-ansi-${state.bg}`);
  if (state.bold) classes.push('ansi-bold');
  if (state.italic) classes.push('ansi-italic');
  if (state.underline) classes.push('ansi-underline');
  return classes;
}

function parseAnsi(input: string): AnsiToken[] {
  if (!input) return [];
  let lastIndex = 0;
  let state: State = {};
  const tokens: AnsiToken[] = [];
  const matches = Array.from(input.matchAll(ANSI_REGEX));
  for (const match of matches) {
    if (match.index! > lastIndex) {
      tokens.push({ text: input.slice(lastIndex, match.index), classes: classesFor(state) });
    }
    const codes = match[1].split(';').map((c) => parseInt(c, 10) || 0);
    state = processAnsiCodes(codes, state);
    lastIndex = match.index! + match[0].length;
  }
  if (lastIndex < input.length) {
    tokens.push({ text: input.slice(lastIndex), classes: classesFor(state) });
  }
  return tokens;
}

self.onmessage = (e: MessageEvent<string>) => {
  try {
    const tokens = parseAnsi(e.data);
    (self as any).postMessage(tokens);
  } catch {
    (self as any).postMessage([]);
  }
};

