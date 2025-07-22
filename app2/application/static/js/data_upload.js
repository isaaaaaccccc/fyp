document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Data upload page loaded');
    
    const uploadZones = document.querySelectorAll('.upload-zone');
    const uploadForm = document.getElementById('uploadForm');
    const progressContainer = document.querySelector('.upload-progress');
    const progressBar = document.querySelector('.progress-bar');

    console.log('📊 Found upload zones:', uploadZones.length);
    console.log('📋 Found upload form:', !!uploadForm);

    // Initialize drag and drop for each upload zone
    uploadZones.forEach((zone, index) => {
        const targetField = zone.dataset.target;
        const fileInput = document.getElementById(targetField);
        const fileInfo = document.getElementById(targetField + '_info');

        console.log(`🎯 Zone ${index + 1}: target="${targetField}", input found: ${!!fileInput}, info found: ${!!fileInfo}`);

        if (!fileInput) {
            console.error(`❌ File input not found for target: ${targetField}`);
            return;
        }

        // Click to browse
        zone.addEventListener('click', (e) => {
            console.log('🖱️ Upload zone clicked:', targetField);
            if (e.target === zone || e.target.closest('i') || e.target.closest('.upload-zone-text') || e.target.closest('.upload-zone-subtext')) {
                console.log('✅ Valid click target, opening file dialog');
                fileInput.click();
            } else {
                console.log('❌ Invalid click target:', e.target);
            }
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            console.log(`📁 File input changed for ${targetField}:`, e.target.files);
            console.log(`📁 Files count: ${e.target.files.length}`);
            if (e.target.files.length > 0) {
                console.log(`📁 Selected file:`, {
                    name: e.target.files[0].name,
                    size: e.target.files[0].size,
                    type: e.target.files[0].type
                });
            }
            handleFileSelect(e.target.files[0], zone, fileInfo, targetField);
        });

        // Drag and drop events
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
            console.log(`🔄 Dragover on ${targetField}`);
        });

        zone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            if (!zone.contains(e.relatedTarget)) {
                zone.classList.remove('dragover');
                console.log(`🔄 Dragleave on ${targetField}`);
            }
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            console.log(`📦 Drop event on ${targetField}`);
            
            const files = e.dataTransfer.files;
            console.log(`📦 Dropped files count: ${files.length}`);
            
            if (files.length > 0) {
                const file = files[0];
                console.log(`📦 Dropped file:`, {
                    name: file.name,
                    size: file.size,
                    type: file.type
                });
                
                if (validateCSVFile(file)) {
                    console.log('✅ File validation passed');
                    // Create a new FileList-like object
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    fileInput.files = dt.files;
                    console.log(`📦 File assigned to input, files count now: ${fileInput.files.length}`);
                    handleFileSelect(file, zone, fileInfo, targetField);
                } else {
                    console.log('❌ File validation failed');
                    showError('Please upload only CSV files.');
                }
            }
        });
    });

    function handleFileSelect(file, zone, fileInfo, fieldName) {
        console.log(`🔧 handleFileSelect called for ${fieldName}:`, file);
        
        if (file && validateCSVFile(file)) {
            console.log('✅ File is valid, processing...');
            const fileSize = formatFileSize(file.size);
            const lastModified = new Date(file.lastModified).toLocaleDateString();
            
            fileInfo.innerHTML = `
                <div class="file-details">
                    <div class="file-meta">
                        <div class="file-name">${file.name}</div>
                        <div class="file-stats">
                            ${fileSize} • Modified: ${lastModified}
                        </div>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <div class="status-success">
                            <i class="bi bi-check-circle"></i>
                            Ready to upload
                        </div>
                        <button type="button" class="remove-file" onclick="removeFile('${fieldName}')">
                            <i class="bi bi-x-circle"></i>
                        </button>
                    </div>
                </div>
            `;
            fileInfo.classList.add('show');
            console.log(`✅ File info updated and shown for ${fieldName}`);
            
            // Update zone appearance
            zone.style.borderColor = 'var(--active-color)';
            zone.style.backgroundColor = 'rgba(13, 110, 253, 0.05)';
            
            // Update zone content to show success
            zone.innerHTML = `
                <i class="bi bi-check-circle-fill upload-zone-icon" style="color: #198754;"></i>
                <div class="upload-zone-text" style="color: #198754;">File Selected: ${file.name}</div>
                <div class="upload-zone-subtext">Click to change file or drag a new one</div>
            `;
            
            console.log(`✅ Zone appearance updated for ${fieldName}`);
            
            // Log current state of file input
            const currentInput = document.getElementById(fieldName);
            console.log(`📊 Current input state for ${fieldName}:`, {
                files: currentInput.files,
                filesLength: currentInput.files.length,
                value: currentInput.value
            });
            
        } else if (file) {
            console.log('❌ File validation failed for:', file);
            showError('Please select a valid CSV file.');
            resetZone(zone, fieldName);
        } else {
            console.log('❌ No file provided to handleFileSelect');
        }
    }

    // Global function to remove files
    window.removeFile = function(fieldName) {
        console.log(`🗑️ Removing file for ${fieldName}`);
        const fileInput = document.getElementById(fieldName);
        const fileInfo = document.getElementById(fieldName + '_info');
        const zone = document.querySelector(`[data-target="${fieldName}"]`);
        
        console.log(`🗑️ Before removal - files count: ${fileInput.files.length}`);
        fileInput.value = '';
        console.log(`🗑️ After removal - files count: ${fileInput.files.length}, value: "${fileInput.value}"`);
        
        fileInfo.classList.remove('show');
        resetZone(zone, fieldName);
    };

    function resetZone(zone, fieldName) {
        console.log(`🔄 Resetting zone for ${fieldName}`);
        const fieldConfig = getFieldConfig(fieldName);
        zone.style.borderColor = '';
        zone.style.backgroundColor = '';
        zone.innerHTML = `
            <i class="bi bi-file-earmark-text upload-zone-icon"></i>
            <div class="upload-zone-text">${fieldConfig.text}</div>
            <div class="upload-zone-subtext">${fieldConfig.subtext}</div>
        `;
        console.log(`✅ Zone reset complete for ${fieldName}`);
    }

    function getFieldConfig(fieldName) {
        const configs = {
            'availability_file': {
                text: 'Drop availability.csv here or click to browse',
                subtext: 'Expected format: availability_id, coach_id, day, period, available, restriction_reason'
            },
            'branch_config_file': {
                text: 'Drop branch_config.csv here or click to browse',
                subtext: 'Expected format: branch, max_classes_per_slot'
            },
            'coaches_file': {
                text: 'Drop coaches.csv here or click to browse',
                subtext: 'Expected format: coach_id, coach_name, residential_area, assigned_branch, position, status, etc.'
            },
            'enrollment_file': {
                text: 'Drop enrollment.csv here or click to browse',
                subtext: 'Expected format: Branch, Level Category Base, Count'
            },
            'popular_timeslots_file': {
                text: 'Drop popular_timeslots.csv here or click to browse',
                subtext: 'Expected format: time_slot, day, level'
            }
        };
        return configs[fieldName] || { text: 'Drop file here', subtext: 'CSV files only' };
    }

    // Form submission with enhanced progress and detailed logging
    uploadForm.addEventListener('submit', function(e) {
        console.log('🚀 Form submission started');
        
        const formData = new FormData(uploadForm);
        let hasFiles = false;
        let fileCount = 0;
        const fileDetails = {};

        console.log('📋 Analyzing form data...');

        // Log all form entries
        for (let [key, value] of formData.entries()) {
            console.log(`📋 FormData entry: ${key} =`, value);
            
            if (value instanceof File) {
                console.log(`📁 File details for ${key}:`, {
                    name: value.name,
                    size: value.size,
                    type: value.type,
                    lastModified: value.lastModified
                });
                
                if (value.size > 0) {
                    hasFiles = true;
                    fileCount++;
                    fileDetails[key] = {
                        name: value.name,
                        size: value.size,
                        type: value.type
                    };
                } else {
                    console.log(`⚠️ File ${key} has 0 size`);
                }
            }
        }

        // Additional check - inspect file inputs directly
        console.log('🔍 Direct file input inspection:');
        const fileInputs = ['availability_file', 'branch_config_file', 'coaches_file', 'enrollment_file', 'popular_timeslots_file'];
        
        fileInputs.forEach(inputId => {
            const input = document.getElementById(inputId);
            if (input) {
                console.log(`🔍 Input ${inputId}:`, {
                    files: input.files,
                    filesLength: input.files.length,
                    value: input.value,
                    hasFiles: input.files.length > 0
                });
                
                if (input.files.length > 0) {
                    Array.from(input.files).forEach((file, index) => {
                        console.log(`🔍 File ${index} in ${inputId}:`, {
                            name: file.name,
                            size: file.size,
                            type: file.type
                        });
                        
                        if (file.size > 0) {
                            hasFiles = true;
                            fileCount++;
                        }
                    });
                }
            } else {
                console.error(`❌ Input element not found: ${inputId}`);
            }
        });

        console.log(`📊 Final file analysis:`, {
            hasFiles,
            fileCount,
            fileDetails
        });

        if (!hasFiles) {
            console.log('❌ No valid files found, preventing form submission');
            e.preventDefault();
            showError('Please select at least one file to upload.');
            return;
        }

        console.log(`✅ Found ${fileCount} valid file(s), proceeding with submission`);

        // Show progress
        progressContainer.classList.add('show');
        progressBar.style.width = '0%';

        // Disable submit button
        const submitBtn = uploadForm.querySelector('.btn-upload');
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            Processing ${fileCount} file${fileCount > 1 ? 's' : ''}...
        `;

        console.log('🔄 Progress bar shown, submit button disabled');

        // Simulate realistic progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 10 + 5;
            if (progress > 85) {
                progress = 85;
                clearInterval(progressInterval);
            }
            progressBar.style.width = progress + '%';
        }, 300);

        // Complete progress after a delay
        setTimeout(() => {
            progressBar.style.width = '100%';
            console.log('✅ Progress bar completed');
        }, 1500);
    });

    // File validation with logging
    function validateCSVFile(file) {
        console.log('🔍 Validating file:', file);
        if (!file) {
            console.log('❌ No file provided for validation');
            return false;
        }
        
        const validTypes = ['text/csv', 'application/vnd.ms-excel', 'text/plain'];
        const validExtensions = ['.csv'];
        
        const hasValidType = validTypes.includes(file.type);
        const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
        
        console.log('🔍 Validation results:', {
            fileName: file.name,
            fileType: file.type,
            hasValidType,
            hasValidExtension,
            isValid: hasValidType || hasValidExtension
        });
        
        return hasValidType || hasValidExtension;
    }

    // Sample data copy functionality
    const csvSamples = document.querySelectorAll('.csv-sample');
    csvSamples.forEach((sample, index) => {
        console.log(`📋 CSV sample ${index + 1} found`);
        sample.addEventListener('click', () => {
            console.log(`📋 CSV sample ${index + 1} clicked`);
            const text = sample.textContent.replace(/Sample Format.*?:/s, '').trim();
            navigator.clipboard.writeText(text).then(() => {
                console.log('✅ Text copied to clipboard');
                // Show visual feedback
                const originalBg = sample.style.backgroundColor;
                const originalBorder = sample.style.borderColor;
                sample.style.backgroundColor = 'rgba(13, 110, 253, 0.2)';
                sample.style.borderColor = 'var(--active-color)';
                
                // Show tooltip
                showTooltip(sample, 'Copied to clipboard!');
                
                setTimeout(() => {
                    sample.style.backgroundColor = originalBg;
                    sample.style.borderColor = originalBorder;
                }, 1000);
            }).catch((err) => {
                console.error('❌ Failed to copy to clipboard:', err);
                showError('Failed to copy to clipboard');
            });
        });
    });

    // Utility functions
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function showError(message) {
        console.log('🚨 Showing error:', message);
        // Create temporary alert
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            <i class="bi bi-exclamation-circle me-2"></i>${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    function showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'position-absolute bg-dark text-white px-2 py-1 rounded';
        tooltip.style.cssText = 'top: -35px; left: 50%; transform: translateX(-50%); font-size: 0.8rem; z-index: 1000;';
        tooltip.textContent = text;
        
        element.style.position = 'relative';
        element.appendChild(tooltip);
        
        setTimeout(() => {
            tooltip.remove();
        }, 2000);
    }

    console.log('✅ Data upload JavaScript initialization complete');
});