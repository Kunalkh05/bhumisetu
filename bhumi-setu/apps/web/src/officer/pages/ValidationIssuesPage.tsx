import { PagePlaceholder } from './PagePlaceholder';

export function ValidationIssuesPage() {
  return (
    <PagePlaceholder
      title="Validation issues"
      task="18.5"
      requirements="14.3, 14.5, 14.8"
      note="Ordered by severity then detection time. A BLOCKING waiver needs the matching permission."
    />
  );
}
