(() => {
"use strict";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const ERA_NAMES = {original:"Original",neo:"Neo",e:"e-Card",ADV:"ADV",PCG:"PCG",DP:"Diamond & Pearl",DPt:"Platinum",LEGEND:"LEGEND",BW:"Black & White",XY:"XY",SM:"Sun & Moon",S:"Sword & Shield",SV:"Scarlet & Violet",M:"Mega Evolution"};
const fold = value => String(value ?? "").normalize("NFKC").toLocaleLowerCase();

// Shared legacy view parameters remain readable; the calendar always shows artwork.
function normalizeState(input, context) {
  const min = Math.min(...context.years), max = Math.max(...context.years);
  const year = (value, fallback) => /^\d{4}$/.test(String(value ?? "")) ? Math.max(min, Math.min(max, Number(value))) : fallback;
  let from = year(input.from, min), to = year(input.to, max);
  if (from > to) [from, to] = [to, from];
  return {
    q: String(input.q ?? "").trim().slice(0, 200),
    era: context.eras.includes(input.era) ? input.era : "",
    from, to, view: "artwork"
  };
}

function readState(search, context) {
  const params = new URLSearchParams(search);
  return normalizeState(Object.fromEntries(["q", "era", "from", "to", "view"].map(key => [key, params.get(key)])), context);
}

function writeState(state, currentUrl, context) {
  const url = new URL(currentUrl);
  const defaults = normalizeState({}, context);
  for (const key of ["q", "era", "from", "to", "view"]) {
    if (state[key] === defaults[key]) url.searchParams.delete(key);
    else url.searchParams.set(key, String(state[key]));
  }
  return url;
}

function filterSets(sets, state) {
  const query = fold(state.q);
  return sets.filter(set => set.year >= state.from && set.year <= state.to && (!state.era || set.era === state.era) &&
    (!query || fold(`${set.name} ${set.code} ${set.era} ${ERA_NAMES[set.era] || ""}`).includes(query)));
}

function resolveSitePath(path, siteRoot) {
  if (!path.startsWith("/") || path.startsWith("//")) return new URL(path, siteRoot).href;
  const url = new URL(path.slice(1), siteRoot);
  if (url.pathname.endsWith("/")) url.pathname += "index.html";
  return url.href;
}

function initializeTimeline(root, siteRoot) {
  const {sets} = JSON.parse(root.querySelector("#timeline-data").textContent);
  if (!Array.isArray(sets) || !sets.length) return;
  const context = {years: [...new Set(sets.map(set => set.year))].sort((a,b) => a-b), eras: [...new Set(sets.map(set => set.era))]};
  const byId = new Map(sets.map(set => [set.id, set]));
  const form = root.querySelector(".timeline-filters");
  const chart = root.querySelector("[data-timeline-chart]");
  const table = chart.querySelector("table");
  const empty = root.querySelector("[data-timeline-empty]");
  const status = root.querySelector("#timeline-status");
  const packs = [...chart.querySelectorAll("[data-set-id]")];
  const rows = [...chart.querySelectorAll("tbody tr")];
  const dialog = root.querySelector("[data-set-dialog]");
  let state = readState(location.search, context);
  let opener = null, searchTimer;

  // Horizontal overflow prevents native sticky headers from following page scroll.
  // A small, non-interactive copy keeps month labels aligned without a vertical scroll box.
  const floating = document.createElement("div");
  floating.className = "timeline-floating-months";
  floating.setAttribute("aria-hidden", "true");
  floating.hidden = true;
  const floatingTable = document.createElement("table");
  floatingTable.className = "timeline-table";
  floatingTable.append(table.tHead.cloneNode(true));
  floating.append(floatingTable);
  root.append(floating);
  let framePending = false;
  function positionMonths() {
    framePending = false;
    const rect = chart.getBoundingClientRect();
    const header = document.querySelector(".site-header, .header");
    const headerPosition = header ? getComputedStyle(header).position : "static";
    const headerRect = header?.getBoundingClientRect();
    const top = headerRect && ["fixed", "sticky"].includes(headerPosition) && headerRect.top <= 0 ? Math.max(0, headerRect.bottom) : 0;
    const height = table.tHead.getBoundingClientRect().height;
    floating.hidden = chart.hidden || rect.top >= top || rect.bottom < top + height;
    if (floating.hidden) return;
    Object.assign(floating.style, {left:`${rect.left}px`, top:`${top}px`, width:`${chart.clientWidth}px`, height:`${height}px`});
    floatingTable.style.width = `${table.getBoundingClientRect().width}px`;
    floatingTable.style.transform = `translateX(${-chart.scrollLeft}px)`;
    floatingTable.rows[0].cells[0].style.transform = `translateX(${chart.scrollLeft}px)`;
  }
  function scheduleMonths() {
    if (!framePending) { framePending = true; requestAnimationFrame(positionMonths); }
  }
  window.addEventListener("scroll", scheduleMonths, {passive:true});
  window.addEventListener("resize", scheduleMonths);
  chart.addEventListener("scroll", scheduleMonths, {passive:true});
  window.addEventListener("beforeprint", () => {
    for (const image of chart.querySelectorAll("img")) image.loading = "eager";
  });
  window.addEventListener("afterprint", () => {
    for (const image of chart.querySelectorAll("img")) image.loading = "lazy";
  });

  function render(preserveSearchInput = false) {
    const filtered = filterSets(sets, state);
    const ids = new Set(filtered.map(set => set.id));
    const visibleYears = new Set(filtered.map(set => set.year));
    for (const pack of packs) pack.hidden = !ids.has(pack.dataset.setId);
    for (const row of rows) row.hidden = !visibleYears.has(Number(row.dataset.year));
    chart.hidden = !filtered.length;
    empty.hidden = filtered.length > 0;
    status.textContent = `${filtered.length} ${filtered.length === 1 ? "set" : "sets"} · ${visibleYears.size} ${visibleYears.size === 1 ? "year" : "years"}${filtered.length !== sets.length ? ` · ${sets.length} total` : ""}`;
    root.querySelector(".timeline-scroll-hint").hidden = !filtered.length;
    for (const key of ["q", "era", "from", "to"]) {
      if (key !== "q" || !preserveSearchInput) form.elements.namedItem(key).value = state[key];
    }
    scheduleMonths();
  }

  function update(next, preserveSearchInput = false) {
    state = normalizeState({...state, ...next}, context);
    const url = writeState(state, location.href, context);
    if (url.href !== location.href) history.pushState(null, "", url);
    render(preserveSearchInput);
  }

  function reset() {
    clearTimeout(searchTimer);
    update(normalizeState({}, context));
  }

  const searchInput = form.elements.namedItem("q");
  form.addEventListener("submit", event => {
    event.preventDefault();
    clearTimeout(searchTimer);
    update({q:searchInput.value});
  });
  form.addEventListener("change", event => {
    clearTimeout(searchTimer);
    if (event.target.name) update({[event.target.name]:event.target.value, q:searchInput.value});
  });
  searchInput.addEventListener("compositionstart", () => clearTimeout(searchTimer));
  searchInput.addEventListener("input", event => {
    clearTimeout(searchTimer);
    if (event.isComposing) return;
    const value = event.target.value;
    searchTimer = setTimeout(() => update({q:value}, true), 180);
  });
  searchInput.addEventListener("compositionend", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => update({q:searchInput.value}, true), 180);
  });
  form.addEventListener("reset", event => { event.preventDefault(); reset(); });
  root.querySelector("[data-reset-filters]").addEventListener("click", () => { reset(); searchInput.focus(); });
  root.querySelector("[data-copy-link]")?.addEventListener("click", () => {
    clearTimeout(searchTimer);
    update({q:searchInput.value});
  }, {capture:true});
  window.addEventListener("popstate", () => { clearTimeout(searchTimer); state = readState(location.search, context); render(); });

  root.addEventListener("click", event => {
    const link = event.target.closest("a[data-set-id]");
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0 || typeof dialog.showModal !== "function") return;
    const set = byId.get(link.dataset.setId);
    if (!set) return;
    event.preventDefault();
    opener = link;
    const image = document.createElement("img");
    image.alt = set.name;
    image.decoding = "async";
    image.src = resolveSitePath(set.image, siteRoot);
    root.querySelector("[data-dialog-art]").replaceChildren(image);
    root.querySelector("#timeline-dialog-title").textContent = set.name;
    root.querySelector("[data-dialog-era]").textContent = ERA_NAMES[set.era] || set.era;
    root.querySelector("[data-dialog-date]").textContent = `${MONTHS[set.month-1]} ${set.year}`;
    const source = root.querySelector("[data-dialog-source]");
    source.hidden = !set.url;
    if (set.url) source.href = set.url;
    else source.removeAttribute("href");
    root.querySelector("[data-dialog-no-source]").hidden = Boolean(set.url);
    root.querySelector("[data-dialog-original]").href = image.src;
    dialog.showModal();
    root.querySelector("[data-dialog-close]").focus();
  });
  root.querySelector("[data-dialog-close]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog.addEventListener("close", () => {
    root.querySelector("[data-dialog-art]").replaceChildren();
    if (opener?.isConnected && !opener.hidden) opener.focus();
  });

  render();
  if (typeof dialog.showModal === "function") packs.forEach(pack => pack.setAttribute("aria-haspopup", "dialog"));
  for (const controls of root.querySelectorAll("[data-timeline-controls]")) controls.hidden = false;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {normalizeState, readState, writeState, filterSets, resolveSitePath};
}
if (typeof document !== "undefined") {
  const root = document.querySelector("[data-timeline]");
  if (root) initializeTimeline(root, new URL("../../", document.currentScript.src));
}
})();
