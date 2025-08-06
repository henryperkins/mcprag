import React, { useState, useCallback } from 'react';

interface CopyChipProps {
  code: string;
  language?: string;
}

export const CopyChip: React.FC<CopyChipProps> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  }, [code]);
  
  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        {language && <span className="code-language fg-ansi-8">{language}</span>}
        <button
          className="copy-button"
          onClick={handleCopy}
          role="button"
          aria-label={copied ? 'Copied' : 'Copy code'}
        >
          {copied ? (
            <span className="fg-ansi-10">✓ Copied</span>
          ) : (
            <span className="fg-ansi-7">Copy</span>
          )}
        </button>
      </div>
      <pre className="code-block">
        <code>{code}</code>
      </pre>
    </div>
  );
};
