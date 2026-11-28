const flatten = (v) =>
  Array.isArray(v) ? v.map(flatten).filter(Boolean).join(" ")
  : v && typeof v === "object" ? Object.entries(v).map(([k, x]) => `${k}: ${flatten(x)}`).join(" ")
  : String(v ?? "");

/** Turns an axios error into { message, fields, status } for banners and form fields. */
export function parseApiError(error) {
  if (!error?.response) {
    return { message: "Cannot reach the server. Check your connection.", fields: {}, status: 0 };
  }
  const { status, data } = error.response;
  const fields = {};
  if (data?.errors && typeof data.errors === "object") {
    Object.entries(data.errors).forEach(([key, value]) => { fields[key] = flatten(value); });
  }
  let message = data?.message || "Something went wrong.";
  if (fields.non_field_errors) message = fields.non_field_errors;
  if (status === 429) message = "Too many attempts. Please wait a minute and try again.";
  if (status === 403 && !data?.message) message = "You do not have permission to do this.";
  return { message, fields, status };
}