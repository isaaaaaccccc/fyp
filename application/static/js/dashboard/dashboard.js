// static/js/dashboard/dashboard.js
import { WEEK_DAYS, rebuildNativeSelect, setChoicesList, $ } from "./dashboard_utils.js";
import { updateFilterChips, wireFilters } from "./filters.js";
import renderCardStrip          from "./kpi.js";
import renderCoachWorkload      from "./coachWorkload.js";
import renderCoachRadar         from "./coachRadar.js";
import renderSessionsPerDay     from "./sessionsPerDay.js";
import renderSessionsPerCourse  from "./sessionsPerCourse.js";
import renderSessionsPerBranch  from "./sessionsPerBranch.js";
import renderSessionsMatrix     from "./sessionsMatrix.js";
import renderTimetable          from "./timetable.js";

import {
  exportStats,
  toggleTimetable,
  toggleAnalytics,
  toggleKPI
} from "./exports.js";

window.addEventListener("DOMContentLoaded", () => {
  if (window.Chart && Chart.registerables) {
    Chart.register(...Chart.registerables);
  }

  // DOM refs
  const loader           = $("loader");
  const filtersBox       = $("filters");
  const kpiSection       = $("kpi-section");
  const kpiCards         = $("kpi-cards");
  const chartsSection    = $("charts-section");
  const chartsContent    = $("charts-content");
  const timetableSection = $("timetable-section");

  const branchSel        = $("tt-branch-select");   // global/off-canvas branch filter
  const dayFilter        = $("day-filter");
  const classFilter      = $("class-filter");
  const coachFilter      = $("coach-filter");
  const timeFilter       = $("time-filter");

  const exportCoachesBtn = $("export-coaches");
  const exportStatsBtn   = $("export-stats");

  // Pager elements (only used when global branch = "All")
  const pagerWrapper     = $("timetable-pager");
  const pagerSelect      = $("timetable-branch-select");
  const pagerPrevBtn     = $("tt-prev-branch");
  const pagerNextBtn     = $("tt-next-branch");
  const pagerCounter     = $("tt-branch-counter");

  // Panel toggles
  document.getElementById("toggle-timetable")?.addEventListener("click", toggleTimetable);
  document.getElementById("toggle-analytics")?.addEventListener("click", toggleAnalytics);
  document.getElementById("toggle-kpi")?.addEventListener("click", toggleKPI);

  // Export stats
  exportStatsBtn?.addEventListener("click", () => {
    exportStats(
      branchSel.value,
      dayFilter.value,
      classFilter.value,
      coachFilter.value,
      timeFilter.value
    );
  });

  // Pager state
  let branchListForPager = [];
  let currentPagerIndex  = 0;
  window.currentTimetablePageBranch = null;

  function buildPagerBranchList(allData) {
    branchListForPager = Object.keys(allData || {}).sort();
    if (currentPagerIndex >= branchListForPager.length) currentPagerIndex = 0;
  }

  function syncPagerSelect() {
    if (!pagerSelect) return;
    const list = branchListForPager;
    rebuildNativeSelect(
      pagerSelect,
      list,
      window.currentTimetablePageBranch || list[0]
    );
    if (pagerCounter) {
      const i = branchListForPager.indexOf(pagerSelect.value);
      pagerCounter.textContent = `Branch ${i + 1} of ${branchListForPager.length}`;
    }
  }

  function updateTimetablePagerUI(globalBranchValue) {
    if (!pagerWrapper) return;

    if (globalBranchValue === "All" && branchListForPager.length > 0) {
      pagerWrapper.style.display = "flex";
      syncPagerSelect();
      window.currentTimetablePageBranch = pagerSelect.value;
    } else {
      pagerWrapper.style.display = "none";
      window.currentTimetablePageBranch = null;
    }
  }

  function movePager(delta, drawFn) {
    if (branchListForPager.length === 0) return;
    currentPagerIndex = (currentPagerIndex + delta + branchListForPager.length) % branchListForPager.length;
    window.currentTimetablePageBranch = branchListForPager[currentPagerIndex];
    syncPagerSelect();
    drawFn(
      branchSel?.value || "All",
      dayFilter?.value || "All",
      classFilter?.value || "All",
      coachFilter?.value || "All",
      timeFilter?.value || "All"
    );
  }

  pagerPrevBtn?.addEventListener("click", () => {
    if (branchSel?.value === "All" && typeof drawAll === "function") movePager(-1, drawAll);
  });

  pagerNextBtn?.addEventListener("click", () => {
    if (branchSel?.value === "All" && typeof drawAll === "function") movePager(1, drawAll);
  });

  pagerSelect?.addEventListener("change", () => {
    if (branchSel?.value !== "All") return;
    window.currentTimetablePageBranch = pagerSelect.value;
    currentPagerIndex = branchListForPager.indexOf(pagerSelect.value);
    updateTimetablePagerUI(branchSel.value);
    typeof drawAll === "function" && drawAll(
      branchSel.value,
      dayFilter?.value || "All",
      classFilter?.value || "All",
      coachFilter?.value || "All",
      timeFilter?.value || "All"
    );
  });

  let drawAll; // assigned after data load

  // Fetch data
  fetch("/api/timetable/active")
    .then(res => res.json())
    .then(json => {
      const data = json['data'];
      window.allData = data;

      // Reveal UI
      loader            && (loader.style.display = "none");
      filtersBox        && (filtersBox.style.display = "block");
      kpiSection        && (kpiSection.style.display = "block");
      kpiCards          && (kpiCards.style.display = "flex");
      chartsSection     && (chartsSection.style.display = "block");
      chartsContent     && (chartsContent.style.display = "grid");
      timetableSection  && (timetableSection.style.display = "block");
      exportCoachesBtn  && (exportCoachesBtn.disabled = false);
      exportStatsBtn    && (exportStatsBtn.disabled = false);

      // Populate global Branch select
      if (branchSel) {
        branchSel.innerHTML =
          `<option value="All">All</option>` +
          Object.keys(data).sort().map(b => `<option value="${b}">${b}</option>`).join("");
      }

      // Populate Class filter
      const classSet = new Set();
      Object.values(data).forEach(bi =>
        Object.values(bi.schedule).forEach(dayObj =>
          Object.values(dayObj).flat().forEach(s => classSet.add(s.name))
        )
      );
      if (classFilter) {
        classFilter.innerHTML =
          `<option value="All">All</option>` +
          Array.from(classSet).sort().map(c => `<option value="${c}">${c}</option>`).join("");
      }
      if (coachFilter) coachFilter.innerHTML = `<option value="All">All</option>`;

      /**
       * Main draw function – redraws everything based on filters.
       */
      drawAll = (branchValue, dayValue, classValue, coachValue, timeValue) => {
        let info, label;

        if (branchValue === "All") {
          // Build unified dataset
          info = { coaches: [], schedule: {} };
          WEEK_DAYS.forEach(d => { info.schedule[d] = {}; });

          Object.values(data).forEach(bInfo => {
            (bInfo.coaches || []).forEach(c => info.coaches.push(c));
            WEEK_DAYS.forEach(d => {
              const dayObj = bInfo.schedule[d] || {};
              Object.entries(dayObj).forEach(([coach, arr]) => {
                (info.schedule[d][coach] ??= []).push(...arr);
              });
            });
          });
          info.coaches = Array.from(new Set(info.coaches));
          label = "All";

          buildPagerBranchList(data);
          updateTimetablePagerUI("All");

        } else {
          info  = data[branchValue];
          label = branchValue;

          // Hide pager & sync
          updateTimetablePagerUI(branchValue);
          window.currentTimetablePageBranch = branchValue;

          if (pagerSelect) pagerSelect.value = branchValue; // ensure no stale value
        }

        if (!info || !info.schedule) {
          console.warn("No schedule for selected branch(es)");
          return;
        }

        // Charts / KPI
        renderCardStrip(info, dayValue, classValue, coachValue, timeValue);
        renderCoachWorkload("coach-workload", info, dayValue, classValue, coachValue, timeValue);
        renderCoachRadar("coach-performance-radar", info, dayValue, classValue, coachValue, timeValue);
        renderSessionsPerDay(label, info, dayValue, classValue, coachValue, timeValue);
        renderSessionsPerCourse(label, info, dayValue, classValue, coachValue, timeValue);
        renderSessionsPerBranch(
          "sessions-per-branch",
          data,
          branchValue,
          dayValue,
          classValue,
          coachValue,
          timeValue
        );
        renderSessionsMatrix("sessions-matrix-container", info, dayValue, classValue, coachValue);

        // Timetable
        renderTimetable(
          info,
          dayValue,
          classValue,
          coachValue,
          timeValue,
          undefined,
          branchValue,
          window.allData
        );

        updateFilterChips(drawAll);
      };

      // Init filters (Choices etc.)
      wireFilters(drawAll);

      // Coach dropdown update when branch changes
      function populateCoaches() {
        const ch = window.choicesInstances?.coach;
        if (!ch) return;

        const selected = branchSel?.value || "All";
        const coaches = selected === "All"
          ? Object.values(data).flatMap(b => b.coaches || [])
          : (data[selected]?.coaches || []);

        const unique = Array.from(new Set(coaches)).sort();
        ch.clearChoices();
        ch.setChoices(
          [{ value: "All", label: "All" }].concat(unique.map(c => ({ value: c, label: c })) ),
          "value","label", true
        );
        ch.setChoiceByValue("All");
      }

      branchSel?.addEventListener("change", () => {
        currentPagerIndex = 0;
        window.currentTimetablePageBranch = null; // reset pager pointer
        populateCoaches();
        drawAll(
          branchSel.value,
          dayFilter?.value || "All",
          classFilter?.value || "All",
          coachFilter?.value || "All",
          timeFilter?.value || "All"
        );
      });

      // Initial render
      populateCoaches();
      drawAll(
        branchSel?.value || "All",
        dayFilter?.value || "All",
        classFilter?.value || "All",
        coachFilter?.value || "All",
        timeFilter?.value || "All"
      );
    })
    .catch(err => console.error("API error:", err));
});
