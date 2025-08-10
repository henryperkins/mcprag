export default function DesignPrinciples() {
  return (
    <section className="mx-auto max-w-4xl px-5 py-6 space-y-5">
      <h2 className="text-[22px] font-semibold tracking-tight text-white/95">
        Key Design Principles
      </h2>

      <article className="space-y-4">
        <h3 className="text-base font-semibold text-white/90">1. Stateful Context Management</h3>
        <ul className="list-disc pl-5 space-y-1 text-[15px] leading-relaxed text-[color:var(--text-secondary)]">
          <li>Maintain a running context of search results and findings</li>
          <li>Pass full context to the LLM for each decision</li>
          <li>Avoid redundant searches by tracking what&apos;s been explored</li>
        </ul>
      </article>

      <article className="space-y-3">
        <h3 className="text-base font-semibold text-white/90">2. Tool Chaining Strategy</h3>
        <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[color:color-mix(in srgb, var(--bg-elevated) 60%, transparent)] p-4">
          <pre className="m-0 whitespace-pre-wrap text-[13px] leading-[1.55] text-white/95">
            <code>{`search("topic") → fetch(urls) → extract(content) → search("follow-up")`}</code>
          </pre>
        </div>
      </article>

      <article className="space-y-2">
        <h3 className="text-base font-semibold text-white/90">3. Practical Implementation Tips</h3>
        <ul className="list-disc pl-5 space-y-1 text-[15px] leading-relaxed text-[color:var(--text-secondary)]">
          <li><span className="font-medium">Rate Limiting:</span> Implement backoff for API calls</li>
          <li><span className="font-medium">Caching:</span> Cache search results and reuse when possible</li>
        </ul>
      </article>
    </section>
  )
}
