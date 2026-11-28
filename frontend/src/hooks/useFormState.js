import { useState } from "react";

export function useFormState(initial) {
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState({});
  return {
    values, errors, setErrors, setValues,
    set: (name, value) => setValues((v) => ({ ...v, [name]: value })),
    reset: (next = initial) => { setValues(next); setErrors({}); },
  };
}