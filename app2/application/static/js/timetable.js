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
// This variable will handle the data thats to be saved to the database 
let data = {};  

// Functions
function formatTime(timeStr) {
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

    for (const [coach, classes] of Object.entries(schedule)) {
        classes.forEach(classInfo => {
            const startIdx = timeSlots.indexOf(classInfo.start_time)
            if (startIdx === -1) return;

            for (let i = 0; i < classInfo.duration; i++) {
                if ((startIdx + i) >= timeSlots.length) break;

                matrix[coach][startIdx + i] = {
                    name: classInfo.name,
                    startIdx: startIdx,
                    position: i,
                    duration: classInfo.duration,
                };
            }
        })
    }

    return matrix
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

function renderTimetable(data) {
    const timetableDiv = document.getElementById('timetableDiv');
    
    timetableDiv.innerHTML = '';
    for (const branch of Object.keys(data)) {
        const { coaches: coachOrder, schedule } = data[branch];
        coachOrder.sort((a, b) => a.localeCompare(b));
        
        const matrix = {}
        days.forEach(day => {
            matrix[day] = scheduleMatrix(schedule[day] || {}, coachOrder);
        });

        const table = document.createElement('table');
        table.className = 'table table-bordered table-secondary';

        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');

        const dayRow = document.createElement('tr');
        const coachRow = document.createElement('tr');

        const timeHeader = document.createElement('th');
        timeHeader.textContent = 'Timimg';
        timeHeader.rowSpan = 2;
        timeHeader.className = 'time-slot separator';
        dayRow.appendChild(timeHeader)

        // Create table header, containing day and coaches working
        for (const day of days) {
            if (!schedule[day]) continue;
            
            const num_coaches = Object.keys(schedule[day]).length;  // Number of assigned coaches that day
            const dayHeader = document.createElement('th');
            dayHeader.className = 'day-header separator';
            dayHeader.textContent = day;
            dayHeader.colSpan = Object.keys(schedule[day]).length
            dayRow.appendChild(dayHeader);
            
            const coaches = Object.keys(schedule[day]).filter(coach => coachOrder.includes(coach)).sort();
            for (const [coachIdx, coach] of coaches.entries()) {
                const coachHeader = document.createElement('th');
                coachHeader.textContent = coach;
                coachHeader.className = 'coach-header';
                if (coachIdx === coaches.length - 1) coachHeader.classList.add('separator');

                coachRow.appendChild(coachHeader);
            }
        }

        // Remove separator from last day-header
        dayRow.lastChild.classList.remove('separator')

        // Create timetable body
        for (const [timeIdx, timeSlot] of timeSlots.slice(0, -1).entries()) {
            const row = document.createElement('tr');
            
            const timeCell = document.createElement('td');
            timeCell.textContent = `${formatTime(timeSlot)} - ${formatTime(timeSlots[timeIdx + 1])}`;
            timeCell.className = 'time-slot separator';
            row.appendChild(timeCell);
            for (const day of days) {
                if (!schedule[day]) continue;

                const coaches = Object.keys(schedule[day]).filter(coach => coachOrder.includes(coach)).sort();
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
        timetableDiv.appendChild(table)
    }
}

function removeClass(branch, day, coach, time) {
    const timeIdx = timeSlots.indexOf(time);
    if (!timeIdx) throw new Error(`${time} is not a valid timeslot`);
    
    const classes = data?.[branch]?.schedule?.[day]?.[coach];
    if (!classes) return;

    const classIdx = classes.findIndex(cls => cls.start_time === time);
    if (classIdx === -1) return;


    console.log(branch, day, coach, timeIdx)
    classes.splice(classIdx, 1);
    updateCell(branch, day, coach, timeIdx);
}

function addClass(branch, day, coach, time, level, duration) {
    const timeIdx = timeSlots.indexOf(time);
    if (!timeIdx) throw new Error(`${time} is not a valid timeslot`);
    if (!data[branch]) data[branch] = {coaches: [], schedule: {}};
    if (!data[branch].schedule[day]) data[branch].schedule[day] = {};
    if (!data[branch].schedule[day][coach]) data[branch].schedule[day][coach] = [];

    const classInfo = {
        name: level,
        start_time: time,
        duration: duration
    };

    data[branch].schedule[day][coach].push(classInfo);
    updateCell(branch, day, coach, timeIdx, classInfo);
}

// Update a single cell
// if no classInfo is passed, the contents of the cell get removed 
function updateCell(branch, day, coach, timeIdx, classInfo=null) {
    const cell = document.querySelector(`[data-day="${day}"][data-coach="${coach}"][data-time-idx="${timeIdx}"]`);
    if (!cell) return;

    cell.innerHTML = '';

    if (!classInfo) return;

    const classBlock = createClassBlock(classInfo, branch, day, coach, timeIdx)
    cell.appendChild(classBlock);
}

// Drag Helper functions

function canDropAt(transferedData, target) {
    const { branch, day, coach } = target.dataset;
    const timeIdx = parseInt(target.dataset.timeIdx);
    const { duration, day: classDay, branch: classBranch, coach: classCoach } = transferedData;
    const startIdx = parseInt(transferedData.startIdx);

    // Check if it is placed at the very end of the day
    if (timeIdx + duration >= timeSlots.length) return false;

    // Check if is from the same branch
    if (branch !== classBranch) return false;

    const daySchedule = data[branch].schedule[day] || {};
    const coaches = Object.keys(daySchedule);
    const matrix = scheduleMatrix(daySchedule, coaches);

    for (let i = 0; i < duration; i++) {
        const slotIndex = timeIdx + i;
        if (matrix[coach] && matrix[coach][slotIndex] !== null) {
            const existingClass = matrix[coach][slotIndex];

            // Skip check for itself
            if (day === classDay && coach === classCoach && existingClass.startIdx === startIdx) continue;
            
            return false;
        }
    }

    return true;

}

// Drag Events
/*
The drag data store has different modes depending on when you access it:

On dragstart event it's on read/write mode.
On drop event, it's in read only mode.
And on all other events, it's in protected mode.

Protected mode is defined this way:

Protected mode: For all other events. 
The formats and kinds in the drag data store list of items representing dragged data can be enumerated, 
but the data itself is unavailable and no new data can be added.
*/

// Workaround for no access to data
let draggedElement;
let draggedData;

function handleDragStart(e) {
    classBlock = e.target;

    const transferedData = {
        branch: e.target.dataset.branch,
        level: e.target.dataset.level,
        duration: parseInt(e.target.dataset.duration),
        day: e.target.dataset.day,
        coach: e.target.dataset.coach,
        startIdx: e.target.dataset.startIdx
    };

    e.target.classList.add('dragging');
    e.dataTransfer.setData('application/json', JSON.stringify(transferedData));
    e.dataTransfer.setData('text/html', e.target.outerHTML);

    draggedData = transferedData;
    draggedElement = e.target.outerHTML;
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.drag-valid, .drag-invalid').forEach(el => el.classList.remove('drag-valid', 'drag-invalid'));
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
        // alert('Cannot drop here - not enough space or slot is occupied!');
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

    generate_btn.addEventListener('click', async () => {
        timetableDiv.innerHTML = `
            <div class="d-flex justify-content-center align-items-center">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>`;

        const response = await fetch(`/api/generate`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        data = await response.json();
        renderTimetable(data)
    });

    save_btn.addEventListener('click', async () => {
        if (!data || Object.keys(data).length === 0) {
            alert('No timetable data to save!');
            return;
        }

        try {
            const response = await fetch('/api/save', {
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