const cents = (v) => Math.round((Number(v) || 0) * 100);

export function calcTotals(items, discount, taxRate) {
  const lines = items.map((i) => Math.round((Number(i.quantity) || 0) * cents(i.unit_price)));
  const subtotal = lines.reduce((a, b) => a + b, 0);
  const disc = cents(discount);
  const taxable = Math.max(subtotal - disc, 0);
  const tax = Math.round((taxable * (Number(taxRate) || 0)) / 100);
  return {
    lines: lines.map((c) => c / 100), subtotal: subtotal / 100, discount: disc / 100,
    tax: tax / 100, total: (taxable + tax) / 100, discountTooHigh: disc > subtotal,
  };
}