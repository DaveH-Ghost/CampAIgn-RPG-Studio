/**
 * Multi-area snapshot helpers (V0.4.0c1 engine, c2 UI).
 */

export const DEFAULT_AREA_ID = "room";

/** @param {unknown} value */
export function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function normalizeAreaBlock(area) {
  if (!area || typeof area !== "object") {
    return {
      grid: null,
      area_description: "",
      objects: [],
      decorations: [],
      recent_events: [],
    };
  }
  return {
    ...area,
    objects: asArray(area.objects),
    decorations: asArray(area.decorations),
    recent_events: asArray(area.recent_events),
  };
}

/** Full session snapshot with normalized area blocks. */
export function normalizeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return snapshot;
  }

  if (snapshot.areas && Object.keys(snapshot.areas).length > 0) {
    const areas = {};
    for (const [areaId, area] of Object.entries(snapshot.areas)) {
      areas[areaId] = normalizeAreaBlock(area);
    }
    const { grid: _g, area_description: _d, objects: _o, recent_events: _e, ...rest } = snapshot;
    return {
      ...rest,
      active_area_id: snapshot.active_area_id || DEFAULT_AREA_ID,
      areas,
      agents: asArray(snapshot.agents).map((agent) => ({
        ...agent,
        area_id: agent.area_id ?? snapshot.active_area_id ?? DEFAULT_AREA_ID,
      })),
    };
  }

  const grid = snapshot.grid;
  if (!grid) {
    return {
      ...snapshot,
      agents: asArray(snapshot.agents),
    };
  }

  const areaId = snapshot.active_area_id || DEFAULT_AREA_ID;
  return normalizeSnapshot({
    ...snapshot,
    active_area_id: areaId,
    areas: {
      [areaId]: normalizeAreaBlock({
        grid,
        area_description: snapshot.area_description ?? "",
        objects: snapshot.objects,
        recent_events: snapshot.recent_events,
      }),
    },
    agents: asArray(snapshot.agents).map((agent) => ({
      ...agent,
      area_id: agent.area_id ?? areaId,
    })),
  });
}

/** Active-area grid view for rendering and context menus. */
export function activeAreaView(snapshot) {
  const normalized = normalizeSnapshot(snapshot);
  if (!normalized?.areas || !normalized.active_area_id) {
    return {
      ...normalized,
      agents: asArray(normalized?.agents),
      objects: asArray(normalized?.objects),
      recent_events: asArray(normalized?.recent_events),
    };
  }
  const block = normalizeAreaBlock(normalized.areas[normalized.active_area_id]);
  const agentsHere = asArray(normalized.agents).filter(
    (a) => a.area_id === normalized.active_area_id,
  );
  return {
    ...normalized,
    grid: block.grid,
    area_description: block.area_description ?? "",
    objects: block.objects,
    decorations: block.decorations,
    agents: agentsHere,
    recent_events: block.recent_events,
  };
}

/** @deprecated Use activeAreaView */
export function normalizeUiSnapshot(snapshot) {
  return activeAreaView(snapshot);
}

/** @param {object} obj */
export function objectFootprintSize(obj) {
  return {
    width: Number(obj?.width ?? 1) || 1,
    height: Number(obj?.height ?? 1) || 1,
  };
}

/** @param {object} obj */
export function isMultiTileObject(obj) {
  const { width, height } = objectFootprintSize(obj);
  return width > 1 || height > 1;
}

/** @param {object} obj */
export function objectOccupiesTile(obj, x, y) {
  const { width, height } = objectFootprintSize(obj);
  const [ax, ay] = obj.position;
  return x >= ax && x < ax + width && y >= ay && y < ay + height;
}
