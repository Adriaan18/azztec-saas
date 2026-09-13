# Azztec SaaS — S1i Priority Badge Paint Chunk Spec

**File:** Azztec_SaaS_S1i_Priority_Paint_Chunk_Spec_v1_0_0.md · **Version:** 1.0.0 · **Date:** 2026-09-14 · **Author:** Adriaan
**Status:** Draft — **OD-38, OD-39, OD-40, OD-41 need 🤙 before anything is built**
**Target path:** `docs/Azztec_SaaS_S1i_Priority_Paint_Chunk_Spec_v1_0_0.md` (+ project knowledge)
**Parent spec:** `Azztec_SaaS_Planner_Port_Spec_v1_0_4.md` §3 (`priorities[]`), §6 (the frontend slice before S2), §9
**Source of truth:** `Planner_v1_8_1.html` — `.chip .pri` CSS 282–283, `chipEl` 595, the day-dialog row 723
**Closes:** the **frontend half of open item 29** and open item **36** (the renderer guard)
**Signed decisions in force:** OD-36 (the API ships `colour` as stored, validated nowhere), OD-27 (the port ships the oracle's CSS), OD-31 (no shadcn in a port), OD-32 **withdrawn** (rank is not priority), OD-33 (hover stays `chipTitle`), OD-23 (the 42-day cap)

---

## 1. Scope — thirteen cards and two generated sets, then stop

| # | Deliverable | Target path | Version | Change |
|---|---|---|---|---|
| 1 | `Azztec_SaaS_app_main_v1_0_4.py` | `backend/app/main.py` | 0.3.0 → **0.4.0** | version line + changelog only (OD-38) |
| 2 | `Azztec_SaaS_test_smoke_v1_1_1.py` | `backend/tests/test_smoke.py` | 1.1.0 → **1.1.1** | **header only** — its `Pair of main.py 0.3.0` line goes stale |
| 3 | `Azztec_SaaS_web_openapi_ts_config_v1_0_2.ts` | `web/openapi-ts.config.ts` | 1.0.1 → **1.0.2** | `input` path (OD-38) |
| 4 | `Azztec_SaaS_web_planner_rules_v1_2_0.ts` | `web/src/features/planner/rules.ts` | 1.1.0 → **1.2.0** | `isHexColour`, `luminance`, `textOn`, `PriBadge`, `priBadgeMap` (OD-39, OD-40) |
| 5 | `Azztec_SaaS_web_planner_rules_test_v1_2_0.ts` | `web/src/features/planner/rules.test.ts` | 1.1.0 → **1.2.0** | pair of 4 |
| 6 | `Azztec_SaaS_web_planner_range_fixture_v1_2_0.ts` | `web/src/features/planner/range.fixture.ts` | 1.1.0 → **1.2.0** | `colour` on five rows — **a compile error until it lands** |
| 7 | `Azztec_SaaS_web_planner_WOCard_v1_1_0.tsx` | `web/src/features/planner/WOCard.tsx` | 1.0.1 → **1.1.0** | `priRank?: number` → `badge?: PriBadge` (OD-41) |
| 8 | `Azztec_SaaS_web_planner_WOCard_test_v1_1_0.tsx` | `web/src/features/planner/WOCard.test.tsx` | 1.0.1 → **1.1.0** | pair of 7 |
| 9 | `Azztec_SaaS_web_planner_DayCell_v1_1_0.tsx` | `web/src/features/planner/DayCell.tsx` | 1.0.1 → **1.1.0** | `rank` prop → `badges`, passed through |
| 10 | `Azztec_SaaS_web_planner_PlannerGrid_v1_1_0.tsx` | `web/src/features/planner/PlannerGrid.tsx` | 1.0.1 → **1.1.0** | one `useMemo` swaps map |
| 11 | `Azztec_SaaS_web_planner_PlannerGrid_test_v1_1_0.tsx` | `web/src/features/planner/PlannerGrid.test.tsx` | 1.0.1 → **1.1.0** | pair of 9 + 10 |
| 12 | `Azztec_SaaS_web_planner_DayDialog_v1_1_0.tsx` | `web/src/features/planner/DayDialog.tsx` | 1.0.0 → **1.1.0** | same swap, second badge site |
| 13 | `Azztec_SaaS_web_planner_DayDialog_test_v1_1_0.tsx` | `web/src/features/planner/DayDialog.test.tsx` | 1.0.1 → **1.1.0** | pair of 12 |

**Generated, committed, never cards:** `docs/api/openapi_0_4_0.json` (exported from the app, §7) and `web/src/api/client/**` (`pnpm gen:api`). `docs/api/openapi_0_3_0.json` is `git rm`-ed in the same commit — git keeps it, and two contract documents on disk invite the generator to read the wrong one.

**`planner.css` stays 1.1.1.** The paint is an inline `backgroundColor` / `color` pair, which beats the stylesheet's `background` shorthand without a new rule, and the `.pri.A–D` letter rules must survive untouched for KT (OD-41). A file that does not change does not ship.

**Not in this slice:** the priority `<select>` in `FiltersRow` (the oracle has no swatch there — oracle 845), the `SelectedWOCard` Priority row (a `kv` text row, oracle 814, not a badge), `CapacityBar` 1.0.1 / `nWorkers` (item 27), `prettier --check` in the smoke (item 25), item 35's role tokens, item 37's SQL rewrite. Nothing writes to any database.

**The cut available at the gate:** drop cards 12–13 and paint the chip only (eleven cards). **Not recommended** — the day dialog shows the same WOs on the same data one click away, and a grey badge next to an orange one for the same priority reads as a defect. If the count is the problem, the honest cut is the whole slice, not half a feature.

## 2. Evidence — read 2026-09-14, before any 🤙

### 2.1 The contract has already moved; three artefacts disagree

```
docs/api/openapi_0_3_0.json   info.version 0.3.0, 20325 B, written 11/09/2026 5:32 pm
  components.schemas.Priority  properties id, short, title   required [id, short, title]

app.openapi() on the box now (offline, no server)
  components.schemas.Priority  properties id, short, title, colour
                               required [id, short, title, colour]   additionalProperties false

web/src/api/client/types.gen.ts:112  export type Priority = { id: number; ... }   -- three fields
web/src/api/client/types.gen.ts:164  priorities: Array<Priority>

web/package.json:16  "gen:api": "openapi-ts"
web/openapi-ts.config.ts:27  input: '../docs/api/openapi_0_3_0.json'
Get-ChildItem -Recurse -Filter openapi_*.json -> exactly one file
```

`colour` is **required**, not optional — `schemas.Priority.colour: str` has no default, so the generated TS field is `colour: string`. Three consequences: the regeneration is not cosmetic, `range.fixture.ts` stops compiling the moment it lands (§2.3), and the generator's input file is the only thing standing between the committed contract and the real one.

### 2.2 The oracle paints two badge sites, and already does the text-colour trick by hand

```
Planner_v1_8_1.html 282   .chip .pri{...color:#2b2b2b;background:var(--mut)...}        --mut  #9AA3AD
Planner_v1_8_1.html 283   .chip .pri.A{background:var(--red);color:#fff}               --red  #EF6C57
                          .chip .pri.B{background:var(--gold2)}                        --gold2 #D4A863
                          .chip .pri.C{background:#8fa3b5}
                          .chip .pri.D{background:#6f7c87;color:#fff}
Planner_v1_8_1.html 723   the day-dialog row repeats the badge with the same values inline

planner.css 1.1.1 118     .wm-planner .chip .pri{...}          — the port, same values
planner.css 1.1.1 120     .wm-planner .chip .pri.A..D{...}     — KT's letters
planner.css 1.1.1 218     .wm-planner .dd2 .job .pri{...}      — the second site
planner.css 1.1.1 121     ".pri.r1..r4 removed in 1.1.1 - the rank class is still on the badge, unstyled"
```

A and D get `#fff`, B and C keep `#2b2b2b`. The oracle decided that by eye, per class. RST has no A–D shorts (P1…P6, N/A), so **every RST badge renders in the base muted style today** — that is the defect item 29 is about, not a missing feature.

**Nothing in the port reads the payload's `colours{}`.** Category colour comes from the `.cat-<cat>` classes; `colours` is on the wire and unused (`usePlannerRange.test.tsx` sends `colours: {}` and nothing notices). Port Spec 1.0.3 §9 said the chip would paint "as it already does for category colours" — there is no such precedent, and 1.0.4 no longer claims one. This slice is the first payload-driven paint in the port.

### 2.3 The four files the regeneration touches, and the one it breaks

| File | Priority contact | Effect of a required `colour` |
|---|---|---|
| `range.fixture.ts` 1.1.0 | `export const RANGE: RangeData` with five `{id, short, title}` rows (213–219) | **compile error** — the only frontend file that constructs a `Priority` literal |
| `rules.test.ts` 1.1.0 | reads `RANGE.priorities` (410–459) | compiles; `priorityOptions` / `priRank` / `priRankMap` assertions unaffected |
| `usePlannerRange.test.tsx` 1.0.0 | an untyped object with `priorities: []` → `JSON.stringify` | unaffected — no annotation, no literal |
| `PlannerGrid` / `DayCell` / `WOCard` / `DayDialog` | `priRankMap` → `ReadonlyMap<number, number>` → `priRank` | compiles unchanged; paints nothing |

So the regeneration alone leaves the tree red on `pnpm build` and green on `pnpm test` — the fixture is a type-only failure. That is why the fixture is in this slice and not the next.

### 2.4 The payload on each site

```
RST, seven active rows, every colour distinct (S1h §5.1, on the wire 7 of 7)
  P2 #FF9F40   P1 #FF0000   P3 #74EE66   P5 #C499C1   P6 #C0C0C0   P4 #0080FF   N/A #FFFFFF
KT, four rows, no ties
  A #FF8000    B #FF8000    C #FF8000    D #FF8000
Colour is varchar(255) NULL on both — free text, '' for NULL (OD-36)
```

RST distinguishes seven priorities by colour. KT distinguishes nothing by colour and everything by letter class. Both have to keep working off one code path, and neither is the "right" one.

## 3. The changes, exactly

### 3.1 `main.py` → 0.4.0 and the export filename (OD-38)

`__version__ = "0.4.0"` plus a changelog line. No logic change. `info.version` in the exported document is `main.__version__` (line 83), so the document's own version is the only honest dial for "the published schema gained a field" — and `openapi-ts.config.ts`'s header already states the convention: *bump the input path when main.py bumps its version*. Nothing pins the literal: `test_smoke.test_health_versions_match_the_modules` compares `/health` against `db`, `diag`, `config` and `planner_router.__version__` and never against `main`, and `test_openapi_contract` reads `app.openapi()` live.

`test_smoke.py` → **1.1.1, header only**: its line 5 reads `Pair of main.py 0.3.0`. Flagged here rather than shipped false (Ways of Working §5, the S1h precedent). Its assertions need nothing.

**`/health`'s own `version` field is the one version nobody asserts.** Adding `assert body["version"] == main.__version__` would make `test_smoke` a behaviour change (1.2.0) inside a slice that signed a header-only edit, so it is **new open item 39**, not a smuggled fix.

### 3.2 `rules.ts` → 1.2.0 — four pure functions and one map

```ts
/** planner.css 118 / oracle 282: the base badge's own text colour. */
const PRI_FG_DARK = '#2b2b2b';
const PRI_FG_LIGHT = '#ffffff';
const HEX6 = /^#[0-9A-Fa-f]{6}$/;

/** OD-36 ships varchar(255) free text. Nothing reaches a style attribute without passing this. */
export function isHexColour(s: string): boolean {
  return HEX6.test(s);
}

/** WCAG relative luminance. Pure arithmetic on a validated #RRGGBB - no DOM, no Date. */
export function luminance(hex: string): number {
  const ch = (i: number) => {
    const x = parseInt(hex.slice(i, i + 2), 16) / 255;
    return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * ch(1) + 0.7152 * ch(3) + 0.0722 * ch(5);
}

/** The higher-contrast of the base badge's dark text and white. OD-40. */
export function textOn(hex: string): string {
  const l = luminance(hex);
  const ratio = (a: number, b: number) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  return ratio(l, L_DARK) >= ratio(l, 1) ? PRI_FG_DARK : PRI_FG_LIGHT;
}

export type PriBadge = { rank: number; bg: string; fg: string };

/**
 * One entry per priority: the OD-32 rank always, a paint pair only when the payload's colours
 * carry information (>= 2 distinct usable values - OD-39). Built once per data load, never per
 * chip (Landmines §D).
 */
export function priBadgeMap(priorities: ReadonlyArray<Priority>): Map<number, PriBadge> {
  const rank = priRankMap(priorities);
  const distinct = new Set(
    priorities.filter((p) => isHexColour(p.colour)).map((p) => p.colour.toUpperCase()),
  );
  const paint = distinct.size >= 2;
  return new Map(
    priorities.map((p) => [
      p.id,
      paint && isHexColour(p.colour)
        ? { rank: rank.get(p.id) ?? 0, bg: p.colour, fg: textOn(p.colour) }
        : { rank: rank.get(p.id) ?? 0, bg: '', fg: '' },
    ]),
  );
}
```

`L_DARK` is `luminance(PRI_FG_DARK)` computed once at module scope. `priRank`, `priRankMap` and `priClass` are **unchanged and still exported** — `priBadgeMap` calls `priRankMap`, so the rank contract keeps one implementation and the OD-32 tests keep passing on it.

### 3.3 The two badge sites (OD-41)

`WOCard`'s prop becomes `badge?: PriBadge` (default `undefined`), and the badge span becomes:

```tsx
{wo.pri ? (
  <span
    className={rankCls ? `pri ${wo.pri} ${rankCls}` : `pri ${wo.pri}`}
    style={badge && badge.bg ? { backgroundColor: badge.bg, color: badge.fg } : undefined}
  >
    {wo.pri}
  </span>
) : null}
```

`rankCls` is `priClass(badge?.rank ?? 0)` — the class string is built exactly as 1.0.1 built it, so `'pri P1'`, `'pri P1 r1'` and `'pri N/A'` are byte-identical and the existing assertions stay green. `DayDialog` takes the same treatment at line 57; it already receives `priorities` and builds its own map in a `useMemo`, so it gains no prop. `PlannerGrid` line 83 swaps `priRankMap` for `priBadgeMap` and `DayCell`'s prop becomes `badges: ReadonlyMap<number, PriBadge>`, forwarded as `badge={badges.get(wo.priId)}`.

Four components, one map, one lookup per chip. `planner.css` is untouched.

## 4. Traps

1. **Inline style beats the letter class, which is the whole reason for OD-39's gate.** A painted badge on KT would make A/B/C/D four identical orange chips. The gate is not a nicety; it is what keeps the oracle's CSS meaningful on the site that has no usable colour.
2. **Case.** `#ff8000` and `#FF8000` are one colour. The distinct set is built on `toUpperCase()` or KT's suppression can be defeated by a data edit.
3. **`backgroundColor`, not `background`.** The stylesheet sets the `background` shorthand; an inline longhand still wins, and jsdom reports `style.backgroundColor` as `rgb(r, g, b)` — assert that form, not the hex.
4. **`**` not `Math.pow`.** `@tanstack/eslint-config` prefers the exponentiation operator, and TS 6 + ESLint 10 fail `pnpm lint` before the test runs (Landmines §C).
5. **`rank.get(p.id) ?? 0`, never `!`.** The config flags non-null assertions; the map is built from the same array two lines above, so `?? 0` is unreachable and harmless.
6. **The fixture's colours are test data, not RST's table.** Five rows get RST's real values for the shorts they name so the branches are covered, but no test asserts a row count or an alphabetical order — that is the S1h §6.3 trap, and Ways of Working §6 now names it.
7. **Do not add `prettier --check` to the smoke while in the file** (item 25, unsigned), and do not touch `CapacityBar` (item 27).
8. **The export command must use `main.py`'s own `app`, not a second `create_app()`.** `main.py` builds `app = create_app()` at module scope, so importing the factory and calling it wires diag twice — both `[F] diag wired` lines in today's audit read came from exactly that. `from app.main import app` wires once.
9. **`git rm` the old export in the same commit as the new one**, or `pnpm gen:api` can be re-run later against a contract that is two versions stale and succeed.

## 5. Test plan

### 5.1 `rules.test.ts` → 1.2.0, zero DB, zero DOM

`isHexColour`: `#FF9F40` and `#ff9f40` true; `''`, `#FFF`, `#GGGGGG`, `FF9F40`, `#FF9F400`, `red`, `rgb(1,2,3)` false.

`textOn` — the seven RST values. **Computed by hand for this spec; the test is what verifies them**, and if one disagrees the arithmetic was wrong, not the rule:

| colour | luminance (predicted) | contrast vs `#2b2b2b` | vs `#ffffff` | `textOn` |
|---|---|---|---|---|
| `#FF9F40` | 0.464 | 6.93 | 2.04 | `#2b2b2b` |
| `#74EE66` | 0.658 | 9.55 | 1.58 | `#2b2b2b` |
| `#C0C0C0` | 0.527 | 7.78 | 1.85 | `#2b2b2b` |
| `#C499C1` | 0.384 | 5.85 | 2.42 | `#2b2b2b` |
| `#FFFFFF` | 1.000 | 14.16 | 1.00 | `#2b2b2b` |
| `#FF0000` | 0.213 | 3.54 | 4.00 | `#ffffff` |
| `#0080FF` | 0.227 | 3.73 | 3.80 | `#ffffff` |

`#0080FF` is the case to watch — a 2 % margin, and any threshold-style rule would flip it. Pinned deliberately.

`priBadgeMap`:
- the RST-shaped fixture → every row painted, `fg` per the table, `rank` equal to `priRankMap`'s for every id
- a KT-shaped local literal (four rows, all `#FF8000`) → every `bg` `''`, ranks 1–4 intact
- mixed (`#FF0000`, `''`, `not-a-colour`, `#0080FF`) → the two hex rows painted, the other two `bg: ''`
- one usable colour among several → **nothing painted** (`distinct.size < 2`), the documented consequence of OD-39
- every row junk → nothing painted, ranks intact
- an empty array → an empty map, no throw
- `#ff8000` mixed with `#FF8000` counts as one distinct colour

`luminance` gets `#000000` → 0 and `#FFFFFF` → 1 as its anchors.

### 5.2 Component tests

`WOCard.test.tsx` 1.1.0 — the three existing className assertions unchanged (`'pri P1'`, `'pri P1 r1'`, `'pri N/A'`, and no badge when `pri` is `''`), plus: a painted badge carries `style.backgroundColor === 'rgb(255, 0, 0)'` and `style.color === 'rgb(255, 255, 255)'`; a `bg: ''` badge carries no inline background; `badge` omitted renders exactly as 1.0.1 did.

`PlannerGrid.test.tsx` 1.1.0 — one assertion that the paint reaches a chip through the grid off `RANGE.priorities` (the map is built here, so this is the only test that proves the plumbing).

`DayDialog.test.tsx` 1.1.0 — the same on a `.dd2 .job .pri` badge, so the second site cannot silently stay grey.

### 5.3 Counts

Backend **156** and no new cases — `main.py` and `test_smoke.py` are version lines. Frontend is 155 + the new cases; **read both off the run**, gate on `$LASTEXITCODE`.

## 6. Open decisions — 🤙 required

| ID | Question | Proposal |
|---|---|---|
| **OD-38** | The published `Priority` schema changed and `main.py.__version__` did not, so the export has no filename to land on. Regenerate `openapi_0_3_0.json` in place, or bump the app? | **Bump `main.py` to 0.4.0, export `docs/api/openapi_0_4_0.json`, `git rm` the 0.3.0 file, config → 1.0.2.** `info.version` *is* `main.__version__`, the document gained a required field, and minor-for-a-new-field is the standing bump rule. The alternative keeps a filename that asserts a contract version the file no longer holds — and the versioned filename exists precisely so that "regenerate" means "the contract changed". Cost: two extra cards (`main.py`, `test_smoke.py` header). |
| **OD-39** | When may the payload's `colour` paint the badge at all? `varchar(255)` free text on RST; four identical values on KT. | **Per row it must pass `^#[0-9A-Fa-f]{6}$`; per payload it paints only when there are ≥ 2 distinct usable colours.** RST (7 distinct) paints; KT (1 distinct) falls to `.pri.A–D` and keeps its letters. Consequence accepted: a payload with exactly one usable colour paints nothing. The alternative — paint whatever is usable — makes KT four identical chips, which is the thing item 29 was told not to do. |
| **OD-40** | What text colour goes on a painted badge? The base `.pri` sets `#2b2b2b`, which is unreadable on `#FF0000`. | **Whichever of `#2b2b2b` and `#ffffff` has the higher WCAG contrast against the background; ties go dark.** No threshold constant to argue about, and the base badge's own colour is one of the two candidates. **Stated plainly: this is a contrast floor, not the oracle's aesthetic** — applied to `.pri.A` (`#EF6C57`) it would choose dark where the oracle chose white. It never runs there: A–D are CSS classes and KT never reaches the paint path. |
| **OD-41** | How does the paint reach two badge sites without per-chip work or a CSS change? | **One map, `priBadgeMap → {rank, bg, fg}`, replacing `priRankMap` at both call sites; the badge takes `badge?: PriBadge` and applies inline `backgroundColor` / `color` longhands.** `priRank`/`priRankMap`/`priClass` stay exported and `priBadgeMap` calls `priRankMap`, so the rank contract has one implementation and the OD-32 tests keep passing. The class string is built exactly as 1.0.1 built it, so no existing className assertion moves and `planner.css` stays 1.1.1. The alternative — a second `priPaintMap` and a second prop — is a smaller diff, two memos over the same input and two places to disagree about how a badge looks. |

## 7. Smoke

Backend first (the app version moved, and `dist/` already exists):

```
cd C:\dev\workmate-saas\backend
uv run ruff format .
uv run ruff check .
uv run pytest
"backend exit $LASTEXITCODE"
```

Export the contract, then regenerate the client:

```
cd C:\dev\workmate-saas\backend
uv run python -c "import json, pathlib; from app.main import app; pathlib.Path('../docs/api/openapi_0_4_0.json').write_text(json.dumps(app.openapi(), indent=2), encoding='utf-8')"
cd ..
git rm --cached docs\api\openapi_0_3_0.json
Remove-Item docs\api\openapi_0_3_0.json
Get-ChildItem docs\api | Format-List Name, Length, LastWriteTime
Select-String -Path docs\api\openapi_0_4_0.json -Pattern '"colour"' -SimpleMatch
```

```
cd C:\dev\workmate-saas\web
pnpm gen:api
Select-String -Path src\api\client\types.gen.ts -Pattern 'colour' -Context 1,1
pnpm lint
pnpm test
"frontend exit $LASTEXITCODE"
pnpm build
Get-Item dist\index.html | Format-List Name, Length, LastWriteTime
```

Then the browser, **one tab**, backend and Vite in their own windows: `http://localhost:3000/planner?mode=week&anchor=2026-09-14`. Expected — P1 badges red with white text, P4 blue with white text, P2 orange / P3 green / P5 mauve / P6 silver / N/A white all with the dark text, the same colours in the 14 Sep day dialog (106 PMs), and `chipTitle` hover unchanged (OD-33). Screenshot held next to the Ignition planner: KT's A–D are unaffected because KT never reaches the paint path.

## 8. Acceptance

- Thirteen cards in §1, no fourteenth. `planner.css`, `FiltersRow`, `SelectedWOCard`, `CapacityBar`, `service.py` and every backend planner module untouched.
- `docs/api/openapi_0_4_0.json` committed, `openapi_0_3_0.json` removed, both in one commit; `web/src/api/client/**` regenerated and committed, never hand-edited.
- Backend **156**, exit 0. Frontend green, exit 0, count read from the run. `pnpm build` clean — which is also the proof the fixture landed.
- Every §5.1 row asserted, including `#0080FF` → white and the KT-shaped suppression.
- Nothing wrote to any database.
- `git commit -m "planner priority badge paint 1.2.0 — S1i"`, tag the versions that shipped: `s1i-priority-paint-1.2.0`.
- Raw log carries §2's three-artefact disagreement, the `textOn` table as verified by the run, and open item 39.

## 9. Consequences

### 9.1 Doc corrections for the next compiled set

- **Landmines §E**, `dbo.Priority`: the renderer guard is no longer pending — record that the badge paints from the payload behind OD-39's gate and OD-40's contrast rule, and that KT keeps its letter classes. §C: inline longhand beats a stylesheet shorthand, which is what lets a payload colour win without a CSS rule.
- **Port Spec §3** `priorities[]`: the frontend half of item 29 is done; §6 gains the S1i row; §9 records OD-38…OD-41 and closes items 29 and 36.
- **Architecture §3.2** API-client row and **§6** step 3: the input is `openapi_0_4_0.json`; §4 D-9 gains OD-38 as the precedent for versioning the exported document.
- **Index** §1 state, §3.1/3.4/3.4b/3.5 versions, §6 next → the uplift audit.
- **Ways of Working §2**: the export filename convention, if OD-38 is signed as proposed.

### 9.2 What this unblocks

The **uplift audit** (item 32) becomes next with nothing frontend outstanding, and S2 inherits a `PriBadge` map it can reuse for the drag preview.

### 9.3 New open items

- **39** — `/health`'s own `version` field is the only version not asserted against a module constant; `test_smoke` compares `db`, `diag`, `config` and `planner` and skips `main`. One line, deliberately not smuggled into this slice.

## 10. Changelog

- 1.0.0 (2026-09-14) Initial. Written from the item-29 frontend audit: the committed contract, `app.openapi()`, `types.gen.ts`, `package.json` and the generator config read on the box; `WOCard` 1.0.1, `DayCell` 1.0.1, `PlannerGrid` 1.0.1, `DayDialog` 1.0.0, `rules.ts` 1.1.0, `range.fixture.ts` 1.1.0, `rules.test.ts` 1.1.0, `WOCard.test.tsx` 1.0.1, `planner.css` 1.1.1, `test_smoke.py` 1.1.0, `test_openapi_contract.py` 1.0.0 and the oracle's `.pri` CSS read in full. Raises OD-38…OD-41 and item 39.
