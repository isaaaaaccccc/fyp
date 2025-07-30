// Constants
const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const timeSlots = [];
for (let hour = 9; hour <= 19; hour++) {
    for (let minute = 0; minute < 60; minute += 30) {
        if (hour === 19 && minute > 0) break;
        const timeStr = hour.toString().padStart(2, '0') + minute.toString().padStart(2, '0');
        timeSlots.push(timeStr);
    }
}

// Global Variables
// This variable will handle the data that's to be saved to the database 
let data = {};
let draggedData = null;

// Functions
function formatTime(timeStr) {
    if (!timeStr) return '';
    
    const padded = timeStr.toString().padStart(4, '0');
    const hours = parseInt(padded.slice(0, 2), 10);
    const minutes = padded.slice(2, 4);

    const period = hours >= 12 ? 'pm' : 'am';
    const hours12 = hours % 12 || 12;

    return `${hours12}:${minutes}${period}`;
}

function scheduleMatrix(schedule, coaches) {
    const matrix = {};
    coaches.forEach(coach => {
        matrix[coach] = new Array(timeSlots.length).fill(null);
    });

    if (!schedule) return matrix;

    for (const [coach, classes] of Object.entries(schedule)) {
        if (!Array.isArray(classes)) continue;
        
        classes.forEach(classInfo => {
            if (!classInfo || !classInfo.start_time) return;
            
            const startIdx = timeSlots.indexOf(classInfo.start_time);
            if (startIdx === -1) return;

            const duration = classInfo.duration || 2;  // Default to 2 time slots (1 hour)
            
            for (let i = 0; i < duration; i++) {
                if ((startIdx + i) >= timeSlots.length) break;

                matrix[coach][startIdx + i] = {
                    name: classInfo.name || 'Unknown',
                    startIdx: startIdx,
                    position: i,
                    duration: duration,
                };
            }
        });
    }

    return matrix;
}

function createClassBlock(classInfo, branch, day, coach, timeIdx) {
    const classBlock = document.createElement('div');
    classBlock.className = `class-block ${classInfo.name}`;
    classBlock.textContent = classInfo.name;
    classBlock.draggable = true;
    
    classBlock.dataset.branch = branch;
    classBlock.dataset.day = day;
    classBlock.dataset.coach = coach;
    classBlock.dataset.level = classInfo.name;
    classBlock.dataset.duration = classInfo.duration;
    classBlock.dataset.startIdx = timeIdx;
    classBlock.style.height = `calc(${classInfo.duration * 100}% - 16px)`;

    classBlock.addEventListener('dragstart', handleDragStart);
    classBlock.addEventListener('dragend', handleDragEnd);

    return classBlock;
}

function renderBranchTimetable(branch, branchData) {
    const coachOrder = branchData.coaches || [];
    // Sort coach names alphabetically
    coachOrder.sort((a, b) => a.localeCompare(b));
    
    const matrix = {};
    days.forEach(day => {
        if (!branchData.schedule[day]) {
            matrix[day] = {};
            return;
        }
        matrix[day] = scheduleMatrix(branchData.schedule[day], coachOrder);
    });

    const responsiveDiv = document.createElement('div');
    responsiveDiv.className = 'table-responsive';

    const table = document.createElement('table');
    table.className = 'table table-bordered table-secondary';
    responsiveDiv.appendChild(table);

    const thead = document.createElement('thead');
    const tbody = document.createElement('tbody');

    const dayRow = document.createElement('tr');
    const coachRow = document.createElement('tr');

    const timeHeader = document.createElement('th');
    timeHeader.textContent = 'Timing';
    timeHeader.rowSpan = 2;
    timeHeader.className = 'time-slot separator';
    dayRow.appendChild(timeHeader);

    // Create table header, containing day and coaches working
    for (const day of days) {
        if (!branchData.schedule[day]) continue;
        
        const coaches = Object.keys(branchData.schedule[day]).filter(coach => coachOrder.includes(coach)).sort();
        if (coaches.length === 0) continue;
        
        const dayHeader = document.createElement('th');
        dayHeader.className = 'day-header separator';
        dayHeader.textContent = day;
        dayHeader.colSpan = coaches.length;
        dayRow.appendChild(dayHeader);
        
        coaches.forEach((coach, coachIdx) => {
            const coachHeader = document.createElement('th');
            coachHeader.textContent = coach;
            coachHeader.className = 'coach-header';
            if (coachIdx === coaches.length - 1) coachHeader.classList.add('separator');

            coachRow.appendChild(coachHeader);
        });
    }

    // Remove separator from last day-header if it exists
    if (dayRow.lastChild && dayRow.lastChild.classList) {
        dayRow.lastChild.classList.remove('separator');
    }

    // Create timetable body
    for (const [timeIdx, timeSlot] of timeSlots.slice(0, -1).entries()) {
        const row = document.createElement('tr');
        
        const timeCell = document.createElement('td');
        timeCell.textContent = `${formatTime(timeSlot)} - ${formatTime(timeSlots[timeIdx + 1])}`;
        timeCell.className = 'time-slot separator';
        row.appendChild(timeCell);
        
        for (const day of days) {
            if (!branchData.schedule[day]) continue;

            const coaches = Object.keys(branchData.schedule[day]).filter(coach => coachOrder.includes(coach)).sort();
            if (coaches.length === 0) continue;
            
            coaches.forEach((coach, coachIdx) => {
                
                const cell = document.createElement('td');
                cell.className = 'class-cell';
                cell.dataset.branch = branch;
                cell.dataset.day = day;
                cell.dataset.coach = coach;
                cell.dataset.timeIdx = timeIdx;

                cell.addEventListener('dragover', handleDragOver);
                cell.addEventListener('dragenter', handleDragEnter);
                cell.addEventListener('dragleave', handleDragLeave);
                cell.addEventListener('drop', handleDrop);

                if (coachIdx === coaches.length - 1) cell.classList.add('separator');
                row.appendChild(cell);
                
                if (!matrix[day][coach]) return; // Skip if no schedule for this coach
                
                const classInfo = matrix[day][coach][timeIdx];  // Check if a class exists for the coach on this day and time
                if (!classInfo || classInfo.position !== 0) return;

                const classBlock = createClassBlock(classInfo, branch, day, coach, timeIdx);

                cell.appendChild(classBlock);
            });
        }
        tbody.appendChild(row);
    }

    table.appendChild(thead);
    table.appendChild(tbody);
    thead.appendChild(dayRow);
    thead.appendChild(coachRow);
    timetableDiv.appendChild(responsiveDiv);
    
    // Add branch title
    const branchTitle = document.createElement('h3');
    branchTitle.className = 'mt-4 mb-2';
    branchTitle.textContent = branch;
    responsiveDiv.insertBefore(branchTitle, table);
}

function renderTimetable(data) {
    const timetableDiv = document.getElementById('timetableDiv');
    timetableDiv.innerHTML = '';
    
    // Add defensive check at the beginning
    if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
        timetableDiv.innerHTML = '<div class="alert alert-warning">No timetable data available.</div>';
        return;
    }

    for (const branch of Object.keys(data)) {
        const branchData = data[branch];
        
        // Add defensive check for branch data
        if (!branchData || !branchData.coaches || !branchData.schedule) {
            continue;
        }
        
        renderBranchTimetable(branch, branchData);
    }
}

function addClass(branch, day, coach, time, level, duration) {
    const timeIdx = timeSlots.indexOf(time);
    if (timeIdx === -1) {
        console.error(`${time} is not a valid timeslot`);
        return;
    }
    
    // Initialize data structure if needed
    if (!data[branch]) {
        data[branch] = {
            coaches: [coach],
            schedule: {}
        };
    }
    
    if (!data[branch].schedule[day]) {
        data[branch].schedule[day] = {};
    }
    
    if (!data[branch].coaches.includes(coach)) {
        data[branch].coaches.push(coach);
    }
    
    if (!data[branch].schedule[day][coach]) {
        data[branch].schedule[day][coach] = [];
    }
    
    // Add class
    data[branch].schedule[day][coach].push({
        name: level,
        start_time: time,
        duration: duration || 2  // Default to 2 slots (1 hour)
    });
    
    // Re-render timetable
    renderTimetable(data);
}

function removeClass(branch, day, coach, time) {
    if (!branch || !day || !coach || !time) return;
    
    const timeIdx = timeSlots.indexOf(time);
    if (timeIdx === -1) {
        console.error(`${time} is not a valid timeslot`);
        return;
    }
    
    const classes = data?.[branch]?.schedule?.[day]?.[coach];
    if (!classes) return;

    const classIdx = classes.findIndex(cls => cls.start_time === time);
    if (classIdx === -1) return;

    classes.splice(classIdx, 1);
    
    // Clean up empty structures
    if (classes.length === 0) {
        delete data[branch].schedule[day][coach];
    }
    
    if (Object.keys(data[branch].schedule[day]).length === 0) {
        delete data[branch].schedule[day];
    }
    
    // Re-render timetable
    renderTimetable(data);
}

function updateCell(branch, day, coach, timeIdx) {
    // Just re-render entire timetable for now
    renderTimetable(data);
}

function canDropAt(draggedData, targetCell) {
    if (!draggedData || !targetCell) return false;
    
    const targetBranch = targetCell.dataset.branch;
    const targetDay = targetCell.dataset.day;
    const targetCoach = targetCell.dataset.coach;
    const targetTimeIdx = parseInt(targetCell.dataset.timeIdx);

    const { duration, day: classDay, branch: classBranch, coach: classCoach } = draggedData;
    const startIdx = parseInt(draggedData.startIdx);
    
    if (targetBranch !== classBranch) return false; 

    // Check if there's enough space
    for (let i = 0; i < duration; i++) {
        const nextCellIdx = targetTimeIdx + i;
        if (nextCellIdx >= timeSlots.length) return false;
        
        const selector = `.class-cell[data-branch="${targetBranch}"][data-day="${targetDay}"][data-coach="${targetCoach}"][data-time-idx="${nextCellIdx}"] .class-block`;
        const nextCell = document.querySelector(selector);

        if (targetDay === classDay && targetCoach === classCoach && nextCellIdx === startIdx) continue;

        if (nextCell) return false;
    }
    
    return true;
}

// Drag and drop handlers
function handleDragStart(e) {
    this.classList.add('dragging');
    
    draggedData = {
        branch: this.dataset.branch,
        day: this.dataset.day,
        coach: this.dataset.coach,
        level: this.dataset.level,
        duration: this.dataset.duration,
        startIdx: this.dataset.startIdx
    };
    
    e.dataTransfer.setData('application/json', JSON.stringify(draggedData));
    e.dataTransfer.effectAllowed = 'move';
    
    // Show delete zone
    const deleteZone = document.getElementById('deleteZone');
    if (deleteZone) deleteZone.classList.add('active');
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    
    // Hide delete zone
    const deleteZone = document.getElementById('deleteZone');
    if (deleteZone) deleteZone.classList.remove('active');
    
    // Clear all drag effects
    document.querySelectorAll('.drag-valid, .drag-invalid').forEach(el => {
        el.classList.remove('drag-valid', 'drag-invalid');
    });
}

// Handle the style of the cells that the class block is being dragged over
function handleDragEnter(e) {
    e.preventDefault();

    if (e.target.classList.contains('class-cell')) {
        const valid = canDropAt(draggedData, e.target);
        e.target.classList.add(valid ? 'drag-valid' : 'drag-invalid');
    }
}

function handleDragLeave(e) {
    e.target.classList.remove('drag-valid', 'drag-invalid');
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
}

function handleDrop(e) {
    e.preventDefault();

    if (!e.dataTransfer) return;

    const transferedData = JSON.parse(e.dataTransfer.getData('application/json'));
    const target = e.target.closest('.class-cell');

    if (!canDropAt(transferedData, target)) {
        // Cannot drop here
        return;
    }

    const { branch, day, coach } = target.dataset;
    const timeIdx = parseInt(target.dataset.timeIdx);
    removeClass(branch, transferedData.day, transferedData.coach, timeSlots[transferedData.startIdx]);
    addClass(branch, day, coach, timeSlots[timeIdx], transferedData.level, transferedData.duration);
}

document.addEventListener('DOMContentLoaded', async () => {
    const timetableDiv = document.getElementById('timetableDiv');
    const generate_btn = document.getElementById('generateBtn');
    const save_btn = document.getElementById('saveBtn');
    const deleteZone = document.getElementById('deleteZone');

    // Set up delete zone
    if (deleteZone) {
        deleteZone.addEventListener('dragover', e => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            deleteZone.classList.add('dragover');
        });
        
        deleteZone.addEventListener('dragleave', () => {
            deleteZone.classList.remove('dragover');
        });
        
        deleteZone.addEventListener('drop', e => {
            e.preventDefault();
            deleteZone.classList.remove('dragover', 'active');
            
            if (draggedData) {
                removeClass(
                    draggedData.branch, 
                    draggedData.day, 
                    draggedData.coach, 
                    timeSlots[draggedData.startIdx]
                );
            }
        });
    }

    generate_btn.addEventListener('click', async () => {
        timetableDiv.innerHTML = `
            <div class="d-flex justify-content-center align-items-center">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <span class="ms-2">Generating timetable...</span>
            </div>`;

        const formEl = document.querySelector('#collapseConfig form');
        const formData = new FormData(formEl);
        const config = {};

        for (const [key, value] of formData.entries()) {
            // Convert to number if it looks numeric
            config[key] = isNaN(value) ? value : Number(value);
        }
        console.log(config)

        try {
            const response = await fetch(`/api/timetable/generate/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            data = await response.json();
            if (!response.ok) {
                console.log(response)
                throw new Error(`Server returned ${response.status}: ${response.statusText}, ${data.message}`);
            }
            
            renderTimetable(data);
        } catch (error) {
            console.error("Error generating timetable:", error);
            timetableDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> ${error.message || "Failed to generate timetable"}
                </div>
                <button id="retryBtn" class="btn btn-primary">Retry</button>
            `;
            
            document.getElementById('retryBtn')?.addEventListener('click', () => {
                generate_btn.click();
            });
        }
    });

    save_btn.addEventListener('click', async () => {
        if (!data || Object.keys(data).length === 0) {
            alert('No timetable data to save!');
            return;
        }

        console.log(data)

        try {
            const response = await fetch('/api/timetable/save/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                alert('Timetable saved successfully!');
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error saving timetable:', error);
            alert('Error saving timetable. Please try again.');
        }
    });
});