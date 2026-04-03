const DOMAIN = "dashboard_rotator";
const RUNTIME_ROLE = "runtime";
const REPORT_INTERVAL_MS = 5000;
const TICK_MS = 1000;

const I18N = {
  en: {
    header: "Dashboard Rotator",
    runtimeNotFound: "Dashboard Rotator runtime sensor not found.",
    status: "Status",
    dashboard: "Dashboard",
    thisBrowserClient: "This browser client",
    rotatorEnabled: "Rotator enabled",
    addToTargets: "Add to targets",
    removeFromTargets: "Remove from targets",
    alreadyTarget: "Already targeted",
    clearTargets: "Clear targets",
    targetBadge: "Target",
    currentBadge: "This browser",
    activeBadge: "Active",
    switchEntityNotResolved: "switch entity not resolved",
    targetClient: "Target client",
    allClients: "all clients",
    cardCommandTarget: "Card command target",
    activeClient: "Active client",
    clients: "Clients",
    current: "Current",
    next: "Next",
    remaining: "Remaining",
    visible: "Visible",
    pause: "Pause",
    resume: "Resume",
    prev: "Prev",
    nextButton: "Next",
    lastUpdate: "Last update",
    setAlias: "Set alias",
    aliasPrompt: "Alias for {clientId}",
    id: "id",
    title: "title",
    updated: "updated",
    currentLabel: "current",
    nextLabel: "next",
    remainingLabel: "remaining",
    visibleLabel: "visible",
    trueText: "Yes",
    falseText: "No",
    statusLabels: {
      disabled: "Disabled",
      running: "Running",
      navigating: "Navigating",
      interaction_pause: "Paused by interaction",
      manual_pause: "Paused manually",
      waiting_start: "Waiting to start",
      not_targeted: "Not targeted",
      hidden: "Hidden",
      target_unavailable: "Target unavailable",
      idle: "Idle",
      no_views: "No views"
    }
  },
  zhHant: {
    header: "儀表板輪播",
    runtimeNotFound: "找不到 Dashboard Rotator runtime 感測器。",
    status: "狀態",
    dashboard: "儀表板",
    thisBrowserClient: "這個瀏覽器的 client",
    rotatorEnabled: "輪播啟用",
    addToTargets: "加入 target",
    removeFromTargets: "移出 target",
    alreadyTarget: "已在 target 內",
    clearTargets: "清除 target",
    targetBadge: "Target",
    currentBadge: "這個瀏覽器",
    activeBadge: "作用中",
    switchEntityNotResolved: "無法解析對應的 switch entity",
    targetClient: "目標 client",
    allClients: "全部 client",
    cardCommandTarget: "卡片命令目標",
    activeClient: "目前作用 client",
    clients: "Client 數",
    current: "目前頁面",
    next: "下一頁",
    remaining: "剩餘秒數",
    visible: "可見",
    pause: "暫停",
    resume: "恢復",
    prev: "上一頁",
    nextButton: "下一頁",
    lastUpdate: "最後更新",
    setAlias: "設定別名",
    aliasPrompt: "為 {clientId} 設定別名",
    id: "ID",
    title: "頁面標題",
    updated: "更新時間",
    currentLabel: "目前",
    nextLabel: "下一個",
    remainingLabel: "剩餘",
    visibleLabel: "可見",
    trueText: "是",
    falseText: "否",
    statusLabels: {
      disabled: "已停用",
      running: "執行中",
      navigating: "切換中",
      interaction_pause: "互動暫停",
      manual_pause: "手動暫停",
      waiting_start: "等待開始",
      not_targeted: "非目標 client",
      hidden: "頁面隱藏",
      target_unavailable: "目標 client 未連線",
      idle: "待命",
      no_views: "沒有可用頁面"
    }
  }
};

const getUiStrings = () => {
  const lang = String(document.documentElement?.lang || navigator.language || "").toLowerCase();
  if (lang.startsWith("zh-hant") || lang.startsWith("zh-tw") || lang.startsWith("zh-hk") || lang.startsWith("zh-mo") || lang === "zh") {
    return I18N.zhHant;
  }
  return I18N.en;
};

const normalizeSortText = (value) => String(value || '').trim().toLowerCase();

const stableClientSort = (clients, targetClientIds, currentBrowserClientId) => {
  const targetIndex = new Map((targetClientIds || []).map((clientId, index) => [clientId, index]));
  return [...clients].sort((a, b) => {
    const aIsTarget = targetIndex.has(a.client_id);
    const bIsTarget = targetIndex.has(b.client_id);
    if (aIsTarget !== bIsTarget) return aIsTarget ? -1 : 1;
    if (aIsTarget && bIsTarget) {
      return (targetIndex.get(a.client_id) ?? 9999) - (targetIndex.get(b.client_id) ?? 9999);
    }

    const aIsCurrent = a.client_id === currentBrowserClientId;
    const bIsCurrent = b.client_id === currentBrowserClientId;
    if (aIsCurrent !== bIsCurrent) return aIsCurrent ? -1 : 1;

    const aLabel = normalizeSortText(a.display_name || a.page_title || a.client_id);
    const bLabel = normalizeSortText(b.display_name || b.page_title || b.client_id);
    if (aLabel !== bLabel) return aLabel.localeCompare(bLabel);

    return normalizeSortText(a.client_id).localeCompare(normalizeSortText(b.client_id));
  });
};

const normalizePath = (value) => {
  const raw = String(value || "").split("?", 1)[0].split("#", 1)[0].trim();
  if (!raw) return "";
  const prefixed = raw.startsWith("/") ? raw : `/${raw}`;
  return prefixed.replace(/\/+$/, "") || "/";
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

class DashboardRotatorController {
  constructor() {
    this._lastCommandSeq = 0;
    this._lastReportKey = "";
    this._lastReportAt = 0;
    this._viewStartedAt = 0;
    this._viewStartPath = "";
    this._dashboardEnteredAt = 0;
    this._manualPauseUntil = 0;
    this._commandPause = false;
    this._clientId = this._ensureClientId();

    this._boundTick = this.tick.bind(this);
    this._boundInteraction = this.handleInteraction.bind(this);

    window.addEventListener("pointerdown", this._boundInteraction, true);
    window.addEventListener("keydown", this._boundInteraction, true);
    window.addEventListener("touchstart", this._boundInteraction, true);
    document.addEventListener("visibilitychange", this._boundTick);
    window.setInterval(this._boundTick, TICK_MS);
    window.setTimeout(this._boundTick, 1500);
  }

  _ensureClientId() {
    try {
      const existing = window.sessionStorage.getItem("dashboard_rotator_client_id");
      if (existing) return existing;
      const created = `dr-${Math.random().toString(36).slice(2, 10)}`;
      window.sessionStorage.setItem("dashboard_rotator_client_id", created);
      return created;
    } catch (_err) {
      return `dr-${Math.random().toString(36).slice(2, 10)}`;
    }
  }

  getHass() {
    return document.querySelector("home-assistant")?.hass || null;
  }

  findRuntimeState(hass) {
    if (!hass?.states) return null;
    return Object.values(hass.states).find(
      (stateObj) =>
        stateObj?.attributes?.integration_domain === DOMAIN &&
        stateObj?.attributes?.entity_role === RUNTIME_ROLE
    ) || null;
  }

  getManagedViews(profile) {
    return Array.isArray(profile?.views)
      ? profile.views.filter((view) => view && view.enabled !== false && view.path)
      : [];
  }

  getCurrentPath() {
    return normalizePath(window.location.pathname);
  }

  findCurrentIndex(path, views) {
    return views.findIndex((view) => normalizePath(view.path) === path);
  }

  isOnManagedDashboard(path, profile) {
    const dashboardPath = normalizePath(profile?.dashboard_path);
    if (!dashboardPath) return false;
    return path === dashboardPath || path.startsWith(`${dashboardPath}/`);
  }

  getSecondsForView(view, profile) {
    return Math.max(1, Number(view?.seconds || profile?.default_interval || 15));
  }

  getTargetClientIds(profile) {
    if (Array.isArray(profile?.target_client_ids)) {
      return profile.target_client_ids.map((value) => String(value || "").trim()).filter(Boolean);
    }
    const single = String(profile?.target_client_id || "").trim();
    return single ? [single] : [];
  }

  isTargetClient(profile) {
    const targetClientIds = this.getTargetClientIds(profile);
    return !targetClientIds.length || targetClientIds.includes(this._clientId);
  }

  async navigateTo(path) {
    const target = normalizePath(path);
    if (!target || target === this.getCurrentPath()) return;
    try {
      window.history.pushState(null, "", target);
      window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
    } catch (_err) {
      window.location.assign(target);
      return;
    }
    this._viewStartPath = target;
    this._viewStartedAt = Date.now();
    await sleep(50);
  }

  handleInteraction() {
    const hass = this.getHass();
    const runtime = this.findRuntimeState(hass);
    const profile = runtime?.attributes?.profile;
    if (!profile) return;

    const path = this.getCurrentPath();
    if (!this.isOnManagedDashboard(path, profile)) return;

    const seconds = Number(profile.pause_on_interaction || 0);
    if (seconds <= 0) return;
    this._manualPauseUntil = Date.now() + (seconds * 1000);
    this.tick();
  }

  async handleCommand(command, profile, currentPath, views) {
    const seq = Number(command?.seq || 0);
    if (!seq || seq === this._lastCommandSeq) return false;
    const profileTargetClientIds = this.getTargetClientIds(profile);
    if (profileTargetClientIds.length && !profileTargetClientIds.includes(this._clientId)) return false;
    const targetClientId = String(command?.target_client_id || "").trim();
    if (targetClientId && targetClientId !== this._clientId) return false;
    this._lastCommandSeq = seq;

    const name = command?.name;
    if (name === "pause") {
      this._commandPause = true;
      return true;
    }
    if (name === "resume") {
      this._commandPause = false;
      this._manualPauseUntil = 0;
      return true;
    }
    if (!views.length) return false;

    const currentIndex = this.findCurrentIndex(currentPath, views);
    if (name === "next_view") {
      const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % views.length : 0;
      await this.navigateTo(views[nextIndex].path);
      return true;
    }
    if (name === "previous_view") {
      const previousIndex = currentIndex >= 0 ? (currentIndex - 1 + views.length) % views.length : views.length - 1;
      await this.navigateTo(views[previousIndex].path);
      return true;
    }
    if (name === "jump_to_view") {
      const target = normalizePath(command?.view_path);
      if (target) {
        await this.navigateTo(target);
        return true;
      }
    }

    return false;
  }

  async reportState(hass, payload) {
    if (!hass) return;
    const report = {
      ...payload,
      page_title: payload.page_title ?? document.title ?? null,
    };
    const key = JSON.stringify(report);
    const now = Date.now();
    if (key === this._lastReportKey && (now - this._lastReportAt) < REPORT_INTERVAL_MS) {
      return;
    }
    this._lastReportKey = key;
    this._lastReportAt = now;
    try {
      await hass.callService(DOMAIN, "client_state", report);
    } catch (err) {
      console.debug("Dashboard Rotator client_state report failed", err);
    }
  }

  async tick() {
    const hass = this.getHass();
    const runtime = this.findRuntimeState(hass);
    if (!hass || !runtime) return;

    const attrs = runtime.attributes || {};
    const profile = attrs.profile || null;
    const command = attrs.command || null;
    const path = this.getCurrentPath();

    if (!profile) return;

    const visible = document.visibilityState === "visible";
    const views = this.getManagedViews(profile);
    const onManagedDashboard = this.isOnManagedDashboard(path, profile);
    const isTargetClient = this.isTargetClient(profile);
    await this.handleCommand(command, profile, path, views);

    if (!profile.enabled) {
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "disabled",
        current_view: path,
        next_view: null,
        remaining_seconds: null,
        page_visible: visible,
        on_managed_dashboard: onManagedDashboard,
      });
      return;
    }

    if (!onManagedDashboard) {
      this._dashboardEnteredAt = 0;
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "idle",
        current_view: path,
        next_view: null,
        remaining_seconds: null,
        page_visible: visible,
        on_managed_dashboard: false,
      });
      return;
    }

    if (!isTargetClient) {
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "not_targeted",
        current_view: path,
        next_view: null,
        remaining_seconds: null,
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    if (!views.length) {
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "no_views",
        current_view: path,
        next_view: null,
        remaining_seconds: null,
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    if (profile.only_when_visible && !visible) {
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "hidden",
        current_view: path,
        next_view: null,
        remaining_seconds: null,
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    const now = Date.now();
    const currentIndex = this.findCurrentIndex(path, views);

    if (currentIndex === -1) {
      if (!this._dashboardEnteredAt) this._dashboardEnteredAt = now;
      const waitMs = Math.max(0, Number(profile.start_delay || 0) * 1000);
      const remaining = Math.max(0, Math.ceil((waitMs - (now - this._dashboardEnteredAt)) / 1000));
      const firstView = views[0];
      if (waitMs === 0 || now - this._dashboardEnteredAt >= waitMs) {
        await this.navigateTo(firstView.path);
      }
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "waiting_start",
        current_view: path,
        next_view: firstView?.path || null,
        remaining_seconds: remaining,
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    this._dashboardEnteredAt = 0;
    const currentView = views[currentIndex];
    const nextView = views[(currentIndex + 1) % views.length];

    if (this._viewStartPath !== path) {
      this._viewStartPath = path;
      this._viewStartedAt = now;
    }

    if (this._commandPause) {
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "manual_pause",
        current_view: currentView.path,
        next_view: nextView.path,
        remaining_seconds: null,
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    if (this._manualPauseUntil > now) {
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "interaction_pause",
        current_view: currentView.path,
        next_view: nextView.path,
        remaining_seconds: Math.ceil((this._manualPauseUntil - now) / 1000),
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    const intervalMs = this.getSecondsForView(currentView, profile) * 1000;
    const elapsedMs = now - this._viewStartedAt;
    const remainingSeconds = Math.max(0, Math.ceil((intervalMs - elapsedMs) / 1000));

    if (elapsedMs >= intervalMs) {
      await this.navigateTo(nextView.path);
      await this.reportState(hass, {
        client_id: this._clientId,
        status: "navigating",
        current_view: currentView.path,
        next_view: nextView.path,
        remaining_seconds: 0,
        page_visible: visible,
        on_managed_dashboard: true,
      });
      return;
    }

    await this.reportState(hass, {
      client_id: this._clientId,
      status: "running",
      current_view: currentView.path,
      next_view: nextView.path,
      remaining_seconds: remainingSeconds,
      page_visible: visible,
      on_managed_dashboard: true,
    });
  }
}

class DashboardRotatorStatusCard extends HTMLElement {
  static getConfigElement() {
    return null;
  }

  getEnabledEntityId(runtime) {
    const explicit = String(this._config?.enabled_entity || "").trim();
    if (explicit) return explicit;
    const runtimeEntityId = String(runtime?.entity_id || this._config?.entity || "").trim();
    if (runtimeEntityId.startsWith("sensor.") && runtimeEntityId.endsWith("_runtime")) {
      return runtimeEntityId.replace(/^sensor\./, "switch.").replace(/_runtime$/, "_enabled");
    }
    return "";
  }

  t(key) {
    return (this._strings || I18N.en)[key] || I18N.en[key] || key;
  }

  formatBool(value) {
    if (value === null || value === undefined || value === "") return "-";
    return value ? this.t("trueText") : this.t("falseText");
  }

  formatStatus(value) {
    if (!value) return "-";
    return this._strings?.statusLabels?.[value] || I18N.en.statusLabels?.[value] || value;
  }

  setConfig(config) {
    this._config = config || {};
    this._strings = getUiStrings();
    this._expandedClientIds = this._expandedClientIds || new Set();
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => {
        const el = ev.target?.closest?.("[data-action]") || ev.target;
        const action = el?.dataset?.action;
        if (!action || !this._hass) return;
        if (action === "toggle_enabled") return;
        const targetClientId = String(this._config?.target_client_id || "").trim();
        const data = targetClientId ? { target_client_id: targetClientId } : {};
        if (action === "alias" && el.dataset.clientId) {
          const clientId = el.dataset.clientId;
          const currentAlias = el.dataset.alias || "";
          const alias = window.prompt(this.t("aliasPrompt").replace("{clientId}", clientId), currentAlias);
          if (alias === null) return;
          this._hass.callService(DOMAIN, "set_client_alias", { client_id: clientId, alias });
          return;
        }
        if (action === "add_target_current" && el.dataset.clientId) {
          this._hass.callService(DOMAIN, "set_target_client", { target_client_id: el.dataset.clientId, append: true });
          return;
        }
        if (action === "remove_target" && el.dataset.clientId) {
          this._hass.callService(DOMAIN, "set_target_client", { target_client_id: el.dataset.clientId, remove: true });
          return;
        }
        if (action === "clear_targets") {
          this._hass.callService(DOMAIN, "set_target_client", {});
          return;
        }
        if (action === "jump" && el.dataset.path) {
          this._hass.callService(DOMAIN, "jump_to_view", { ...data, path: el.dataset.path });
          return;
        }
        this._hass.callService(DOMAIN, action, data);
      });
      this.shadowRoot.addEventListener("change", (ev) => {
        const el = ev.target?.closest?.("[data-action='toggle_enabled']") || ev.target;
        if (!this._hass || el?.dataset?.action !== "toggle_enabled" || !el.dataset.entityId) return;
        const entityId = el.dataset.entityId;
        const checked = !!el.checked;
        this._hass.callService("switch", checked ? "turn_on" : "turn_off", { entity_id: entityId });
      });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._strings = getUiStrings();
    this.render();
  }

  getCardSize() {
    return 3;
  }

  findRuntime() {
    if (!this._hass?.states) return null;
    if (this._config?.entity && this._hass.states[this._config.entity]) {
      return this._hass.states[this._config.entity];
    }
    return Object.values(this._hass.states).find(
      (stateObj) =>
        stateObj?.attributes?.integration_domain === DOMAIN &&
        stateObj?.attributes?.entity_role === RUNTIME_ROLE
    ) || null;
  }

  isClientExpanded(clientId, activeClientId, targetClientIds, currentBrowserClientId) {
    if (this._expandedClientIds?.has(clientId)) return true;
    return clientId === activeClientId || clientId === currentBrowserClientId || targetClientIds.includes(clientId);
  }

  render() {
    if (!this.shadowRoot) return;
    const runtime = this.findRuntime();
    if (!runtime) {
      this.shadowRoot.innerHTML = `<ha-card><div class="pad">${this.t("runtimeNotFound")}</div></ha-card>`;
      return;
    }

    const attrs = runtime.attributes || {};
    const profile = attrs.profile || {};
    const client = attrs.client_state || {};
    const clientStates = attrs.client_states || {};
    const activeClientId = attrs.active_client_id || null;
    const activeClientAlias = attrs.active_client_alias || null;
    const targetClientIds = Array.isArray(attrs.target_client_ids)
      ? attrs.target_client_ids
      : (Array.isArray(profile.target_client_ids) ? profile.target_client_ids : (attrs.target_client_id || profile.target_client_id ? [attrs.target_client_id || profile.target_client_id] : []));
    const currentBrowserClientId = window.dashboardRotatorController?._clientId || window.sessionStorage?.getItem?.("dashboard_rotator_client_id") || null;
    const enabledEntityId = this.getEnabledEntityId(runtime);
    const enabledState = enabledEntityId ? this._hass?.states?.[enabledEntityId]?.state : null;
    const enabledKnown = enabledState === "on" || enabledState === "off";
    const views = Array.isArray(profile.views) ? profile.views.filter((view) => view.enabled !== false) : [];
    const clients = stableClientSort(Object.values(clientStates), targetClientIds, currentBrowserClientId);

    this.shadowRoot.innerHTML = `
      <style>
        .pad { padding: 16px; }
        .row { display:flex; justify-content:space-between; gap:8px; margin: 6px 0; }
        .buttons { display:flex; gap:8px; flex-wrap:wrap; margin-top: 12px; }
        button { border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); border-radius: 8px; padding: 8px 10px; cursor: pointer; }
        .chips { display:flex; gap:8px; flex-wrap:wrap; margin-top: 12px; }
        .chip { border: 1px solid var(--divider-color); border-radius: 999px; padding: 4px 10px; font-size: 12px; }
        .role-badges { display:flex; gap:6px; flex-wrap:wrap; margin-top:6px; }
        .role-badge { border-radius:999px; padding: 2px 8px; font-size:11px; font-weight:600; line-height:1.4; border:1px solid var(--divider-color); }
        .role-badge.target { border-color: var(--warning-color, #ff9800); color: var(--warning-color, #ff9800); }
        .role-badge.current { border-color: var(--info-color, #2196f3); color: var(--info-color, #2196f3); }
        .role-badge.active { border-color: var(--success-color, #4caf50); color: var(--success-color, #4caf50); }
        .muted { color: var(--secondary-text-color); }
        .client-list { margin-top: 12px; display:grid; gap:8px; }
        .client-item { border: 1px solid var(--divider-color); border-radius: 10px; }
        .client-item.active { border-color: var(--primary-color); }
        .client-head { display:flex; justify-content:space-between; gap:8px; font-weight:600; list-style:none; cursor:pointer; padding: 10px; align-items:flex-start; }
        .client-head::-webkit-details-marker { display:none; }
        .client-title { min-width:0; }
        .client-body { padding: 0 10px 10px; }
        .tiny { font-size: 12px; color: var(--secondary-text-color); }
        .switch-row { display:flex; justify-content:space-between; align-items:center; gap:12px; margin: 6px 0; }
        .switch-meta { display:flex; flex-direction:column; gap:2px; }
        .switch-title { font-weight:600; }
        .switch-subtitle { font-size:12px; color: var(--secondary-text-color); }
        ha-switch[disabled] { opacity: 0.5; }
      </style>
      <ha-card header="${this.t("header")}">
        <div class="pad">
          <div class="row"><strong>${this.t("status")}</strong><span>${this.formatStatus(runtime.state)}</span></div>
          <div class="row"><strong>${this.t("dashboard")}</strong><span>${profile.dashboard_path || "-"}</span></div>
          <div class="row"><strong>${this.t("thisBrowserClient")}</strong><span>${currentBrowserClientId || "-"}</span></div>
          ${(currentBrowserClientId || targetClientIds.length) ? `<div class="buttons" style="margin-top:6px;">
            ${currentBrowserClientId ? `<button data-action="add_target_current" data-client-id="${currentBrowserClientId}" ${targetClientIds.includes(currentBrowserClientId) ? 'disabled' : ''}>${targetClientIds.includes(currentBrowserClientId) ? this.t("alreadyTarget") : this.t("addToTargets")}</button>` : ''}
            ${targetClientIds.length ? `<button data-action="clear_targets">${this.t("clearTargets")}</button>` : ''}
          </div>` : ''}
          <div class="switch-row">
            <div class="switch-meta">
              <span class="switch-title">${this.t("rotatorEnabled")}</span>
              <span class="switch-subtitle">${enabledEntityId || this.t("switchEntityNotResolved")}</span>
            </div>
            <ha-switch data-action="toggle_enabled" data-entity-id="${enabledEntityId}" ${enabledKnown && enabledState === 'on' ? 'checked' : ''} ${enabledEntityId ? '' : 'disabled'}></ha-switch>
          </div>
          <div class="row"><strong>${this.t("targetClient")}</strong><span>${targetClientIds.length ? '' : this.t("allClients")}</span></div>
          ${targetClientIds.length ? `<div class="chips" style="margin-top:6px;">${targetClientIds.map((clientId) => `<span class="chip">🎯 ${clientId}</span>`).join('')}</div>` : ''}
          ${this._config?.target_client_id ? `<div class="row"><strong>${this.t("cardCommandTarget")}</strong><span>${this._config.target_client_id}</span></div>` : ''}
          <div class="row"><strong>${this.t("activeClient")}</strong><span>${activeClientAlias ? `${activeClientAlias} (${activeClientId || '-'})` : (activeClientId || "-")}</span></div>
          <div class="row"><strong>${this.t("clients")}</strong><span>${clients.length}</span></div>
          <div class="row"><strong>${this.t("current")}</strong><span>${client.current_view || "-"}</span></div>
          <div class="row"><strong>${this.t("next")}</strong><span>${client.next_view || "-"}</span></div>
          <div class="row"><strong>${this.t("remaining")}</strong><span>${client.remaining_seconds ?? "-"}</span></div>
          <div class="row"><strong>${this.t("visible")}</strong><span>${this.formatBool(client.page_visible)}</span></div>
          <div class="buttons">
            <button data-action="pause">${this.t("pause")}</button>
            <button data-action="resume">${this.t("resume")}</button>
            <button data-action="previous_view">${this.t("prev")}</button>
            <button data-action="next_view">${this.t("nextButton")}</button>
          </div>
          <div class="chips">
            ${views.map((view) => `<button class="chip" data-action="jump" data-path="${view.path}">${view.title || view.path}</button>`).join("")}
          </div>
          <div class="client-list">
            ${clients.map((item) => `
              <details class="client-item ${item.client_id === activeClientId ? 'active' : ''}" data-client-id="${item.client_id || ''}" ${this.isClientExpanded(item.client_id, activeClientId, targetClientIds, currentBrowserClientId) ? 'open' : ''}>
                <summary class="client-head">
                  <div class="client-title">
                    <div>${item.display_name || item.client_id || '-'}</div>
                    <div class="role-badges">
                      ${targetClientIds.includes(item.client_id) ? `<span class="role-badge target">🎯 ${this.t("targetBadge")}</span>` : ''}
                      ${item.client_id === currentBrowserClientId ? `<span class="role-badge current">🖥️ ${this.t("currentBadge")}</span>` : ''}
                      ${item.client_id === activeClientId ? `<span class="role-badge active">✅ ${this.t("activeBadge")}</span>` : ''}
                    </div>
                  </div>
                  <span>${this.formatStatus(item.status)}</span>
                </summary>
                <div class="client-body">
                <div class="tiny">${this.t("id")}: ${item.client_id || '-'}</div>
                <div class="tiny">${this.t("currentLabel")}: ${item.current_view || '-'} | ${this.t("nextLabel")}: ${item.next_view || '-'}</div>
                <div class="tiny">${this.t("remainingLabel")}: ${item.remaining_seconds ?? '-'} | ${this.t("visibleLabel")}: ${this.formatBool(item.page_visible)}</div>
                <div class="tiny">${this.t("title")}: ${item.page_title || '-'}</div>
                <div class="tiny">${this.t("updated")}: ${item.updated_at || '-'}</div>
                <div class="buttons" style="margin-top:8px;">
                  <button data-action="alias" data-client-id="${item.client_id || ''}" data-alias="${item.client_alias || ''}">${this.t("setAlias")}</button>
                  ${targetClientIds.includes(item.client_id)
                    ? `<button data-action="remove_target" data-client-id="${item.client_id || ''}">${this.t("removeFromTargets")}</button>`
                    : `<button data-action="add_target_current" data-client-id="${item.client_id || ''}">${this.t("addToTargets")}</button>`}
                </div>
                </div>
              </details>
            `).join('')}
          </div>
          <div class="muted" style="margin-top:12px;">${this.t("lastUpdate")}: ${client.updated_at || "-"}</div>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll('details.client-item[data-client-id]').forEach((el) => {
      el.addEventListener('toggle', () => {
        const clientId = String(el.dataset.clientId || '');
        if (!clientId) return;
        if (el.open) this._expandedClientIds.add(clientId);
        else this._expandedClientIds.delete(clientId);
      });
    });
  }
}

window.DashboardRotatorStatusCard = DashboardRotatorStatusCard;

if (!customElements.get("dashboard-rotator-status")) {
  customElements.define("dashboard-rotator-status", DashboardRotatorStatusCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "dashboard-rotator-status",
  name: "Dashboard Rotator Status",
  description: "Status and control card for Dashboard Rotator",
  preview: true,
  documentationURL: "https://github.com/ivanlee1007/ha-dashboard-rotator",
});

window.dashboardRotatorController = window.dashboardRotatorController || new DashboardRotatorController();
