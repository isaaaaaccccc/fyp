// canonical Mon→Sun order
const WEEK_DAYS = [
  "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
];

document.addEventListener('DOMContentLoaded', () => {
  const loader             = document.getElementById('loader');
  const dayFilterContainer = document.getElementById('day-filter-container');
  const dayFilter          = document.getElementById('day-filter');
  const summaryCards       = document.getElementById('summary-cards');
  const chartContainer     = document.getElementById('dashboard-container');
  const ttSection          = document.getElementById('timetable-section');
  const ttBranchSelect     = document.getElementById('tt-branch-select');
  const ttContainer        = document.getElementById('timetable-container');

  console.log('▶ dashboard.js initializing');

  fetch('/api/generate')
    .then(res => {
      console.log('▶ fetch /api/generate status', res.status);
      if (!res.ok) throw new Error(res.statusText);
      return res.json();
    })
    .then(data => {
      console.log('▶ data received:', data);

      // reveal UI
      loader.style.display             = 'none';
      dayFilterContainer.style.display = 'block';
      summaryCards.style.display       = 'flex';
      chartContainer.style.display     = 'flex';
      ttSection.style.display          = 'block';

      // initial render
      renderSummary(summaryCards, data, dayFilter.value);
      renderCharts(chartContainer, data);
      setupTimetable(ttBranchSelect, data, ttContainer);

      // re-render summary on day change
      dayFilter.addEventListener('change', () => {
        console.log('▶ day filter:', dayFilter.value);
        renderSummary(summaryCards, data, dayFilter.value);
      });

      // switch timetable on branch change
      ttBranchSelect.addEventListener('change', () => {
        renderTimetable(ttContainer, data[ttBranchSelect.value]);
      });
    })
    .catch(err => {
      console.error('❌ Dashboard load error:', err);
      loader.innerHTML = `<p class="text-danger">Failed to load: ${err.message}</p>`;
    });
});

/**
 * Summary cards showing # of coaches, filtered by day.
 */
function renderSummary(container, data, day) {
  container.innerHTML = '';
  Object.entries(data).forEach(([branch, info]) => {
    let count;
    if (day === 'All') {
      count = info.coaches.length;
    } else {
      const sched = info.schedule[day] || {};
      count = Object.keys(sched).length;
    }

    const col = document.createElement('div');
    col.className = 'col-6 col-md-4 col-lg-2 mb-3';
    col.innerHTML = `
      <div class="card text-center h-100">
        <div class="card-body">
          <h5 class="card-title">${branch}</h5>
          <p class="display-6 mb-0">${count}</p>
          <small class="text-muted">coaches</small>
        </div>
      </div>`;
    container.appendChild(col);
  });
}

/**
 * One bar-chart per branch with per-coach filter.
 */
function renderCharts(container, data) {
  container.innerHTML = '';
  const entries = Object.entries(data);
  const pct     = (100 / entries.length) + '%';

  entries.forEach(([branch, info]) => {
    // flex‐item wrapper
    const col = document.createElement('div');
    Object.assign(col.style, {
      flex:     `0 0 ${pct}`,
      maxWidth: pct,
      padding:  '0 .5rem',
      minWidth: '0'
    });
    col.classList.add('mb-5','d-flex','flex-column');

    // branch header
    const hdr = document.createElement('h4');
    hdr.classList.add('text-center');
    hdr.textContent = branch;
    col.appendChild(hdr);

    // coach filter dropdown
    const filter = document.createElement('select');
    filter.className = 'form-select form-select-sm mb-2';
    filter.innerHTML = `<option value="All">All Coaches</option>` +
      info.coaches.map(c => `<option value="${c}">${c}</option>`).join('');
    col.appendChild(filter);

    // chart container with fixed height
    const wrapper = document.createElement('div');
    Object.assign(wrapper.style, {
      position: 'relative',
      width:    '100%',
      height:   '300px'
    });
    col.appendChild(wrapper);

    // canvas element
    const canvas   = document.createElement('canvas');
    const canvasId = `chart-${branch.replace(/\s+/g, '-')}`;
    canvas.id      = canvasId;
    wrapper.appendChild(canvas);

    container.appendChild(col);

    // initial draw
    const chart = buildChart(canvasId, info, 'All');

    // update on coach select
    filter.addEventListener('change', () => {
      buildChart(canvasId, info, filter.value, chart);
    });
  });
}

/**
 * Creates or updates a Chart.js bar chart for a given coach.
 */
function buildChart(canvasId, info, coach, existingChart) {
  const days = WEEK_DAYS;
  const counts = days.map(day => {
    const sched = info.schedule[day] || {};
    if (coach === 'All') {
      return Object.values(sched).reduce((sum, sessions) => sum + sessions.length, 0);
    }
    return (sched[coach] || []).length;
  });

  const ctx = document.getElementById(canvasId).getContext('2d');

  if (existingChart) {
    existingChart.data.labels = days;
    existingChart.data.datasets[0].data = counts;
    existingChart.data.datasets[0].label = coach === 'All'
      ? 'Sessions / Day'
      : `${coach} Sessions`;
    existingChart.update();
    return existingChart;
  }

  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels: days,
      datasets: [{
        label: coach === 'All' ? 'Sessions / Day' : `${coach} Sessions`,
        data: counts
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { title: { display: true, text: 'Day of Week' } },
        y: { beginAtZero: true, title: { display: true, text: 'Sessions' } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

/**
 * Populate branch dropdown and render initial timetable.
 */
function setupTimetable(selectEl, data, container) {
  selectEl.innerHTML = Object.keys(data)
    .map(b => `<option value="${b}">${b}</option>`)
    .join('');
  renderTimetable(container, data[selectEl.value]);
}

/**
 * Render a one‐row timetable table for a single branch.
 */
function renderTimetable(container, branchInfo) {
  let html = '<table class="table table-bordered"><thead><tr>';
  WEEK_DAYS.forEach(day => {
    html += `<th>${day}</th>`;
  });
  html += '</tr></thead><tbody><tr>';

  WEEK_DAYS.forEach(day => {
    const daySched = branchInfo.schedule[day] || {};
    if (!Object.keys(daySched).length) {
      html += '<td class="align-top text-muted">—</td>';
    } else {
      html += '<td class="align-top">';
      Object.entries(daySched).forEach(([coach, sessions]) => {
        html += `<div><strong>${coach}</strong><ul class="mb-2 ps-3">`;
        sessions.forEach(s => {
          html += `<li>${s.name} (${formatTime(s.start_time)} • ${s.duration}h)</li>`;
        });
        html += '</ul></div>';
      });
      html += '</td>';
    }
  });

  html += '</tr></tbody></table>';
  container.innerHTML = html;
}

/** Format “1530” → “15:30” */
function formatTime(hhmm) {
  return hhmm.slice(0,2) + ':' + hhmm.slice(2);
}
