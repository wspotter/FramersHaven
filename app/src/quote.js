const TAX_RATE = 0.06;

export function calculateQuote(input) {
  const width = Number(input.widthIn || 0);
  const height = Number(input.heightIn || 0);
  const mouldingCostPerFt = Number(input.mouldingCostPerFt || 0);
  const matCostPerSqFt = Number(input.matCostPerSqFt || 0);
  const matBorderIn = Number(input.matBorderIn || 0);
  const labor = Number(input.labor || 0);

  const perimeterFt = (2 * (width + height)) / 12;
  const moulding = roundMoney(perimeterFt * mouldingCostPerFt);

  const totalW = width + matBorderIn * 2;
  const totalH = height + matBorderIn * 2;
  const matAreaSqFt = (totalW * totalH) / 144;
  const mat = roundMoney(matAreaSqFt * matCostPerSqFt);

  const subtotal = roundMoney(moulding + mat + labor);
  const tax = roundMoney(subtotal * TAX_RATE);
  const total = roundMoney(subtotal + tax);

  return {
    lineItems: {
      moulding,
      mat,
      labor: roundMoney(labor)
    },
    measurements: { width, height, totalW, totalH, perimeterFt: round3(perimeterFt), matAreaSqFt: round3(matAreaSqFt) },
    subtotal,
    taxRate: TAX_RATE,
    tax,
    total
  };
}

function roundMoney(value) {
  return Math.round(value * 100) / 100;
}

function round3(value) {
  return Math.round(value * 1000) / 1000;
}
