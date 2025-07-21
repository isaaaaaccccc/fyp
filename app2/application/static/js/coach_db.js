async function updateCoaches() {
    const form = document.getElementById('coachFilter');
    const coachList = document.getElementById('coachList');
    const coachCount = document.getElementById('coachCount');
    
    const params = new URLSearchParams(new FormData(form));

    coachList.innerHTML = `
        <div id="loader" class="text-center my-5">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Loading…</span>
            </div>
        </div>`;
    const response = await fetch(`/api/coach?${params.toString()}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
    });

    const coaches = await response.json();
    coachList.innerHTML = '';

    if (coaches.length == 0) {
        coachList.innerHTML = `
            <div class="col-12 text-center py-5 text-muted">
                <p class="text-white fs-5">No coaches found matching your criteria.</p>
            </div>
        `;
    } else {
        coachCount.innerText = coaches.length;
        coaches.forEach(coach => {
            const card = document.createElement('div');
            card.className = 'col-xl-3 col-lg-4 col-md-6 col-sm-12';
    
            card.innerHTML = `
                <div class="card h-100" data-bs-toggle="modal" data-bs-target="#editModal" data-id="${coach.id}">
                    <div class="card-body">
                        <div class="card-title d-flex justify-content-between align-items-center">
                            <h5 class="fw-bold">${coach.name}</h5>
                            <span class="badge ms-auto ${coach.status === 'Full time' ? 'bg-success' : 'bg-danger'}">
                                ${coach.status.split(' ')[0].toUpperCase()}
                            </span>
                        </div>
                        <h6 class="card-subtitle mb-2 text-body-secondary">${coach.position}</h6>
    
                        <div class="mb-2">
                            <small class="fw-semibold">Branches:</small>
                            ${coach.assigned_branches.map(abbrv => `
                                <span class="badge bg-primary me-1">${abbrv}</span>
                            `).join('')}
                        </div>
    
                        <div class="mt-auto">
                            <small class="fw-semibold">Preferred Levels:</small>
                            ${coach.preferred_levels.map(level => `
                                <span class="badge ${level === 'BearyTots' ? 'Tots' : level} text-dark me-1">
                                    ${level}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
    
            coachList.appendChild(card);
        });
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('coachFilter');
    const resultCount = document.getElementById('searchResults');
    const coachList = document.getElementById('coachList');
    const nameField = document.getElementById('name');
    const cancelBtn = document.getElementById('cancelBtn');

    updateCoaches();

    form.addEventListener('change', updateCoaches);
    nameField.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            updateCoaches();
        };
    });
    cancelBtn.addEventListener('click', () => {
        form.reset();
        updateCoaches();
    });
});