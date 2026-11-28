import { useMutation } from "@tanstack/react-query";
import { parseApiError } from "../utils/errors";

/** run(...) never throws. It returns { ok, data } or { ok: false, error }, and exposes busy and error for the UI. */
export function useApiAction(fn, { onSuccess } = {}) {
  const m = useMutation({ mutationFn: fn, onSuccess });
  const run = async (...args) => {
    try {
      return { ok: true, data: await m.mutateAsync(...args) };
    } catch (e) {
      return { ok: false, data: null, error: parseApiError(e) };
    }
  };
  return { run, busy: m.isPending, error: m.error ? parseApiError(m.error) : null, reset: m.reset };
}