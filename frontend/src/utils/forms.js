/** Builds multipart form data. Empty strings are kept (so fields can be cleared); null and undefined are skipped. */
export function toFormData(values) {
  const fd = new FormData();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null) fd.append(key, value);
  });
  return fd;
}

export const MULTIPART = { headers: { "Content-Type": "multipart/form-data" } };