// static/js/dashboard/uiToggles.js
document.addEventListener('DOMContentLoaded', () => {
  // Tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]')
          .forEach(el => new bootstrap.Tooltip(el));

  // KPI / Analytics / Timetable highlight toggles
  ['toggle-kpi','toggle-analytics','toggle-timetable']
    .forEach(id => {
      const btn = document.getElementById(id);
      btn && btn.addEventListener('click', () => btn.classList.toggle('is-active'));
    });

  // Scroll to Top
  const scrollBtn = document.getElementById('scrollToTopBtn');
  function toggleScrollBtn() {
    scrollBtn.classList.toggle('show', window.scrollY > 200);
  }
  window.addEventListener('scroll', toggleScrollBtn, { passive: true });
  scrollBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  toggleScrollBtn();
});
