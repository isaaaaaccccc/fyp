// static/js/dashboard/coachWorkload.js
import { $, WEEK_DAYS, passClass, timePass } from "./dashboard_utils.js";
let workloadChart;

export default function renderCoachWorkload(id, info, dayVal, clsVal, coachVal, timeVal) {
  const tally = {};
  const days = dayVal === "All" ? WEEK_DAYS : [dayVal];

  days.forEach(d => {
    // default to empty object if schedule for that day is missing
    const daySchedule = info.schedule?.[d] || {};
    Object.entries(daySchedule).forEach(([c, arr]) => {
      if (coachVal === "All" || c === coachVal) {
        tally[c] = (tally[c] || 0)
          + arr.filter(s => passClass(clsVal, s) && timePass(timeVal, s)).length;
      }
    });
  });

  if (workloadChart) workloadChart.destroy();
  workloadChart = new Chart($(id), {
    type: "pie",
    data: {
      labels:   Object.keys(tally),
      datasets: [{ data: Object.values(tally) }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#fff" } }
      }
    }
  });
}
