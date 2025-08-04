// Constants
const days = ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]; // Removed Monday
const timeSlots = [];
for (let hour = 9; hour <= 19; hour++) {
    for (let minute = 0; minute < 60; minute += 30) {
        if (hour === 19 && minute > 0) break;
        const timeStr = hour.toString().padStart(2, '0') + minute.toString().padStart(2, '0');
        timeSlots.push(timeStr);
    }
}

// Branch opening hours
const branchHours = {
    "Monday": { open: null, close: null }, // Closed
    "Tuesday": { open: "1500", close: "1900" }, // 3pm - 7pm
    "Wednesday": { open: "1000", close: "1900" }, // 10am - 7pm
    "Thursday": { open: "1000", close: "1900" }, // 10am - 7pm
    "Friday": { open: "1000", close: "1900" }, // 10am - 7pm
    "Saturday": { open: "0830", close: "1830" }, // 8:30am - 6:30pm
    "Sunday": { open: "0830", close: "1830" }  // 8:30am - 6:30pm
};

// Lunch break hours (weekdays only)
const lunchBreak = {
    start: "1200", // 12pm
    end: "1400"    // 2pm
};

// Global Variables
// This variable will handle the data that's to be saved to the database 
let data = {};
let draggedData = null;
let branchCapacities = {}; // Cache for branch max_classes values
let currentHighlightedSlot = null; // Track the currently highlighted slot

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

function renderBranchTimetable(branch, branchData, timetableDiv) {
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
    table.id = `timetable-${branch}`; // Add an ID to the table for easy reference
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
        dayHeader.dataset.day = day;
        dayHeader.colSpan = coaches.length;
        dayRow.appendChild(dayHeader);
        
        coaches.forEach((coach, coachIdx) => {
            const coachHeader = document.createElement('th');
            coachHeader.textContent = coach;
            coachHeader.className = 'coach-header';
            coachHeader.dataset.day = day;
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
        row.dataset.timeSlot = timeSlot;
        row.dataset.timeIndex = timeIdx;
        
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
                cell.dataset.timeSlot = timeSlot;

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

async function renderTimetable(data) {
    const mainContainer = document.getElementById('timetableDiv');
    mainContainer.innerHTML = '';
    
    // Reset the currently highlighted slot
    currentHighlightedSlot = null;
    
    // Add defensive check at the beginning
    if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
        mainContainer.innerHTML = '<div class="alert alert-warning">No timetable data available.</div>';
        return;
    }

    // Fetch branch capacities if not already cached
    if (Object.keys(branchCapacities).length === 0) {
        try {
            const response = await fetch('/api/branch/');
            const result = await response.json();
            
            if (result.success) {
                result.branches.forEach(branch => {
                    branchCapacities[branch.abbrv] = branch.max_classes;
                });
            }
        } catch (error) {
            console.error('Error fetching branch capacities:', error);
        }
    }

    // For each branch, show capacity followed by timetable
    for (const branch of Object.keys(data)) {
        const branchData = data[branch];
        
        if (!branchData || !branchData.coaches || !branchData.schedule) {
            continue;
        }
        
        // Container for this branch's content
        const branchContainer = document.createElement('div');
        branchContainer.className = 'branch-container mb-4';
        branchContainer.dataset.branch = branch;
        mainContainer.appendChild(branchContainer);
        
        // 1. Generate spare capacity section for this branch
        await generateSpareCapacitySection(branch, branchData, branchContainer);
        
        // 2. Render timetable for this branch
        renderBranchTimetable(branch, branchData, branchContainer);
    }
}

function addClass(branch, day, coach, time, level, duration) {
    const timeIdx = timeSlots.indexOf(time);
    if (timeIdx === -1) {
        console.error(`${time} is not a valid timeslot`);
        return;
    }
    
    // Ensure minimum duration of 1 hour (2 time slots)
    const actualDuration = Math.max(2, duration || 2);
    
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
        duration: actualDuration  // Ensure minimum duration of 1 hour
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

// Re-render just the capacity section for a specific branch
async function updateCapacitySection(branch) {
    if (!data[branch]) return;
    
    const branchContainer = document.querySelector(`.branch-container[data-branch="${branch}"]`);
    if (!branchContainer) return;
    
    // Remove old capacity section
    const oldCapacitySection = branchContainer.querySelector('.capacity-details');
    if (oldCapacitySection) {
        oldCapacitySection.remove();
    }
    
    // Generate new capacity section
    await generateSpareCapacitySection(branch, data[branch], branchContainer);
    
    // Move the new capacity section to the top
    const capacitySection = branchContainer.querySelector('.capacity-details');
    if (capacitySection) {
        branchContainer.prepend(capacitySection);
    }
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

// Check if a time is within branch opening hours
function isWithinOpeningHours(day, timeSlot) {
    const dayHours = branchHours[day];
    
    // If the branch is closed on this day
    if (!dayHours.open || !dayHours.close) {
        return false;
    }
    
    // Check if time is within operating hours
    if (timeSlot < dayHours.open || timeSlot >= dayHours.close) {
        return false;
    }
    
    // Check for lunch break (weekdays only: Tuesday to Friday)
    if (['Tuesday', 'Wednesday', 'Thursday', 'Friday'].includes(day)) {
        if (timeSlot >= lunchBreak.start && timeSlot < lunchBreak.end) {
            return false;
        }
    }
    
    return true;
}

// Check if a time is during lunch break
function isDuringLunchBreak(day, timeSlot) {
    if (!['Tuesday', 'Wednesday', 'Thursday', 'Friday'].includes(day)) {
        return false;
    }
    
    return (timeSlot >= lunchBreak.start && timeSlot < lunchBreak.end);
}

// Get utilization badge class based on percentage
function getUtilizationBadgeClass(percentage) {
    if (percentage < 30) return 'badge-danger';
    if (percentage < 60) return 'badge-warning';
    return 'badge-success';
}

// Calculate the utilization percentage for a day
function calculateDayUtilization(day, capacityByDayAndTime) {
    let totalSlots = 0;
    let usedSlots = 0;
    
    // Count only slots within opening hours
    for (const slot in capacityByDayAndTime[day]) {
        if (capacityByDayAndTime[day][slot].available) {
            const maxAllowed = capacityByDayAndTime[day][slot].spare + capacityByDayAndTime[day][slot].used;
            totalSlots += maxAllowed;
            usedSlots += capacityByDayAndTime[day][slot].used;
        }
    }
    
    if (totalSlots === 0) return 0;
    return Math.round((usedSlots / totalSlots) * 100);
}

// Calculate the utilization percentage for the entire week (excluding Monday)
function calculateWeekUtilization(capacityByDayAndTime) {
    let totalSlots = 0;
    let usedSlots = 0;
    
    // Count all days except Monday
    for (const day of days) {
        for (const slot in capacityByDayAndTime[day]) {
            if (capacityByDayAndTime[day][slot].available) {
                const maxAllowed = capacityByDayAndTime[day][slot].spare + capacityByDayAndTime[day][slot].used;
                totalSlots += maxAllowed;
                usedSlots += capacityByDayAndTime[day][slot].used;
            }
        }
    }
    
    if (totalSlots === 0) return 0;
    return Math.round((usedSlots / totalSlots) * 100);
}

// Find available one-hour slots (2 consecutive 30-min slots)
function findAvailableHourSlots(day, capacityByDayAndTime) {
    const availableHourSlots = [];
    
    // Check each possible starting time slot
    for (let i = 0; i < timeSlots.length - 1; i++) {
        const startSlot = timeSlots[i];
        const endSlot = timeSlots[i + 1];
        
        // Check if both slots are available and have capacity
        if (capacityByDayAndTime[day][startSlot].available && 
            capacityByDayAndTime[day][startSlot].spare > 0 &&
            capacityByDayAndTime[day][endSlot].available && 
            capacityByDayAndTime[day][endSlot].spare > 0) {
            
            // Take the minimum spare capacity between the two slots
            const minSpare = Math.min(
                capacityByDayAndTime[day][startSlot].spare, 
                capacityByDayAndTime[day][endSlot].spare
            );
            
            availableHourSlots.push({
                startSlot: startSlot,
                endSlot: endSlot,
                spare: minSpare,
                isDuringLunch: isDuringLunchBreak(day, startSlot) || isDuringLunchBreak(day, endSlot)
            });
        }
    }
    
    return availableHourSlots;
}

// Determine availability class based on spare slots
function getAvailabilityClass(spare) {
    if (spare === 0) return 'no-availability';
    if (spare === 1) return 'low-availability';
    if (spare <= 3) return 'medium-availability';
    return 'high-availability';
}

// Highlight a timeslot in the timetable
function highlightTimeslot(branch, day, timeSlot) {
    // Clear any existing highlight
    clearHighlightedTimeslot();
    
    // If clicking the same slot, just clear it and return
    if (currentHighlightedSlot && 
        currentHighlightedSlot.branch === branch && 
        currentHighlightedSlot.day === day && 
        currentHighlightedSlot.timeSlot === timeSlot) {
        currentHighlightedSlot = null;
        return;
    }
    
    // Find the table for this branch
    const table = document.getElementById(`timetable-${branch}`);
    if (!table) return;
    
    // Highlight the day header for this day
    const dayHeaders = table.querySelectorAll(`th[data-day="${day}"]`);
    dayHeaders.forEach(header => {
        header.classList.add('highlighted-day');
    });
    
    // Find all cells for this time slot and day
    const rows = table.querySelectorAll(`tbody tr[data-time-slot="${timeSlot}"]`);
    if (!rows.length) return;
    
    // Store the currently highlighted slot info
    currentHighlightedSlot = { branch, day, timeSlot };
    
    rows.forEach(row => {
        // Get all cells for this day
        const cells = row.querySelectorAll(`td[data-day="${day}"]`);
        cells.forEach(cell => {
            cell.classList.add('highlighted-timeslot');
        });
        
        // Highlight the time cell
        const timeCell = row.querySelector('td.time-slot');
        if (timeCell) {
            timeCell.classList.add('highlighted-timeslot-time');
        }
    });
    
    // Scroll the row into view
    rows[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Clear any highlighted timeslot
function clearHighlightedTimeslot() {
    if (!currentHighlightedSlot) return;
    
    // Remove highlight classes
    document.querySelectorAll('.highlighted-timeslot, .highlighted-timeslot-time, .highlighted-day').forEach(element => {
        element.classList.remove('highlighted-timeslot', 'highlighted-timeslot-time', 'highlighted-day');
    });
}

// Function to handle clicking on a timeslot badge
function handleTimeslotBadgeClick(e) {
    const badge = e.currentTarget;
    const branch = badge.dataset.branch;
    const day = badge.dataset.day;
    const timeSlot = badge.dataset.startSlot;
    
    highlightTimeslot(branch, day, timeSlot);
}

// Generate spare capacity display for a branch
async function generateSpareCapacitySection(branch, branchData, containerElement) {
    if (!containerElement) return;
    
    // Use cached branch capacities or default to 4
    const maxAllowed = branchCapacities[branch] || 4;
    
    // Create capacity object with day and timeslot structure
    const capacityByDayAndTime = {};
    
    // Initialize capacity structure for all days and timeslots
    days.forEach(day => {
        capacityByDayAndTime[day] = {};
        timeSlots.forEach(slot => {
            capacityByDayAndTime[day][slot] = {
                used: 0,
                spare: maxAllowed,
                available: isWithinOpeningHours(day, slot)
            };
        });
    });
    
    // Count used slots
    for (const day in branchData.schedule) {
        for (const coach in branchData.schedule[day]) {
            branchData.schedule[day][coach].forEach(classInfo => {
                if (!classInfo.start_time) return;
                
                const startIdx = timeSlots.indexOf(classInfo.start_time);
                const duration = classInfo.duration || 2;
                
                for (let i = 0; i < duration; i++) {
                    if ((startIdx + i) >= timeSlots.length) break;
                    
                    const slot = timeSlots[startIdx + i];
                    capacityByDayAndTime[day][slot].used++;
                    capacityByDayAndTime[day][slot].spare = maxAllowed - capacityByDayAndTime[day][slot].used;
                }
            });
        }
    }
    
    // Calculate week utilization
    const weekUtilization = calculateWeekUtilization(capacityByDayAndTime);
    
    // Create spare capacity display
    const branchCapacityDiv = document.createElement('div');
    branchCapacityDiv.className = 'capacity-details bg-dark text-white';
    
    // Branch title and legend
    const headerDiv = document.createElement('div');
    headerDiv.className = 'capacity-header';
    
    // Updated portion in generateSpareCapacitySection function
    const titleRow = document.createElement('div');
    titleRow.className = 'd-flex justify-content-between align-items-center';

    const branchTitle = document.createElement('h5');
    branchTitle.className = 'text-white mb-0';
    branchTitle.textContent = `${branch} - Available Capacity`;
    titleRow.appendChild(branchTitle);

    // Add week utilization badge with more spacing
    const utilizationBadge = document.createElement('span');
    utilizationBadge.className = 'week-utilization-badge badge';
    // Use the utility class directly instead of dynamic function
    utilizationBadge.classList.add(weekUtilization < 30 ? 'badge-danger' : weekUtilization < 60 ? 'badge-warning' : 'badge-success');
    utilizationBadge.textContent = `Week: ${weekUtilization}% Utilized`;
    titleRow.appendChild(utilizationBadge);

    headerDiv.appendChild(titleRow);
    
    // Add legend
    const legend = document.createElement('div');
    legend.className = 'capacity-legend';
    
    const highLegend = document.createElement('div');
    highLegend.className = 'legend-item';
    highLegend.innerHTML = '<span class="legend-color high-availability"></span> <span class="text-white">High Availability</span>';
    
    const mediumLegend = document.createElement('div');
    mediumLegend.className = 'legend-item';
    mediumLegend.innerHTML = '<span class="legend-color medium-availability"></span> <span class="text-white">Medium Availability</span>';
    
    const lowLegend = document.createElement('div');
    lowLegend.className = 'legend-item';
    lowLegend.innerHTML = '<span class="legend-color low-availability"></span> <span class="text-white">Low Availability (1 slot)</span>';
    
    const clickInfoLegend = document.createElement('div');
    clickInfoLegend.className = 'legend-item ms-auto';
    clickInfoLegend.innerHTML = '<small class="text-light"><i class="bi bi-info-circle"></i> Click on a timeslot to highlight it</small>';
    
    legend.appendChild(highLegend);
    legend.appendChild(mediumLegend);
    legend.appendChild(lowLegend);
    legend.appendChild(clickInfoLegend);
    
    headerDiv.appendChild(legend);
    branchCapacityDiv.appendChild(headerDiv);
    
    // Create days layout
    const daysList = document.createElement('div');
    daysList.className = 'row';
    
    for (const day of days) {
        const dayCol = document.createElement('div');
        dayCol.className = 'col-md-4 col-sm-6 mb-3';
        
        // Calculate day utilization
        const dayUtilization = calculateDayUtilization(day, capacityByDayAndTime);
        
        // Day header with utilization percentage
        const dayHeader = document.createElement('div');
        dayHeader.className = 'd-flex justify-content-between align-items-center mb-2';
        
        const dayTitle = document.createElement('h6');
        dayTitle.className = 'text-white m-0';
        dayTitle.textContent = day;
        dayHeader.appendChild(dayTitle);
        
        const utilizationBadge = document.createElement('span');
        utilizationBadge.className = `badge ${getUtilizationBadgeClass(dayUtilization)}`;
        utilizationBadge.textContent = `${dayUtilization}% Utilized`;
        dayHeader.appendChild(utilizationBadge);
        
        dayCol.appendChild(dayHeader);
        
        // Check if branch is closed on this day (should not happen since Monday is filtered out)
        if (!branchHours[day].open) {
            const closedNotice = document.createElement('div');
            closedNotice.className = 'closed-notice text-secondary';
            closedNotice.textContent = 'Branch Closed';
            dayCol.appendChild(closedNotice);
            daysList.appendChild(dayCol);
            continue;
        }
        
        // Find available 1-hour slots
        const availableHourSlots = findAvailableHourSlots(day, capacityByDayAndTime);
        
        if (availableHourSlots.length === 0) {
            const noSlotsMsg = document.createElement('div');
            noSlotsMsg.className = 'closed-notice text-secondary';
            noSlotsMsg.textContent = 'No available capacity';
            dayCol.appendChild(noSlotsMsg);
        } else {
            const slotsList = document.createElement('div');
            slotsList.className = 'capacity-list';
            
            // Add each available 1-hour slot
            availableHourSlots.forEach(slotInfo => {
                const slotBadge = document.createElement('span');
                
                // Style based on availability and lunch break
                if (slotInfo.isDuringLunch) {
                    slotBadge.className = 'capacity-badge badge lunch-break clickable-badge';
                } else if (slotInfo.spare === 1) {
                    slotBadge.className = 'capacity-badge badge low-availability clickable-badge';
                } else if (slotInfo.spare <= 3) {
                    slotBadge.className = 'capacity-badge badge medium-availability clickable-badge';
                } else {
                    slotBadge.className = 'capacity-badge badge high-availability clickable-badge';
                }
                
                // Add time range and spare slots
                slotBadge.textContent = `${formatTime(slotInfo.startSlot)}-${formatTime(slotInfo.endSlot)}: ${slotInfo.spare} slot${slotInfo.spare > 1 ? 's' : ''}`;
                
                // Add data attributes for click handling
                slotBadge.dataset.branch = branch;
                slotBadge.dataset.day = day;
                slotBadge.dataset.startSlot = slotInfo.startSlot;
                slotBadge.dataset.endSlot = slotInfo.endSlot;
                
                // Add click event handler
                slotBadge.addEventListener('click', handleTimeslotBadgeClick);
                
                slotsList.appendChild(slotBadge);
            });
            
            dayCol.appendChild(slotsList);
        }
        
        daysList.appendChild(dayCol);
    }
    
    branchCapacityDiv.appendChild(daysList);
    containerElement.appendChild(branchCapacityDiv);
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
    
    // Store original branch for recalculating capacity
    const originalBranch = transferedData.branch;
    
    // Remove class from original position
    removeClass(originalBranch, transferedData.day, transferedData.coach, timeSlots[transferedData.startIdx]);
    
    // Add class to new position
    addClass(branch, day, coach, timeSlots[timeIdx], transferedData.level, transferedData.duration);
    
    // If you want to optimize and only update capacity sections without full re-render:
    // updateCapacitySection(originalBranch);
    // if (branch !== originalBranch) {
    //     updateCapacitySection(branch);
    // }
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
                // Get branch information for recalculating capacity
                const branch = draggedData.branch;
                
                // Remove the class
                removeClass(
                    branch, 
                    draggedData.day, 
                    draggedData.coach, 
                    timeSlots[draggedData.startIdx]
                );
                
                // If you want to optimize and only update capacity section without full re-render:
                // updateCapacitySection(branch);
            }
        });
    }

    // Add event listener for clicking outside of timeslot badges to clear highlights
    document.addEventListener('click', function(e) {
        // If we clicked on a non-badge and non-highlighted element, clear the highlight
        if (!e.target.closest('.clickable-badge') && !e.target.closest('.highlighted-timeslot') && 
            !e.target.closest('.highlighted-timeslot-time') && !e.target.closest('.highlighted-day')) {
            clearHighlightedTimeslot();
        }
    });

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

    // Fetch branch capacities on initial load
    try {
        const response = await fetch('/api/branch/');
        const result = await response.json();
        
        if (result.success) {
            result.branches.forEach(branch => {
                branchCapacities[branch.abbrv] = branch.max_classes;
            });
        }
    } catch (error) {
        console.error('Error fetching branch capacities:', error);
    }
});