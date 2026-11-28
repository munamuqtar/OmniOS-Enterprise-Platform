import { useState } from "react";
import Modal from "./Modal";
import ErrorBanner from "../common/ErrorBanner";

export default function ConfirmDialog({
  open, title, message, confirmLabel = "Confirm", danger = false, requireReason = false,
  reasonLabel = "Reason", busy = false, error, onConfirm, onCancel,
}) {
  const [reason, setReason] = useState("");
  if (!open) return null;
  const canSubmit = !busy && (!requireReason || reason.trim().length > 0);
  const cancel = () => { setReason(""); onCancel(); };

  return (
    <Modal title={title} onClose={cancel} footer={
      <>
        <button className="btn btn-ghost" onClick={cancel} disabled={busy}>Cancel</button>
        <button className={`btn ${danger ? "btn-danger" : "btn-primary"}`} disabled={!canSubmit}
                onClick={() => onConfirm(reason.trim())}>
          {busy ? "Working…" : confirmLabel}
        </button>
      </>
    }>
      <ErrorBanner message={error} />
      <p>{message}</p>
      {requireReason && (
        <label className="field">
          <span>{reasonLabel}</span>
          <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
      )}
    </Modal>
  );
}