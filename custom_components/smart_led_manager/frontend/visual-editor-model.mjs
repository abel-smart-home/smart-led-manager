export function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function rgbToHex(rgb) {
  return `#${rgb
    .map((channel) => Number(channel).toString(16).padStart(2, "0"))
    .join("")}`.toUpperCase();
}

export function hexToRgb(hex) {
  const value = String(hex).replace(/^#/, "");
  if (!/^[0-9a-fA-F]{6}$/.test(value)) {
    throw new Error("invalid hex color");
  }
  return [0, 2, 4].map((index) => Number.parseInt(value.slice(index, index + 2), 16));
}

export function sortPoints(points) {
  return deepClone(points).sort((left, right) => Number(left.value) - Number(right.value));
}

export function replacePoint(points, index, replacement) {
  const updated = deepClone(points);
  updated[index] = {
    value: Number(replacement.value),
    rgb: replacement.rgb.map(Number),
  };
  return sortPoints(updated);
}

export function removePoint(points, index) {
  return points.filter((_, pointIndex) => pointIndex !== index).map(deepClone);
}

export function validateDraft(mode, points, minimum = 2) {
  if (!['interpolate', 'ranges'].includes(mode)) {
    return "invalid_mode";
  }
  if (!Array.isArray(points) || points.length < minimum) {
    return "too_few_points";
  }
  const values = [];
  for (const point of points) {
    const value = Number(point.value);
    if (!Number.isFinite(value)) {
      return "invalid_value";
    }
    if (
      !Array.isArray(point.rgb) ||
      point.rgb.length !== 3 ||
      point.rgb.some(
        (channel) =>
          !Number.isInteger(Number(channel)) || Number(channel) < 0 || Number(channel) > 255,
      )
    ) {
      return "invalid_color";
    }
    values.push(value);
  }
  if (new Set(values).size !== values.length) {
    return "duplicate_value";
  }
  return null;
}

export function draftChanged(original, draft) {
  if (!original || !draft) return false;
  return JSON.stringify({ mode: original.mode, points: sortPoints(original.points) }) !==
    JSON.stringify({ mode: draft.mode, points: sortPoints(draft.points) });
}

export function pointPercent(value, points) {
  const ordered = sortPoints(points);
  if (!ordered.length) return 0;
  const minimum = Number(ordered[0].value);
  const maximum = Number(ordered.at(-1).value);
  if (minimum === maximum) return 50;
  return Math.max(0, Math.min(100, ((Number(value) - minimum) / (maximum - minimum)) * 100));
}

export function gradientStopEntries(points, mode) {
  const ordered = sortPoints(points);
  if (!ordered.length) return [];
  if (mode === "interpolate") {
    return ordered.map((point) => ({
      color: rgbToHex(point.rgb),
      offset: pointPercent(point.value, ordered),
    }));
  }
  const stops = [];
  ordered.forEach((point, index) => {
    const offset = pointPercent(point.value, ordered);
    if (index === 0) {
      stops.push({ color: rgbToHex(point.rgb), offset });
      return;
    }
    stops.push({ color: rgbToHex(ordered[index - 1].rgb), offset });
    stops.push({ color: rgbToHex(point.rgb), offset });
  });
  return stops;
}

export function cssGradient(points, mode) {
  const stops = gradientStopEntries(points, mode);
  if (!stops.length) return "transparent";
  return `linear-gradient(90deg, ${stops
    .map((stop) => `${stop.color} ${stop.offset}%`)
    .join(", ")})`;
}

export function nextPoint(points) {
  const ordered = sortPoints(points);
  if (!ordered.length) return { value: 0, rgb: [255, 255, 255] };
  const last = ordered.at(-1);
  const previous = ordered.at(-2);
  const step = previous ? Math.max(Number(last.value) - Number(previous.value), 1) : 1;
  return { value: Number(last.value) + step, rgb: deepClone(last.rgb) };
}
