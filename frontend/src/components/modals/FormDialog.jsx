import Modal from "./Modal";
import ErrorBanner from "../common/ErrorBanner";

export default function FormDialog({ title, formId, busy, error, onClose, submitLabel, disabled, children }) {
  return (
    <Modal title={title} onClose={onClose} footer={
      <>
        <button className="btn btn-ghost" type="button" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" form={formId} disabled={busy || disabled}>{busy ? "Working…" : submitLabel}</button>
      </>
    }>
      <ErrorBanner message={error} />
      {children}
    </Modal>
  );
}