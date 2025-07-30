// static/js/dashboard/filters.js
import { $, safeChoices, WEEK_DAYS } from "./dashboard_utils.js";

/* Cache Choices instances globally so other modules can access them */
export const ci = (window.choicesInstances = {});

/* ───── constants ───── */
const TIME_SLOTS = ["All", "Morning", "Afternoon"]; // only two slots

/* Central list of filters so we can loop once everywhere */
const FILTERS = [
  { id: "tt-branch-select", key: "branch", label: "Branch" },
  { id: "day-filter",       key: "day",    label: "Day"    },
  { id: "class-filter",     key: "class",  label: "Class"  },
  { id: "coach-filter",     key: "coach",  label: "Coach"  },
  { id: "time-filter",      key: "time",   label: "Time"   }
];

/* ──────────────────────────────────────────────────────────────
 * 0) Timetable pager visibility
 *    Hide the pager when the Branch filter is *not* "All".
 *    (If you prefer to hide it when ANY filter is active, see comment below.)
 * ────────────────────────────────────────────────────────────── */
function syncTimetablePagerVisibility() {
  const pager = $("timetable-pager");
  if (!pager) return;

  const branchVal = $("tt-branch-select")?.value ?? "All";

  // CURRENT RULE: hide when branch is NOT "All"
  const hide = branchVal !== "All";

  // If you want to hide when ANY filter is active, use this instead:
  // const hide = FILTERS.some(({ id }) => (($(id)?.value ?? "All") !== "All"));

  pager.classList.toggle("d-none", hide);
}

/* ───── 1) helpers ───── */
export function applyTimeSlotNow(drawAll) {
  const now = new Date();
  let hour = now.getHours();
  let wd   = now.getDay();

  let slot;
  if      (hour < 8)  slot = "All";        // before 8am just leave it
  else if (hour < 12) slot = "Morning";
  else if (hour < 19) slot = "Afternoon";
  else {                                   // after 7pm → next day Morning
    slot = "Morning";
    wd   = (wd + 1) % 7;
  }

  const dayName = wd === 0 ? "Sunday" : WEEK_DAYS[wd - 1];

  const daySelect  = $("day-filter");
  const timeSelect = $("time-filter");

  daySelect.value  = dayName;
  timeSelect.value = slot;
  ci.day ?.setChoiceByValue(dayName);
  ci.time?.setChoiceByValue(slot);

  drawAll(
    $("tt-branch-select").value,
    dayName,
    $("class-filter").value,
    $("coach-filter").value,
    slot
  );
  updateFilterChips(drawAll);
}

/* ───── 2) pill / badge update ───── */
export function updateFilterChips(drawAll) {
  const active = FILTERS.reduce((n, { id }) =>
    n + (($(id)?.value ?? "All") !== "All"), 0);

  const badge = $("filter-badge");
  if (badge) {
    badge.textContent = active || "";
    badge.classList.toggle("d-none", active === 0);
  }

  const row = $("active-filters");
  if (row) row.innerHTML = "";

  FILTERS.forEach(({ id, key, label }) => {
    const sel = $(id);
    const val = sel?.value;
    if (!val || val === "All" || !row) return;

    const chip = document.createElement("span");
    chip.className = "badge bg-secondary me-2 d-inline-flex align-items-center";
    chip.innerHTML = `
      <span>${label}: ${val}</span>
      <button type="button" class="btn-close btn-close-white btn-sm ms-2"></button>
    `;
    chip.querySelector("button").onclick = () => {
      sel.value = "All";
      ci[key]?.setChoiceByValue?.("All");

      drawAll(
        $("tt-branch-select").value,
        $("day-filter").value,
        $("class-filter").value,
        $("coach-filter").value,
        $("time-filter").value
      );
      updateFilterChips(drawAll);
    };
    row.appendChild(chip);
  });

  // <-- ensure pager visibility follows the rule
  syncTimetablePagerVisibility();
}

/* ───── 3) filter initialisation ───── */
export function wireFilters(drawAll) {
  const branch = $("tt-branch-select"),
        day    = $("day-filter"),
        cls    = $("class-filter"),
        coach  = $("coach-filter"),
        time   = $("time-filter");

  // If your HTML still has "Evening", strip it here
  if (time && time.options.length) {
    const wanted = new Set(TIME_SLOTS);
    [...time.options].forEach(opt => { if (!wanted.has(opt.value)) opt.remove(); });
  }

  if (!ci.branch) ci.branch = safeChoices(branch, { searchEnabled: true });
  if (!ci.day)    ci.day    = safeChoices(day,    { searchEnabled: true, shouldSort: false });
  if (!ci.class)  ci.class  = safeChoices(cls,    { searchEnabled: true });
  if (!ci.coach)  ci.coach  = safeChoices(coach,  { searchEnabled: true });
  if (!ci.time)   ci.time   = safeChoices(time,   { searchEnabled: true, shouldSort: false });

  [branch, day, cls, coach, time].forEach(sel =>
    sel.addEventListener("change", () => {
      drawAll(branch.value, day.value, cls.value, coach.value, time.value);
      updateFilterChips(drawAll);
    })
  );

  $("auto-time-btn")?.addEventListener("click", () => applyTimeSlotNow(drawAll));
  $("clear-filters-btn")?.addEventListener("click", () => {
    [branch, day, cls, coach, time].forEach(sel => sel.value = "All");
    Object.values(ci).forEach(inst => inst?.setChoiceByValue?.("All"));
    drawAll("All", "All", "All", "All", "All");
    updateFilterChips(drawAll);
  });

  updateFilterChips(drawAll);        // initial chips + pager visibility
  syncTimetablePagerVisibility();    // (redundant but explicit)
}
