/** App tab switching (Main / Lorebooks / Templates / Plugins). */

const TAB_IDS = ["main", "lorebooks", "templates", "plugins"];

const onTabShow = {
  lorebooks: null,
  templates: null,
  plugins: null,
};

export function registerTabShowHandler(tabId, handler) {
  if (tabId in onTabShow) {
    onTabShow[tabId] = handler;
  }
}

export function initAppTabs() {
  const panels = Object.fromEntries(
    TAB_IDS.map((id) => [id, document.getElementById(`${id}-tab-panel`)]),
  );
  const tabs = Object.fromEntries(TAB_IDS.map((id) => [id, document.getElementById(`tab-${id}`)]));
  if (!tabs.main || !panels.main) return;

  function showTab(which) {
    for (const id of TAB_IDS) {
      const active = id === which;
      const tab = tabs[id];
      const panel = panels[id];
      if (tab) {
        tab.classList.toggle("active", active);
        tab.setAttribute("aria-selected", active ? "true" : "false");
      }
      if (panel) {
        panel.classList.toggle("hidden", !active);
      }
    }
    const handler = onTabShow[which];
    if (typeof handler === "function") {
      void handler();
    }
  }

  for (const id of TAB_IDS) {
    const tab = tabs[id];
    if (tab) {
      tab.addEventListener("click", () => showTab(id));
    }
  }
}
