// static/js/dashboard/coachRadar.js
import { $, WEEK_DAYS, passClass, timePass } from "./dashboard_utils.js";
let radarChart;

export default function renderCoachRadar(id, info, dayVal, clsVal, coachVal, timeVal) {
  const stats = {};
  const days = dayVal === "All" ? WEEK_DAYS : [dayVal];

  days.forEach(d => {
    const daySchedule = info.schedule?.[d] || {};
    Object.entries(daySchedule).forEach(([c, arr]) => {
      if (coachVal === "All" || c === coachVal) {
        const sess = arr.filter(s => passClass(clsVal, s) && timePass(timeVal, s));
        if (!sess.length) return;
        stats[c] = stats[c] || { n: 0, dur: 0, days: new Set() };
        stats[c].n   += sess.length;
        stats[c].dur += sess.reduce((sum, x) => sum + x.duration, 0);
        sess.forEach(() => stats[c].days.add(d));
      }
    });
  });

  const labels     = Object.keys(stats);
  const sessions   = labels.map(c => stats[c].n);
  const avgDur     = labels.map(c => (stats[c].dur / stats[c].n).toFixed(1));
  const daysWorked = labels.map(c => stats[c].days.size);

  if (radarChart) radarChart.destroy();
  radarChart = new Chart($(id), {
    type: "radar",
    data: {
      labels,
      datasets: [
        { label: "# Sessions",    data: sessions,   fill: true },
        { label: "Avg Duration",  data: avgDur,     fill: true },
        { label: "# Days Worked", data: daysWorked, fill: true }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          beginAtZero: true,
          grid:       { color: "rgba(255,255,255,0.1)" },
          angleLines:{ color: "rgba(255,255,255,0.1)" },
          pointLabels:{ color: "#fff" },
          ticks:     { color: "#fff" }
        }
      },
      plugins: {
        legend: { labels: { color: "#fff" } }
      }
    }
  });
}
