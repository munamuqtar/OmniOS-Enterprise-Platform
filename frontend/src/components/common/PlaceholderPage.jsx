import PageHeader from "./PageHeader";
import EmptyState from "./EmptyState";

export default function PlaceholderPage({ title }) {
  return (
    <>
      <PageHeader title={title} />
      <EmptyState title="Coming in the next step" hint="The navigation and permissions for this screen already work." />
    </>
  );
}