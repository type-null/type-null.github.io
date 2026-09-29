// Run with `node tests/timeline.test.mjs`; no npm dependencies are required.
import assert from "node:assert/strict";
import {readFile, access} from "node:fs/promises";
import {createRequire} from "node:module";

const data = JSON.parse(await readFile(new URL("../content/_data/card-sets.json", import.meta.url), "utf8"));
const require = createRequire(import.meta.url);
const helpers = require("../assets/js/timeline.js");
const {filterSets, writeState, resolveSitePath} = helpers;
// Some sandboxed runners load CommonJS in a separate realm; compare state values,
// including all own keys and strict value types, without coupling their prototypes.
const normalizeState = (...args) => ({...helpers.normalizeState(...args)});
const readState = (...args) => ({...helpers.readState(...args)});
// Stable helper fixtures must not restrict later editorial additions to the archive.
const context = {years: [1996, 2023, 2024, 2025, 2026], eras: ["original", "S", "SV", "M"]};
const defaults = {q: "", era: "", from: 1996, to: 2026, view: "artwork"};
const archiveContext = {years: data.years, eras: data.eras.map(era => era.id)};
const archiveDefaults = {...defaults, from: Math.min(...data.years), to: Math.max(...data.years)};
const cases = [];
const check = (name, run) => cases.push({name, run});
const state = input => normalizeState(input, context);
const filtered = input => filterSets(data.sets, normalizeState(input, archiveContext));
const ids = sets => sets.map(set => set.id);

check("archive metadata tracks all current releases and distinct IDs", () => {
  assert.ok(data.sets.length > 0);
  assert.equal(new Set(ids(data.sets)).size, data.sets.length);
  assert.equal(data.metadata.recordCount, data.sets.length);
  assert.deepEqual(data.years, [...new Set(data.sets.map(set => set.year))].sort((a, b) => a - b));
});

check("all actual archive images exist", async () => {
  for (const set of data.sets) {
    assert.ok(set.image.startsWith("/assets/images/"), set.id);
    await access(new URL(`..${set.image}`, import.meta.url));
    assert.ok(Number.isInteger(set.month) && set.month >= 1 && set.month <= 12, set.id);
    assert.ok(archiveContext.years.includes(set.year), set.id);
    assert.ok(archiveContext.eras.includes(set.era), set.id);
  }
});

check("default and empty shared states retain the full archive", () => {
  assert.deepEqual(state({}), defaults);
  assert.deepEqual(readState("", context), defaults);
  assert.deepEqual(readState("", archiveContext), archiveDefaults);
  assert.deepEqual(ids(filtered({})), ids(data.sets));
  const extended = [...data.sets, {id: "future-fixture", name: "Future release", code: "F1", era: "future", year: archiveDefaults.to + 1, month: 1}];
  const extendedContext = {years: [...archiveContext.years, archiveDefaults.to + 1], eras: [...archiveContext.eras, "future"]};
  assert.deepEqual(ids(filterSets(extended, normalizeState({}, extendedContext))), ids(extended));
});

check("years clamp to archive coverage and reversed ranges normalize", () => {
  assert.deepEqual(state({from: "0000", to: "9999"}), defaults);
  assert.deepEqual(state({from: "2026", to: "1996"}), defaults);
  assert.deepEqual(state({from: "2025", to: "2023"}), {...defaults, from: 2023, to: 2025});
  assert.equal(state({from: 2024, to: 2024}).from, 2024);
});

check("malformed years cannot become partial or exponential numbers", () => {
  for (const value of ["2024junk", "2e03", "2024.0", "-2024", " 2024", "2024 ", "Infinity", "NaN", "２０２４", [], {}, null]) {
    assert.deepEqual(state({from: value, to: value}), defaults, String(value));
  }
});

check("known era IDs are accepted and every view retains artwork", () => {
  for (const era of context.eras) assert.equal(state({era}).era, era);
  for (const era of ["sv", "no-era", "__proto__", "<script>", null, {}]) assert.equal(state({era}).era, "");
  assert.equal(state({view: "artwork"}).view, "artwork");
  for (const view of ["overview", "list", "grid", "ARTWORK", "__proto__", null]) {
    assert.equal(state({view}).view, "artwork");
    assert.equal(readState(`?view=${encodeURIComponent(String(view))}`, context).view, "artwork");
  }
});

check("queries trim whitespace and are bounded", () => {
  assert.equal(state({q: "  サイバージャッジ\n"}).q, "サイバージャッジ");
  assert.equal(state({q: "　 \n\t "}).q, "");
  assert.equal(state({q: "a".repeat(300)}).q.length, 200);
  assert.equal(state({q: null}).q, "");
  assert.deepEqual(Object.keys(state({unknown: "ignored"})), Object.keys(defaults));
});

check("malformed URLs normalize into safe finite state", () => {
  assert.deepEqual(readState("?from=NaN&to=Infinity&era=__proto__&view=wat", context), defaults);
  assert.equal(readState("?q=%E0%A4%A", context).q.length > 0, true);
  assert.equal(readState("?q=SM1%2B", context).q, "SM1+");
  assert.equal(readState("?from=2024&from=1996", context).from, 2024);
});

check("real era and year filters cover the current archive", () => {
  for (const era of archiveContext.eras) {
    assert.deepEqual(ids(filtered({era})), ids(data.sets.filter(set => set.era === era)));
  }
  for (const year of archiveContext.years) {
    assert.deepEqual(ids(filtered({from: year, to: year})), ids(data.sets.filter(set => set.year === year)));
  }
  assert.deepEqual(ids(filtered({era: "SV", from: 2024, to: 2024})), ids(data.sets.filter(set => set.era === "SV" && set.year === 2024)));
  const fixture = [
    {id: "a", year: 2023, era: "SV"},
    {id: "b", year: 2024, era: "SV"},
    {id: "c", year: 2024, era: "S"},
    {id: "d", year: 2025, era: "M"}
  ];
  assert.deepEqual(ids(filterSets(fixture, state({era: "SV", from: 2024, to: 2024}))), ["b"]);
  assert.deepEqual(ids(filterSets(fixture, state({era: "M", to: 2024}))), []);
  assert.deepEqual(ids(filterSets(fixture, state({from: 2024, to: 2025}))), ["b", "c", "d"]);
});

check("Japanese, halfwidth Japanese, and fullwidth ASCII searches work", () => {
  assert.ok(ids(filtered({q: "サイバー"})).includes("2024-01-sv-sv5m"));
  assert.deepEqual(ids(filtered({q: "ﾜｲﾙﾄﾞ"})), ids(filtered({q: "ワイルド"})));
  for (const id of ["2024-01-sv-sv5k", "2014-03-xy-xy2"]) assert.ok(ids(filtered({q: "ワイルド"})).includes(id));
  assert.deepEqual(ids(filtered({q: "ＳＶ５"})), ids(filtered({q: "sv5"})));
  for (const id of ["2024-01-sv-sv5k", "2024-01-sv-sv5m", "2024-03-sv-sv5a"]) assert.ok(ids(filtered({q: "sv5"})).includes(id));
});

check("case-insensitive codes, literal plus signs, and era names work", () => {
  assert.ok(ids(filtered({q: "sM1+"})).includes("2017-01-sm-sm1"));
  const swordResults = new Set(ids(filtered({q: "sword & shield"})));
  for (const set of data.sets.filter(set => set.era === "S")) assert.ok(swordResults.has(set.id), set.id);
  assert.equal(filtered({q: "does-not-exist-493023"}).length, 0);
  assert.equal(filtered({q: "   "}).length, data.sets.length);
});

check("paired releases remain separate and have stable IDs", () => {
  const january = filtered({era: "SV", from: 2024, to: 2024}).filter(set => set.month === 1);
  for (const id of ["2024-01-sv-sv5k", "2024-01-sv-sv5m"]) assert.ok(ids(january).includes(id));
  const december = ids(filtered({era: "S", from: 2019, to: 2019}).filter(set => set.month === 12));
  for (const id of ["2019-12-s-s1h", "2019-12-s-s1w"]) assert.ok(december.includes(id));
});

check("filtering does not mutate or reorder the source archive", () => {
  const before = JSON.stringify(data.sets);
  filtered({era: "SV", q: "sv", view: "artwork"});
  filtered({from: 2024, to: 2024, view: "list"});
  assert.equal(JSON.stringify(data.sets), before);
  assert.deepEqual(ids(filtered({})), ids(data.sets));
});

check("shared state and site paths work on HTTPS and local files", () => {
  const expected = state({q: "サイバー + # % & = ?", era: "SV", from: 2023, to: 2025, view: "artwork"});
  for (const root of ["https://example.test/", "https://example.test/subdir/", "file:///Users/example/My%20Site/_site/"]) {
    const current = `${root}card/2024/02/timeline.html`;
    const url = writeState(expected, current, context);
    assert.deepEqual(readState(url.search, context), expected);
    assert.equal(url.pathname, new URL(current).pathname);
    assert.equal(url.protocol, new URL(current).protocol);
    assert.equal(resolveSitePath("/", root), `${root}index.html`);
    assert.equal(resolveSitePath("/card/", root), `${root}card/index.html`);
    assert.equal(resolveSitePath("/card/?q=SV5#calendar", root), `${root}card/index.html?q=SV5#calendar`);
    assert.equal(resolveSitePath("/card/2024/02/timeline.html", root), current);
    assert.equal(resolveSitePath("assets/images/SM1+-key.png", root), `${root}assets/images/SM1+-key.png`);
    const unicode = resolveSitePath("/assets/images/カード art.png", root);
    assert.equal(decodeURIComponent(new URL(unicode).pathname), `${decodeURIComponent(new URL(root).pathname)}assets/images/カード art.png`);
    assert.equal(resolveSitePath("/assets/images/%E3%82%AB%E3%83%BC%E3%83%89%20art.png", root), unicode);
    assert.equal(resolveSitePath("/assets/images/a%23b%25c.png", root), `${root}assets/images/a%23b%25c.png`);
    assert.equal(resolveSitePath("https://www.pokemon-card.com/ex/sv11/?q=a%2Bb#products", root), "https://www.pokemon-card.com/ex/sv11/?q=a%2Bb#products");
  }
});

check("URL updates preserve fragments and unrelated repeated parameters", () => {
  for (const root of ["https://example.test/", "file:///Users/example/_site/"]) {
    const url = writeState(state({q: "SM1+", view: "artwork"}), `${root}card/2024/02/timeline.html?utm_tag=one&utm_tag=two&foo=a%2Bb#calendar`, context);
    assert.equal(url.hash, "#calendar");
    assert.deepEqual(Array.from(url.searchParams.getAll("utm_tag")), ["one", "two"]);
    assert.equal(url.searchParams.get("foo"), "a+b");
    assert.equal(url.searchParams.get("q"), "SM1+");
    assert.equal(url.searchParams.has("view"), false);
  }
});

check("reset deletes all duplicated managed parameters while preserving others", () => {
  const url = writeState(defaults, "https://example.test/timeline.html?q=a&q=b&era=SV&from=2024&to=2024&view=list&theme=blue#releases", context);
  assert.equal(url.search, "?theme=blue");
  assert.equal(url.hash, "#releases");
});

check("custom coverage contexts determine normalization defaults", () => {
  const limited = {years: [2023, 2024], eras: ["SV"]};
  assert.deepEqual(normalizeState({from: "1996", to: "2026", era: "S"}, limited), {...defaults, from: 2023, to: 2024});
});

export const results = [];
for (const {name, run} of cases) {
  try {
    await run();
    results.push({name, passed: true});
  } catch (error) {
    results.push({name, passed: false, error: error.message});
  }
}
const failed = results.filter(result => !result.passed);
if (failed.length) throw new Error(failed.map(result => `${result.name}: ${result.error}`).join("\n"));
console.log(`Timeline regression tests: ${results.length} passed.`);
