/**
 * Resolve engine appearance paths to realm-studio static URLs (V0.3.2d).
 *
 * Engine stores client-relative paths (e.g. ``tokens/explorer.svg``).
 * Static files are served from ``/static/`` (the frontend directory).
 */

export function resolveAppearanceUrl(path) {
  const trimmed = String(path ?? "").trim();
  if (!trimmed) return "";
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  if (trimmed.startsWith("/")) {
    return trimmed;
  }
  return `/static/${trimmed.replace(/^\/+/, "")}`;
}

export function hasAppearance(entity) {
  return Boolean(String(entity?.appearance ?? "").trim());
}
