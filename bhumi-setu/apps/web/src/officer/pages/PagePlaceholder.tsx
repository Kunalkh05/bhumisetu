interface PagePlaceholderProps {
  readonly title: string;
  readonly task: string;
  readonly requirements: string;
  readonly note?: string;
}

/**
 * Stands in for a page whose task has not run yet.
 *
 * Names the task and requirements it is waiting on rather than saying "coming
 * soon", so an unimplemented route is traceable to the plan instead of looking
 * like a bug.
 */
export function PagePlaceholder({ title, task, requirements, note }: PagePlaceholderProps) {
  return (
    <section aria-labelledby="page-title">
      <h1 id="page-title" className="text-xl font-semibold text-ink">
        {title}
      </h1>
      <dl className="mt-4 grid max-w-xl grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-ink-subtle">Task</dt>
        <dd className="font-mono text-ink-muted">{task}</dd>
        <dt className="text-ink-subtle">Requirements</dt>
        <dd className="font-mono text-ink-muted">{requirements}</dd>
      </dl>
      {note ? <p className="mt-4 max-w-xl text-sm text-ink-muted">{note}</p> : null}
    </section>
  );
}
