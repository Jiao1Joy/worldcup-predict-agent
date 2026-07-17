export function ApprovalPanel({
  onApprove,
  disabled = false,
}: {
  onApprove: (choice: string) => void;
  disabled?: boolean;
}) {
  return (
    <section className="approval-panel" aria-label="Human approval required">
      <p className="eyebrow">HUMAN IN THE LOOP</p>
      <h2>Data snapshots conflict</h2>
      <p>Choose which snapshot should continue through the prediction graph.</p>
      <button type="button" onClick={() => onApprove('official')} disabled={disabled}>Use official snapshot</button>
      <button type="button" onClick={() => onApprove('cached')} disabled={disabled}>Use cached snapshot</button>
    </section>
  );
}
