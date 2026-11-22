/**
 * The API stores and returns UTC. Some fields arrive without a zone suffix
 * ("2026-11-22T17:26:07"); JavaScript would read those as local time and show
 * them 7 hours off, so every display goes through these helpers.
 */
export function parseUtc(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  if (value instanceof Date) return value;
  const text = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`;
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

const ZONE = "Asia/Bangkok";

/** "23 พ.ย. 2569 14:05" */
export function formatDateTime(value: string | Date | null | undefined, fallback = "—") {
  const date = parseUtc(value);
  return date
    ? date.toLocaleString("th-TH", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: ZONE,
      })
    : fallback;
}

/** "23 พ.ย." */
export function formatShortDate(value: string | Date | null | undefined, fallback = "—") {
  const date = parseUtc(value);
  return date
    ? date.toLocaleDateString("th-TH", { day: "numeric", month: "short", timeZone: ZONE })
    : fallback;
}

/** "2 วัน 3 ชม.", "1 ชม. 20 นาที", "15 นาที" (sign ignored). */
export function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(Math.abs(totalSeconds) / 60),
    hours = Math.floor(minutes / 60),
    days = Math.floor(hours / 24);
  if (days) return `${days} วัน${hours % 24 ? ` ${hours % 24} ชม.` : ""}`;
  if (hours) return `${hours} ชม.${minutes % 60 ? ` ${minutes % 60} นาที` : ""}`;
  return `${minutes} นาที`;
}
