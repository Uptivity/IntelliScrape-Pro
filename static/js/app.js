// IntelliScrape Pro Frontend JavaScript

const API_URL = 'http://127.0.0.1:5000';

// Modern Notification System
function showNotification(title, message, type = 'info', duration = 5000) {
    // Remove any existing notifications
    const existing = document.querySelector('.notification-overlay');
    if (existing) {
        existing.remove();
    }

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'notification-overlay';

    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification-modern ${type}`;

    // SVG icons for professional look
    const icons = {
        success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <path d="M20 6L9 17l-5-5"/>
                  </svg>`,
        error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 18L18 6M6 6l12 12"/>
                </svg>`,
        warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 9v4m0 4h.01M5.07 19a9 9 0 119.86 0H5.07z"/>
                  </svg>`,
        info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                 <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
               </svg>`
    };

    notification.innerHTML = `
        <div class="notification-glass">
            <div class="notification-icon-modern">${icons[type] || icons.info}</div>
            <div class="notification-content-modern">
                <div class="notification-title-modern">${title}</div>
                <div class="notification-message-modern">${message}</div>
            </div>
            <button class="notification-close-modern" onclick="closeNotification()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    `;

    overlay.appendChild(notification);
    document.body.appendChild(overlay);

    // Trigger animation
    setTimeout(() => {
        overlay.classList.add('show');
    }, 10);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            closeNotification();
        }, duration);
    }

    return notification;
}

function closeNotification() {
    const overlay = document.querySelector('.notification-overlay');
    if (overlay) {
        overlay.classList.remove('show');
        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}

// Quick notification helpers
function showSuccess(message, title = 'Success') {
    return showNotification(title, message, 'success');
}

function showError(message, title = 'Error') {
    return showNotification(title, message, 'error');
}

function showWarning(message, title = 'Warning') {
    return showNotification(title, message, 'warning');
}

function showInfo(message, title = 'Info') {
    return showNotification(title, message, 'info');
}

// Modern Confirmation Dialog
function showConfirmation(title, message, onConfirm, onCancel) {
    // Remove any existing dialogs
    const existing = document.querySelector('.dialog-overlay');
    if (existing) {
        existing.remove();
    }

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'dialog-overlay';

    // Create dialog
    const dialog = document.createElement('div');
    dialog.className = 'dialog-modern';

    dialog.innerHTML = `
        <div class="dialog-glass">
            <div class="dialog-header">
                <h3 class="dialog-title">${title}</h3>
            </div>
            <div class="dialog-body">
                <p class="dialog-message">${message}</p>
            </div>
            <div class="dialog-actions">
                <button class="dialog-btn cancel" onclick="closeDialog(false)">Cancel</button>
                <button class="dialog-btn confirm" onclick="closeDialog(true)">Confirm</button>
            </div>
        </div>
    `;

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    // Store callbacks
    window.dialogCallbacks = { onConfirm, onCancel };

    // Trigger animation
    setTimeout(() => {
        overlay.classList.add('show');
    }, 10);
}

function closeDialog(confirmed) {
    const overlay = document.querySelector('.dialog-overlay');
    if (overlay) {
        overlay.classList.remove('show');

        // Execute callback
        if (window.dialogCallbacks) {
            if (confirmed && window.dialogCallbacks.onConfirm) {
                window.dialogCallbacks.onConfirm();
            } else if (!confirmed && window.dialogCallbacks.onCancel) {
                window.dialogCallbacks.onCancel();
            }
            delete window.dialogCallbacks;
        }

        setTimeout(() => {
            overlay.remove();
        }, 300);
    }
}

// Field Validation Helper
function validateFields(fields) {
    let isValid = true;
    let emptyFields = [];

    fields.forEach(field => {
        const element = document.getElementById(field.id);
        if (element) {
            const value = element.value.trim();
            if (!value && field.required) {
                isValid = false;
                emptyFields.push(field.name);
                element.classList.add('field-error');
            } else {
                element.classList.remove('field-error');
            }
        }
    });

    if (!isValid) {
        showWarning(
            `Please fill in the following required fields: ${emptyFields.join(', ')}`,
            'Required Fields Missing'
        );
    }

    return isValid;
}

// Simple API validation for basic checks
async function checkApiStatus() {
    try {
        const response = await fetch(`${API_URL}/api/status`);
        const data = await response.json();
        return { success: response.ok && data.status === 'online' };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Clear validation status when user starts typing
function clearValidationStatus(type) {
    const validationId = type === 'firecrawl' ? 'firecrawlValidation' : 'groqValidation';
    const validation = document.getElementById(validationId);
    if (validation) {
        validation.style.display = 'none';
    }
}

// Validate Groq API before allowing AI descriptions toggle
async function validateGroqBeforeToggle(event) {
    const checkbox = event.target;
    const groqKeyInput = document.getElementById('groqKey');
    const groqKeyRequired = document.getElementById('groqKeyRequired');

    // If trying to ENABLE (checkbox will be checked after click)
    if (checkbox.checked && (!groqKeyInput.value.trim())) {
        event.preventDefault();
        checkbox.checked = false;

        // Show error message
        if (groqKeyRequired) {
            groqKeyRequired.style.display = 'block';
        }

        // Shake the card
        const card = document.getElementById('aiDescriptionCard');
        if (card) {
            card.classList.add('invalid-shake');
            setTimeout(() => card.classList.remove('invalid-shake'), 500);
        }

        showError('Groq API key is required for AI descriptions. Please add it in Settings.', 'API Key Required');

        // Open settings modal
        toggleSettings();

        // Focus on Groq key input
        setTimeout(() => {
            groqKeyInput.focus();
            groqKeyInput.classList.add('invalid-shake');
            setTimeout(() => groqKeyInput.classList.remove('invalid-shake'), 500);
        }, 300);

        return false;
    } else if (checkbox.checked && groqKeyInput.value.trim()) {
        // If trying to enable with a key, validate it first
        const isValid = await validateApiKey('groq');
        if (!isValid) {
            event.preventDefault();
            checkbox.checked = false;

            if (groqKeyRequired) {
                groqKeyRequired.style.display = 'block';
            }

            showError('Please enter a valid Groq API key in Settings', 'Invalid API Key');
            toggleSettings();

            return false;
        } else {
            // Hide error message if valid
            if (groqKeyRequired) {
                groqKeyRequired.style.display = 'none';
            }
            showSuccess('AI-powered descriptions enabled', 'Feature Enabled');
        }
    } else if (!checkbox.checked) {
        // If trying to DISABLE, always allow it
        if (groqKeyRequired) {
            groqKeyRequired.style.display = 'none';
        }
        showInfo('AI-powered descriptions disabled', 'Feature Disabled');
    }

    return true;
}

// API Key Validation
async function validateApiKey(type) {
    const inputId = type === 'firecrawl' ? 'apiKey' : 'groqKey';
    const validationId = type === 'firecrawl' ? 'firecrawlValidation' : 'groqValidation';

    const input = document.getElementById(inputId);
    const validation = document.getElementById(validationId);

    if (!input.value.trim()) {
        validation.style.display = 'none';
        return false;
    }

    // Update main API status to show validation in progress
    const apiStatusEl = document.getElementById('apiStatus');
    const originalStatus = apiStatusEl.textContent;
    const originalClass = apiStatusEl.className;

    apiStatusEl.textContent = `Validating ${type === 'firecrawl' ? 'Firecrawl' : 'Groq'}...`;
    apiStatusEl.className = 'status-warning';

    // Show validation UI
    validation.style.display = 'flex';
    const icon = validation.querySelector('.api-status-icon');
    const text = validation.querySelector('.api-status-text');

    icon.className = 'api-status-icon checking';
    icon.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4m0 12v4m4.22-13.22l2.83-2.83M6.95 17.05l-2.83 2.83m0-14.14l2.83 2.83m11.1 11.1l2.83-2.83"/></svg>';
    text.className = 'api-status-text checking';
    text.textContent = 'Validating API key...';

    try {
        // Real API validation
        const response = await fetch(`${API_URL}/api/validate-key`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: type,
                key: input.value
            })
        });

        const result = await response.json();

        if (result.valid) {
            icon.className = 'api-status-icon valid';
            icon.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>';
            text.className = 'api-status-text valid';
            text.textContent = result.message || 'Valid API key';
            input.classList.remove('invalid-shake');

            // Save to localStorage for verification modal
            localStorage.setItem(`${type}_api_key`, input.value);
            showSuccess(`${type === 'firecrawl' ? 'Firecrawl' : 'Groq'} API key validated successfully`, 'API Key Valid');

            // Update system status after successful validation
            setTimeout(checkSystemStatus, 500);
            return true;
        } else {
            icon.className = 'api-status-icon invalid';
            icon.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18L18 6M6 6l12 12"/></svg>';
            text.className = 'api-status-text invalid';
            text.textContent = result.message || 'Invalid API key';

            // Add shake animation
            input.classList.add('invalid-shake');
            setTimeout(() => input.classList.remove('invalid-shake'), 500);

            showError(`${type === 'firecrawl' ? 'Firecrawl' : 'Groq'} API key validation failed`, 'Invalid API Key');

            // Update system status after failed validation
            setTimeout(checkSystemStatus, 500);
            return false;
        }
    } catch (error) {
        icon.className = 'api-status-icon invalid';
        icon.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18L18 6M6 6l12 12"/></svg>';
        text.className = 'api-status-text invalid';
        text.textContent = 'Validation failed';

        // Add shake animation
        input.classList.add('invalid-shake');
        setTimeout(() => input.classList.remove('invalid-shake'), 500);

        showError('Unable to validate API key. Please check your connection.', 'Validation Error');

        // Update system status after error
        setTimeout(checkSystemStatus, 500);
        return false;
    }
}

// Store scraped products globally for editing
let currentProducts = [];

// Session management
let currentSession = {
    id: generateSessionId(),
    products: [],
    status: 'active',
    createdAt: new Date().toISOString()
};

let completedSessions = JSON.parse(localStorage.getItem('completedSessions') || '[]');

// Check system status on load
window.onload = function() {
    checkSystemStatus();
    loadConfig();
    loadSettings();
    loadMarketplaceSelection();  // Add this line
    updateDashboard();
    initSmartFeatures();
};

async function checkSystemStatus() {
    let firecrawlStatus = false;
    let groqStatus = false;
    let systemOnline = false;

    try {
        // First check if the backend server is running
        const response = await fetch(`${API_URL}/api/status`);
        const data = await response.json();
        systemOnline = response.ok;

        // Update modules status
        document.getElementById('modulesStatus').textContent = data.modules_loaded ? 'Loaded' : 'Not Loaded';
        document.getElementById('modulesStatus').className = data.modules_loaded ? 'status-online' : 'status-offline';
    } catch (error) {
        document.getElementById('modulesStatus').textContent = 'Unknown';
        document.getElementById('apiStatus').textContent = 'Server Offline';
        document.getElementById('apiStatus').className = 'status-offline';
        return;
    }

    // Check Firecrawl API if key exists
    const firecrawlKey = document.getElementById('apiKey')?.value?.trim();
    if (firecrawlKey && systemOnline) {
        try {
            const firecrawlResponse = await fetch(`${API_URL}/api/validate-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: 'firecrawl', key: firecrawlKey })
            });
            const firecrawlResult = await firecrawlResponse.json();
            firecrawlStatus = firecrawlResult.valid === true;
        } catch {
            firecrawlStatus = false;
        }
    }

    // Check Groq API if auto-generate description is enabled and key exists
    const autoGenerateDesc = document.getElementById('autoGenerateDescription')?.checked;
    const groqKey = document.getElementById('groqKey')?.value?.trim();

    if (autoGenerateDesc && groqKey && systemOnline) {
        try {
            const groqResponse = await fetch(`${API_URL}/api/validate-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: 'groq', key: groqKey })
            });
            const groqResult = await groqResponse.json();
            groqStatus = groqResult.valid === true;
        } catch {
            groqStatus = false;
        }
    }

    // Update API status based on what's needed
    const apiStatusEl = document.getElementById('apiStatus');
    if (!systemOnline) {
        apiStatusEl.textContent = 'Server Offline';
        apiStatusEl.className = 'status-offline';
    } else if (!firecrawlKey) {
        apiStatusEl.textContent = 'No API Key';
        apiStatusEl.className = 'status-warning';
    } else if (autoGenerateDesc && groqKey) {
        // Both APIs are needed
        if (firecrawlStatus && groqStatus) {
            apiStatusEl.textContent = 'All APIs Online';
            apiStatusEl.className = 'status-online';
        } else if (!firecrawlStatus && !groqStatus) {
            apiStatusEl.textContent = 'APIs Offline';
            apiStatusEl.className = 'status-offline';
        } else if (!firecrawlStatus) {
            apiStatusEl.textContent = 'Firecrawl Offline';
            apiStatusEl.className = 'status-offline';
        } else {
            apiStatusEl.textContent = 'Groq Offline';
            apiStatusEl.className = 'status-offline';
        }
    } else {
        // Only Firecrawl is needed
        if (firecrawlStatus) {
            apiStatusEl.textContent = 'Online';
            apiStatusEl.className = 'status-online';
        } else {
            apiStatusEl.textContent = 'Firecrawl Offline';
            apiStatusEl.className = 'status-offline';
        }
    }
}

// Extract URLs
async function extractUrls() {
    // First, check if user has selected a marketplace
    const selectedMode = document.querySelector('.intelligence-card.selected');
    if (!selectedMode) {
        showError('Please select a marketplace format (WSMarketplace or JustSell) before extracting URLs', 'Marketplace Selection Required');
        // Scroll to intelligence engine section
        document.querySelector('.intelligence-selector').scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        return;
    }

    const textarea = document.getElementById('homepageUrls');
    const urls = textarea.value.split('\n').filter(url => url.trim());

    if (urls.length === 0) {
        showWarning('Please enter at least one homepage URL', 'Missing URLs');
        return;
    }

    // Validate Firecrawl API key first
    const apiKeyInput = document.getElementById('apiKey');
    if (!apiKeyInput.value.trim()) {
        showError('Firecrawl API key is required for URL extraction', 'Missing API Key');
        apiKeyInput.classList.add('invalid-shake');
        apiKeyInput.focus();

        // Open settings modal to show API key field
        toggleSettings();

        setTimeout(() => apiKeyInput.classList.remove('invalid-shake'), 500);
        return;
    }

    // Validate the API key
    const isValidKey = await validateApiKey('firecrawl');
    if (!isValidKey) {
        showError('Please enter a valid Firecrawl API key in Settings', 'Invalid API Key');
        toggleSettings(); // Open settings modal
        return;
    }

    // Show loading state
    const extractBtn = document.getElementById('extractBtn');
    const btnText = extractBtn.querySelector('.btn-text');
    const btnSpinner = extractBtn.querySelector('.btn-spinner');

    extractBtn.disabled = true;
    extractBtn.classList.add('loading');
    btnText.textContent = 'Initializing...';
    btnSpinner.style.display = 'block';

    // Start extraction
    performExtraction(urls);
}

async function performExtraction(urls) {
    // Reset progress tracking for extraction
    progressStartTime = null;
    lastProgressUpdate = null;

    // Show progress section and stop button
    document.getElementById('extractProgress').style.display = 'block';
    document.getElementById('extractResults').style.display = 'none';
    const stopBtn = document.getElementById('stopExtractBtn');
    if (stopBtn) {
        stopBtn.style.display = 'inline-flex';
    }

    try {
        const settings = getSettings(); // Get API key from settings
        const response = await fetch(`${API_URL}/api/extract-urls`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                urls: urls,
                settings: settings
            })
        });

        const data = await response.json();

        if (data.job_id) {
            // Store job ID for stop functionality
            currentExtractJobId = data.job_id;

            // Update button text to "Extracting"
            const extractBtn = document.getElementById('extractBtn');
            const btnText = extractBtn.querySelector('.btn-text');
            btnText.textContent = 'Extracting...';

            showInfo(`Starting URL extraction from ${urls.length} homepage(s)`, 'Extraction Started');
            // Poll for job status
            pollJobStatus(data.job_id, 'extract');
        }
    } catch (error) {
        // Reset button state on error
        const extractBtn = document.getElementById('extractBtn');
        const btnText = extractBtn.querySelector('.btn-text');
        const btnSpinner = extractBtn.querySelector('.btn-spinner');

        extractBtn.disabled = false;
        extractBtn.classList.remove('loading');
        btnText.textContent = 'Initialize Extraction';
        btnSpinner.style.display = 'none';

        showError('Failed to start URL extraction: ' + error.message);
        document.getElementById('extractProgress').style.display = 'none';
    }
}

// Scrape Products
async function scrapeProducts() {
    // First, check if user has selected a marketplace
    const selectedMode = document.querySelector('.intelligence-card.selected');
    if (!selectedMode) {
        showError('Please select a marketplace format (WSMarketplace or JustSell) before scraping products', 'Marketplace Selection Required');
        // Scroll to intelligence engine section
        document.querySelector('.intelligence-selector').scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        return;
    }

    const textarea = document.getElementById('scrapeUrls');
    const urls = textarea.value.split('\n').filter(url => url.trim());

    if (urls.length === 0) {
        showWarning('Please enter product URLs or extract them first', 'No URLs Provided');
        return;
    }

    // Validate Firecrawl API key first
    const apiKeyInput = document.getElementById('apiKey');
    if (!apiKeyInput.value.trim()) {
        showError('Firecrawl API key is required for scraping', 'Missing API Key');
        apiKeyInput.classList.add('invalid-shake');
        apiKeyInput.focus();
        setTimeout(() => apiKeyInput.classList.remove('invalid-shake'), 500);
        return;
    }

    // Validate API key
    const isValidKey = await validateApiKey('firecrawl');
    if (!isValidKey) {
        return;
    }

    // Check if auto-generate description is enabled and validate Groq key
    const autoGenerateDesc = document.getElementById('autoGenerateDescription');
    if (autoGenerateDesc && autoGenerateDesc.checked) {
        const groqKeyInput = document.getElementById('groqKey');
        if (!groqKeyInput.value.trim()) {
            showError('Groq AI API key is required for auto-generating descriptions', 'Missing Groq API Key');
            groqKeyInput.classList.add('invalid-shake');
            groqKeyInput.focus();
            setTimeout(() => groqKeyInput.classList.remove('invalid-shake'), 500);
            return;
        }

        const isValidGroqKey = await validateApiKey('groq');
        if (!isValidGroqKey) {
            return;
        }
    }

    // Show loading state
    const scrapeBtn = document.getElementById('scrapeBtn');
    const btnText = scrapeBtn.querySelector('.btn-text');
    const btnSpinner = scrapeBtn.querySelector('.btn-spinner');

    scrapeBtn.disabled = true;
    scrapeBtn.classList.add('loading');
    btnText.textContent = 'Initializing...';
    btnSpinner.style.display = 'block';

    // Start scraping
    performScraping(urls);
}

async function performScraping(urls) {
    // Reset progress tracking
    progressStartTime = null;
    lastProgressUpdate = null;

    // Show progress section and stop button
    document.getElementById('scrapeProgress').style.display = 'block';
    document.getElementById('scrapeResults').style.display = 'none';
    const stopBtn = document.getElementById('stopScrapeBtn');
    if (stopBtn) {
        stopBtn.style.display = 'inline-flex';
    }

    try {
        const settings = getSettings(); // Get current settings
        // Note: selectedFields ready for future backend integration
        // const selectedFields = getSelectedFields();

        const response = await fetch(`${API_URL}/api/scrape-products`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                urls: urls,
                settings: settings
            })
        });

        const data = await response.json();

        if (data.job_id) {
            // Store job ID for stop functionality
            currentScrapeJobId = data.job_id;

            // Update button text to "Scraping"
            const scrapeBtn = document.getElementById('scrapeBtn');
            const btnText = scrapeBtn.querySelector('.btn-text');
            btnText.textContent = 'Scraping...';

            showInfo(`Starting product scraping for ${urls.length} URL(s)`, 'Scraping Started');
            // Poll for job status
            pollJobStatus(data.job_id, 'scrape');
        }
    } catch (error) {
        // Reset button state on error
        const scrapeBtn = document.getElementById('scrapeBtn');
        const btnText = scrapeBtn.querySelector('.btn-text');
        const btnSpinner = scrapeBtn.querySelector('.btn-spinner');

        scrapeBtn.disabled = false;
        scrapeBtn.classList.remove('loading');
        btnText.textContent = 'Execute Scraping';
        btnSpinner.style.display = 'none';

        showError('Failed to start product scraping: ' + error.message);
        document.getElementById('scrapeProgress').style.display = 'none';
    }
}

// Poll job status
async function pollJobStatus(jobId, jobType) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/api/job/${jobId}`);
            const job = await response.json();

            // Update progress
            if (jobType === 'extract') {
                updateExtractProgress(job);
            } else if (jobType === 'scrape') {
                updateScrapeProgress(job);
            }

            // Auto-save progress incrementally if enabled
            if (document.getElementById('autoSave').checked) {
                saveProgressIncremental(job, jobType);
            }

            // Check if complete
            if (job.status === 'completed' || job.status === 'failed') {
                clearInterval(interval);

                if (jobType === 'extract') {
                    handleExtractComplete(job);
                } else if (jobType === 'scrape') {
                    handleScrapeComplete(job);
                }
            }
        } catch (error) {
            console.error('Error polling job:', error);
        }
    }, 1000); // Poll every second
}

// Update extraction progress
function updateExtractProgress(job) {
    const progressBar = document.getElementById('extractProgressBar');
    const progressPercentage = document.getElementById('extractProgressPercentage');
    const status = document.getElementById('extractStatus');

    if (job.total > 0) {
        const percent = (job.progress / job.total) * 100;
        progressBar.style.width = percent + '%';
        progressPercentage.textContent = Math.round(percent) + '%';
    } else {
        progressPercentage.textContent = '0%';
    }

    status.textContent = job.message;
}

// Handle extraction complete
function handleExtractComplete(job) {
    const extractBtn = document.getElementById('extractBtn');
    const btnText = extractBtn.querySelector('.btn-text');
    const btnSpinner = extractBtn.querySelector('.btn-spinner');

    // Hide stop button
    const stopBtn = document.getElementById('stopExtractBtn');
    if (stopBtn) {
        stopBtn.style.display = 'none';
    }

    // Hide spinner
    btnSpinner.style.display = 'none';

    if (job.status === 'completed' && job.result) {
        // Show success state
        btnText.textContent = '✓ Completed';
        extractBtn.style.background = '#10b981';

        // Show results
        document.getElementById('extractResults').style.display = 'block';
        const urls = job.result.urls_found || [];
        document.getElementById('productUrls').value = urls.join('\n');
        document.getElementById('urlCount').textContent = `${urls.length} URLs found`;
        document.getElementById('extractStatus').textContent = `Extraction complete! Found ${urls.length} product URLs`;
        showSuccess(`Discovered ${urls.length} product URLs from provided homepages`, 'URL Extraction Complete');

        // Reset job ID when extraction completes
        currentExtractJobId = null;

        // Reset button after 3 seconds
        setTimeout(() => {
            extractBtn.disabled = false;
            extractBtn.classList.remove('loading');
            btnText.textContent = 'Initialize Extraction';
            extractBtn.style.background = '';
        }, 3000);
    } else {
        // Show error state
        btnText.textContent = '✕ Failed';
        extractBtn.style.background = '#ef4444';
        document.getElementById('extractStatus').textContent = 'Extraction failed: ' + (job.error || 'Unknown error');
        showError('URL extraction failed: ' + (job.error || 'Unknown error'), 'Extraction Failed');

        // Reset job ID when extraction fails
        currentExtractJobId = null;

        // Reset button after 3 seconds
        setTimeout(() => {
            extractBtn.disabled = false;
            extractBtn.classList.remove('loading');
            btnText.textContent = 'Initialize Extraction';
            extractBtn.style.background = '';
        }, 3000);
    }
}

// Progress tracking variables
let progressStartTime = null;
let lastProgressUpdate = null;

// Update scraping progress
function updateScrapeProgress(job) {
    // Initialize start time on first progress update
    if (!progressStartTime && job.progress > 0) {
        progressStartTime = Date.now();
    }

    const progressBar = document.getElementById('scrapeProgressBar');
    const status = document.getElementById('scrapeStatus');
    const progressStats = document.getElementById('progressStats');
    const progressPercentage = document.getElementById('progressPercentage');
    const estimatedTime = document.getElementById('estimatedTime');
    const elapsedTime = document.getElementById('elapsedTime');
    const processingSpeed = document.getElementById('processingSpeed');

    // Update basic progress
    if (job.total > 0) {
        const percent = (job.progress / job.total) * 100;
        progressBar.style.width = percent + '%';
        progressPercentage.textContent = Math.round(percent) + '%';

        // Update progress stats
        progressStats.textContent = `${job.progress}/${job.total} completed`;

        // Calculate timing metrics
        if (progressStartTime && job.progress > 0) {
            const now = Date.now();
            const elapsedMs = now - progressStartTime;
            const elapsedSeconds = Math.floor(elapsedMs / 1000);

            // Format elapsed time
            const hours = Math.floor(elapsedSeconds / 3600);
            const minutes = Math.floor((elapsedSeconds % 3600) / 60);
            const seconds = elapsedSeconds % 60;

            let elapsedStr = '';
            if (hours > 0) elapsedStr += `${hours}h `;
            if (minutes > 0) elapsedStr += `${minutes}m `;
            elapsedStr += `${seconds}s`;

            elapsedTime.textContent = `Elapsed: ${elapsedStr}`;

            // Calculate speed (items per minute)
            const itemsPerSecond = job.progress / (elapsedMs / 1000);
            const itemsPerMinute = Math.round(itemsPerSecond * 60);
            processingSpeed.textContent = `Speed: ${itemsPerMinute} items/min`;

            // Calculate ETA
            if (job.progress < job.total && itemsPerSecond > 0) {
                const remainingItems = job.total - job.progress;
                const remainingSeconds = Math.ceil(remainingItems / itemsPerSecond);

                const etaHours = Math.floor(remainingSeconds / 3600);
                const etaMinutes = Math.floor((remainingSeconds % 3600) / 60);
                const etaSecs = remainingSeconds % 60;

                let etaStr = '';
                if (etaHours > 0) etaStr += `${etaHours}h `;
                if (etaMinutes > 0) etaStr += `${etaMinutes}m `;
                etaStr += `${etaSecs}s`;

                estimatedTime.textContent = `Est: ${etaStr}`;
            } else if (job.progress >= job.total) {
                estimatedTime.textContent = 'Est: Complete';
            }
        } else {
            elapsedTime.textContent = 'Elapsed: 0s';
            processingSpeed.textContent = 'Speed: -- items/min';
            estimatedTime.textContent = 'Est: --';
        }
    } else {
        progressStats.textContent = '0/0 completed';
        progressPercentage.textContent = '0%';
        elapsedTime.textContent = 'Elapsed: 0s';
        processingSpeed.textContent = 'Speed: -- items/min';
        estimatedTime.textContent = 'Est: --';
    }

    status.textContent = job.message;
}

// Handle scraping complete
function handleScrapeComplete(job) {
    handleScrapeCompleteWithSession(job);
}

// Display products in table
function displayProducts(products) {
    const container = document.getElementById('productTable');

    if (!container) {
        console.error('Product table container not found!');
        return;
    }

    console.log('Displaying products:', products.length);

    if (!products || products.length === 0) {
        container.innerHTML = '<p>No products found</p>';
        return;
    }

    // Create summary section
    let html = '<div class="summary">';
    html += `<h4>Extraction Summary</h4>`;
    html += `<p><strong>Total Products:</strong> ${products.length}</p>`;

    // Count brands
    const brands = [...new Set(products.map(p => p.Brand).filter(b => b))];
    if (brands.length > 0) {
        html += `<p><strong>Brands Identified:</strong> ${brands.join(', ')}</p>`;
    }

    // Count categories
    const categories = [...new Set(products.map(p => p.Category).filter(c => c))];
    if (categories.length > 0) {
        html += `<p><strong>Categories:</strong> ${categories.length} unique</p>`;
    }

    html += '</div>';

    // Create editable table
    html += '<div class="product-table"><table class="editable-table">';
    html += '<thead><tr><th>SKU</th><th>Name</th><th>Brand</th><th>Category</th><th>Price</th><th>Stock</th><th>Status</th></tr></thead>';
    html += '<tbody>';

    products.forEach((product, index) => {
        html += '<tr>';
        html += `<td onclick="editCell(this, ${index}, 'SKU')">${product.SKU || '-'}</td>`;
        html += `<td onclick="editCell(this, ${index}, 'Name')">${product.Name || '-'}</td>`;
        html += `<td onclick="editCell(this, ${index}, 'Brand')">${product.Brand || '-'}</td>`;
        html += `<td onclick="editCell(this, ${index}, 'Category')">${product.Category || '-'}</td>`;
        html += `<td onclick="editCell(this, ${index}, 'Wholesale_Price')">${product.Wholesale_Price ? '$' + product.Wholesale_Price : '-'}</td>`;
        html += `<td onclick="editCell(this, ${index}, 'Stock_Count')">${product.Stock_Count || '100'}</td>`;
        html += `<td onclick="editCell(this, ${index}, 'Status')">${product.Status == '1' ? 'Active' : 'Inactive'}</td>`;
        html += '</tr>';
    });

    html += '</tbody></table></div>';
    html += '<p style="color: var(--text-secondary); margin-top: 10px; font-size: 13px;">Click any cell to edit values</p>';
    container.innerHTML = html;
}

// Copy extracted URLs to scraper
function copyToScraper() {
    const extractedUrls = document.getElementById('productUrls').value;
    document.getElementById('scrapeUrls').value = extractedUrls;
    showSuccess('URLs transferred to scraping queue', 'Transfer Complete');
}

// Configuration Functions
function saveConfig() {
    const config = {
        stock: document.getElementById('defaultStockMain').value,
        markup: document.getElementById('defaultMarkup').value,
        supplier: document.getElementById('supplierName').value,
        status: document.getElementById('defaultStatusMain').value
    };
    localStorage.setItem('scraperConfig', JSON.stringify(config));
    showSuccess('Your configuration has been applied successfully', 'Settings Saved');
}

function loadConfig() {
    const saved = localStorage.getItem('scraperConfig');
    if (saved) {
        const config = JSON.parse(saved);

        const defaultStock = document.getElementById('defaultStockMain');
        if (defaultStock) defaultStock.value = config.stock || 100;

        const defaultMarkup = document.getElementById('defaultMarkup');
        if (defaultMarkup) defaultMarkup.value = config.markup || 30;

        const supplierName = document.getElementById('supplierName');
        if (supplierName) supplierName.value = config.supplier || '';

        const defaultStatus = document.getElementById('defaultStatusMain');
        if (defaultStatus) defaultStatus.value = config.status || '1';
    }
}

function applyConfigToProducts() {
    const config = {
        stock: document.getElementById('defaultStockMain')?.value || '10',
        status: document.getElementById('defaultStatusMain')?.value || 'Active'
    };

    // Check if auto-generate SKU is enabled
    const autoGenerateSKU = document.getElementById('autoGenerateSKU')?.checked;

    currentProducts.forEach((product, index) => {
        // Apply stock and status
        product.Stock_Count = config.stock;
        product.Status = config.status;

        // Generate SKU if enabled and product doesn't have one
        if (autoGenerateSKU && (!product.SKU || product.SKU.trim() === '')) {
            product.SKU = generateSKUFromName(product.Name || product.name || `Product`, index + 1);
            console.log(`Generated SKU for product ${index + 1}: ${product.SKU}`);
        }
    });
}

// Edit Cell Function
function editCell(cell, productIndex, field) {
    const currentValue = currentProducts[productIndex][field] || '';
    const input = document.createElement('input');
    input.type = 'text';
    input.value = field === 'Wholesale_Price' ? currentValue.replace('$', '') : currentValue;

    input.onblur = function() {
        let newValue = input.value;
        if (field === 'Wholesale_Price' && newValue && !newValue.startsWith('$')) {
            newValue = parseFloat(newValue) || 0;
        }
        currentProducts[productIndex][field] = newValue;
        displayProducts(currentProducts);
    };

    input.onkeypress = function(e) {
        if (e.key === 'Enter') {
            input.blur();
        }
    };

    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
}

// Bulk Actions
function setAllStock() {
    const modal = document.getElementById('stockModal');
    const input = document.getElementById('stockInput');
    const productCount = document.getElementById('stockModalProductCount');

    productCount.textContent = currentProducts.length;
    input.value = '100';
    modal.style.display = 'flex';
    setTimeout(() => input.focus(), 100);
}

function confirmSetStock() {
    const modal = document.getElementById('stockModal');
    const input = document.getElementById('stockInput');
    const stock = input.value.trim();

    if (stock && !isNaN(stock) && parseFloat(stock) >= 0) {
        currentProducts.forEach(product => {
            product.Stock_Count = stock;
        });
        displayProducts(currentProducts);
        modal.style.display = 'none';
        showSuccess(`Set stock to ${stock} for ${currentProducts.length} products`, 'Stock Updated');
    } else {
        showError('Please enter a valid stock amount', 'Invalid Input');
    }
}

function applyMarkup() {
    const modal = document.getElementById('markupModal');
    const input = document.getElementById('markupInput');
    const productCount = document.getElementById('markupModalProductCount');

    productCount.textContent = currentProducts.length;
    input.value = '30';
    modal.style.display = 'flex';
    setTimeout(() => input.focus(), 100);
    updateMarkupPreview();
}

function updateMarkupPreview() {
    const input = document.getElementById('markupInput');
    const preview = document.getElementById('markupPreview');
    const markup = parseFloat(input.value) || 0;

    if (markup > 0) {
        const samplePrice = 100;
        const newPrice = (samplePrice * (1 + markup / 100)).toFixed(2);
        preview.textContent = `Example: $${samplePrice} → $${newPrice}`;
        preview.style.opacity = '1';
    } else {
        preview.style.opacity = '0.5';
        preview.textContent = 'Enter markup to see preview';
    }
}

function confirmApplyMarkup() {
    const modal = document.getElementById('markupModal');
    const input = document.getElementById('markupInput');
    const markup = parseFloat(input.value);

    if (!isNaN(markup) && markup >= 0) {
        const markupPercent = markup / 100;
        let updatedCount = 0;

        currentProducts.forEach(product => {
            if (product.Wholesale_Price) {
                const basePrice = parseFloat(product.Wholesale_Price);
                product.Retail_Price = (basePrice * (1 + markupPercent)).toFixed(2);
                updatedCount++;
            }
        });

        displayProducts(currentProducts);
        modal.style.display = 'none';
        showSuccess(`Applied ${markup}% markup to ${updatedCount} products`, 'Markup Applied');
    } else {
        showError('Please enter a valid markup percentage', 'Invalid Input');
    }
}

function setAllActive() {
    const modal = document.getElementById('activateModal');
    const productCount = document.getElementById('activateModalProductCount');

    productCount.textContent = currentProducts.length;
    modal.style.display = 'flex';
}

function confirmSetActive() {
    const modal = document.getElementById('activateModal');

    currentProducts.forEach(product => {
        product.Status = '1';
    });

    displayProducts(currentProducts);
    modal.style.display = 'none';
    showSuccess(`Activated ${currentProducts.length} products`, 'Status Updated');
}

// Modal close functions
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modals when clicking outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('action-modal')) {
        e.target.style.display = 'none';
    }
});

// Add event listener for markup preview and SKU status
document.addEventListener('DOMContentLoaded', function() {
    const markupInput = document.getElementById('markupInput');
    if (markupInput) {
        markupInput.addEventListener('input', updateMarkupPreview);
    }

    // Listen for SKU auto-generate changes
    const autoGenerateSKU = document.getElementById('autoGenerateSKU');
    if (autoGenerateSKU) {
        autoGenerateSKU.addEventListener('change', updateSKUAutoStatus);
    }
});

// ============================================
// ADVANCED CONFIGURATION FUNCTIONS
// ============================================

function toggleAdvancedConfig() {
    const content = document.getElementById('advancedConfigContent');
    const toggle = document.getElementById('configToggle');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.classList.add('expanded');
        updateSKUAutoStatus(); // Update SKU status when opening
    } else {
        content.style.display = 'none';
        toggle.classList.remove('expanded');
    }
}

function updateSKUAutoStatus() {
    const autoGenerateSKU = document.getElementById('autoGenerateSKU');
    const skuStatus = document.getElementById('skuAutoStatus');

    if (skuStatus && autoGenerateSKU) {
        const isEnabled = autoGenerateSKU.checked;
        skuStatus.textContent = isEnabled ? '(Auto-Generate: ON)' : '(Auto-Generate: OFF)';
        skuStatus.style.color = isEnabled ? '#22c55e' : '#ef4444';
    }
}

function toggleAllFields() {
    const checkboxes = document.querySelectorAll('.config-option input[type="checkbox"]:not(:disabled)');
    const selectAllBtn = document.getElementById('selectAllText');

    // Check if all are currently selected
    let allSelected = true;
    checkboxes.forEach(checkbox => {
        if (!checkbox.checked) {
            allSelected = false;
        }
    });

    // Toggle all checkboxes
    checkboxes.forEach(checkbox => {
        checkbox.checked = !allSelected;
    });

    // Update button text
    selectAllBtn.textContent = allSelected ? 'Select All' : 'Deselect All';
}


function getSelectedFields() {
    const selectedFields = {};
    const checkboxes = document.querySelectorAll('.config-option input[type="checkbox"]:checked');

    checkboxes.forEach(checkbox => {
        const fieldName = checkbox.id.replace('extract_', '');
        selectedFields[fieldName] = true;
    });

    return selectedFields;
}

// Export Functions
async function downloadCSV() {
    try {
        const customName = document.getElementById('csvName')?.value.trim();
        let filename;

        if (customName) {
            // Use custom name with .csv extension
            filename = customName.endsWith('.csv') ? customName : customName + '.csv';
        } else {
            // Use default naming format
            filename = `products_${new Date().toISOString().split('T')[0]}.csv`;
        }

        // Convert currentProducts to CSV format
        const csvContent = convertToCSV(currentProducts);
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();

        showSuccess(`CSV exported successfully as "${filename}"`, 'Export Complete');

        // Clear the custom name after successful download
        if (document.getElementById('csvName')) {
            document.getElementById('csvName').value = '';
        }
    } catch (error) {
        showError('Failed to download CSV file: ' + error.message);
    }
}

function downloadExcel() {
    try {
        const customName = document.getElementById('csvName')?.value.trim();
        let filename;

        if (customName) {
            // Use custom name with .xls extension
            const baseName = customName.replace(/\.(csv|xls|xlsx)$/i, '');
            filename = baseName + '.xls';
        } else {
            // Use default naming format
            filename = `products_${new Date().toISOString().split('T')[0]}.xls`;
        }

        // For now, download as CSV with .xls extension (Excel can open it)
        const csvContent = convertToCSV(currentProducts);
        const blob = new Blob([csvContent], { type: 'application/vnd.ms-excel' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();

        showSuccess(`Excel file exported successfully as "${filename}"`, 'Export Complete');

        // Clear the custom name after successful download
        if (document.getElementById('csvName')) {
            document.getElementById('csvName').value = '';
        }
    } catch (error) {
        showError('Failed to download Excel file: ' + error.message);
    }
}

function downloadJSON() {
    try {
        const customName = document.getElementById('csvName')?.value.trim();
        let filename;

        if (customName) {
            // Use custom name with .json extension
            const baseName = customName.replace(/\.(csv|json|xls|xlsx)$/i, '');
            filename = baseName + '.json';
        } else {
            // Use default naming format
            filename = `products_${new Date().toISOString().split('T')[0]}.json`;
        }

        const jsonContent = JSON.stringify(currentProducts, null, 2);
        const blob = new Blob([jsonContent], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();

        showSuccess(`JSON file exported successfully as "${filename}"`, 'Export Complete');

        // Clear the custom name after successful download
        if (document.getElementById('csvName')) {
            document.getElementById('csvName').value = '';
        }
    } catch (error) {
        showError('Failed to download JSON file: ' + error.message);
    }
}

// Helper function to convert products to CSV
function convertToCSV(products) {
    if (products.length === 0) return '';

    // Define exact column order matching your template
    const columns = [
        'Name', 'SKU', 'Category', 'Brand', 'RFQ', 'Description',
        'Wholesale Price', 'MSRP', 'Stock Count', 'Min Order',
        'Expiry date', 'Key Features', 'Certificates', 'Specifications',
        'Images', 'Variations', 'Variants', 'Tiered Pricing', 'Status'
    ];

    // Create header
    const header = columns.join(',');

    // Create rows
    const rows = products.map(product => {
        return columns.map(col => {
            let value = '';

            // Map fields to correct column names
            switch(col) {
                case 'Name':
                    value = product.Name || product.name || '';
                    break;
                case 'SKU':
                    value = product.SKU || product.sku || '';
                    break;
                case 'Category':
                    value = product.Category || product.category || '';
                    break;
                case 'Brand':
                    value = product.Brand || product.brand || '';
                    break;
                case 'RFQ':
                    value = product.RFQ || 'Y';
                    break;
                case 'Description':
                    value = product.Description || product.description || '';
                    break;
                case 'Wholesale Price':
                    value = product.Wholesale_Price || product.wholesale_price || '';
                    break;
                case 'MSRP':
                    value = product.MSRP || product.Retail_Price || '';
                    break;
                case 'Stock Count':
                    value = product.Stock_Count || product.stock || '10';
                    break;
                case 'Min Order':
                    value = product.Min_Order || '';
                    break;
                case 'Expiry date':
                    value = product.Expiry_date || '';
                    break;
                case 'Key Features':
                    value = product.Key_Features || product.key_features || '';
                    break;
                case 'Certificates':
                    value = product.Certificates || '';
                    break;
                case 'Specifications':
                    value = product.Specifications || product.specifications || '';
                    break;
                case 'Images':
                    value = product.Images || product.images || '';
                    break;
                case 'Variations':
                    value = product.Variations || '';
                    break;
                case 'Variants':
                    value = product.Variants || '';
                    break;
                case 'Tiered Pricing':
                    value = product.Tiered_Pricing || '';
                    break;
                case 'Status':
                    value = product.Status || '1';
                    break;
                default:
                    value = '';
            }

            // Escape commas and quotes
            if (value.toString().includes(',') || value.toString().includes('"')) {
                return `"${value.toString().replace(/"/g, '""')}"`;
            }
            return value;
        }).join(',');
    });

    return header + '\n' + rows.join('\n');
}

// Incremental auto-save during progress
function saveProgressIncremental(job, jobType) {
    try {
        const timestamp = new Date().toISOString();
        const progressData = {
            jobId: job.id,
            jobType: jobType,
            status: job.status,
            progress: job.progress,
            total: job.total,
            message: job.message,
            timestamp: timestamp,
            partialResults: null
        };

        // Save partial results based on job type
        if (jobType === 'extract' && job.result && job.result.urls_found) {
            progressData.partialResults = job.result.urls_found.slice(0, job.progress);
        } else if (jobType === 'scrape' && job.result && job.result.products) {
            progressData.partialResults = job.result.products.slice(0, job.progress);
        }

        // Save to localStorage with timestamp
        localStorage.setItem('autoSaveProgress', JSON.stringify(progressData));

        // Show subtle indicator every 10 items processed
        if (job.progress % 10 === 0 && job.progress > 0) {
            const indicator = document.createElement('div');
            indicator.textContent = '💾';
            indicator.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1000; opacity: 0.7; font-size: 16px;';
            document.body.appendChild(indicator);
            setTimeout(() => indicator.remove(), 1000);
        }
    } catch (error) {
        console.error('Auto-save failed:', error);
    }
}

// Restore progress from auto-save
function restoreAutoSavedProgress() {
    try {
        const saved = localStorage.getItem('autoSaveProgress');
        if (saved) {
            const progressData = JSON.parse(saved);
            const timeDiff = new Date() - new Date(progressData.timestamp);

            // Only restore if less than 1 hour old
            if (timeDiff < 3600000) {
                if (progressData.jobType === 'extract' && progressData.partialResults) {
                    document.getElementById('urlList').value = progressData.partialResults.join('\n');
                    showInfo(`Restored ${progressData.partialResults.length} URLs from auto-save`, 'Progress Restored');
                } else if (progressData.jobType === 'scrape' && progressData.partialResults) {
                    if (document.getElementById('autoSave').checked) {
                        currentSession.scrapedProducts.push(...progressData.partialResults);
                        updateSessionDisplay();
                        showInfo(`Restored ${progressData.partialResults.length} products from auto-save`, 'Progress Restored');
                    }
                }
            }
        }
    } catch (error) {
        console.error('Failed to restore auto-saved progress:', error);
    }
}

// Theme Toggle
function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? '' : 'dark';

    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    const themeBtn = document.getElementById('themeToggle');
    themeBtn.textContent = newTheme === 'dark' ? 'Light Mode' : 'Dark Mode';

    showInfo(`Switched to ${newTheme === 'dark' ? 'dark' : 'light'} mode`, 'Theme Changed');
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.body.setAttribute('data-theme', savedTheme);
        const themeBtn = document.getElementById('themeToggle');
        if (themeBtn) {
            themeBtn.textContent = savedTheme === 'dark' ? 'Light Mode' : 'Dark Mode';
        }
    }

    // These are handled by window.onload

    // Auto-validate API keys if they exist
    setTimeout(() => {
        const apiKeyInput = document.getElementById('apiKey');
        const groqKeyInput = document.getElementById('groqKey');

        if (apiKeyInput && apiKeyInput.value.trim()) {
            validateApiKey('firecrawl');
        }

        if (groqKeyInput && groqKeyInput.value.trim()) {
            validateApiKey('groq');
        }

        // Check system status immediately
        checkSystemStatus();

        // Set up periodic status checks every 30 seconds
        setInterval(checkSystemStatus, 30000);
    }, 1000);
});

// Settings Modal
function toggleSettings() {
    const modal = document.getElementById('settingsModal');
    modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
}

function saveSettings() {
    const extractionMode = document.querySelector('input[name="extractionMode"]:checked')?.value || 'wsmarketplace';
    const settings = {
        apiKey: document.getElementById('apiKey').value,
        groqKey: document.getElementById('groqKey').value,
        timeout: document.getElementById('timeout').value,
        maxProducts: document.getElementById('maxProducts').value,
        apiRetries: document.getElementById('apiRetries')?.value || '1',
        autoGenerateSKU: document.getElementById('autoGenerateSKUMain')?.checked || false,
        autoGenerateDescription: document.getElementById('autoGenerateDescriptionMain')?.checked || false,
        extractionMode: extractionMode,
        userHasSelectedMode: true,
        // Inventory defaults
        defaultStock: document.getElementById('defaultStockMain')?.value || '10',
        defaultMinOrder: document.getElementById('defaultMinOrderMain')?.value || '1',
        defaultStatus: document.getElementById('defaultStatusMain')?.value || 'Active',
        defaultRFQ: document.getElementById('defaultRFQMain')?.value || 'Y',
        defaultCategory: document.getElementById('defaultCategoryMain')?.value || 'General',
        defaultSupplier: document.getElementById('defaultSupplierMain')?.value || '',
        defaultWeight: document.getElementById('defaultWeightMain')?.value || '0.5',
        defaultLeadTime: document.getElementById('defaultLeadTimeMain')?.value || '3',
        // JustSell boolean settings (will be ignored for WSMarketplace)
        isFeatured: document.getElementById('isFeaturedMain')?.value || 'FALSE',
        continueSelling: document.getElementById('continueSellingMain')?.value || 'FALSE',
        published: document.getElementById('publishedMain')?.value || 'TRUE',
        requiresShipping: document.getElementById('requiresShippingMain')?.value || 'TRUE',
        taxable: document.getElementById('taxableMain')?.value || 'TRUE',
        euronics: document.getElementById('euronicsMain')?.value || 'FALSE'
    };

    localStorage.setItem('appSettings', JSON.stringify(settings));
    showSuccess('Settings have been saved successfully', 'Settings Saved');

    // Update system status after settings change
    setTimeout(checkSystemStatus, 500);

    toggleSettings();
}

function loadSettings() {
    const saved = localStorage.getItem('appSettings');
    if (saved) {
        const settings = JSON.parse(saved);
        if (document.getElementById('apiKey')) {
            document.getElementById('apiKey').value = settings.apiKey || '';
        }
        if (document.getElementById('groqKey')) {
            document.getElementById('groqKey').value = settings.groqKey || '';
        }
        if (document.getElementById('timeout')) {
            document.getElementById('timeout').value = settings.timeout || '10';
        }
        if (document.getElementById('maxProducts')) {
            document.getElementById('maxProducts').value = settings.maxProducts || '50';
        }
        if (document.getElementById('autoGenerateSKUMain')) {
            document.getElementById('autoGenerateSKUMain').checked = settings.autoGenerateSKU !== false; // Default to true
        }
        if (document.getElementById('autoGenerateDescriptionMain')) {
            document.getElementById('autoGenerateDescriptionMain').checked = settings.autoGenerateDescription === true; // Default to false
        }

        // Load extraction mode
        const extractionMode = settings.extractionMode || 'standard';
        const modeRadio = document.querySelector(`input[name="extractionMode"][value="${extractionMode}"]`);
        if (modeRadio) {
            modeRadio.checked = true;
            // Update the main intelligence engine selection WITHOUT notification
            selectIntelligenceModeQuiet(extractionMode);
        }
    }
}

// Load marketplace selection on page load - DISABLED per user request
function loadMarketplaceSelection() {
    // User wants NO pre-selection - they must manually choose every time
    console.log('Marketplace selection disabled - user must choose manually');

    // Clear any existing selections
    document.querySelectorAll('.intelligence-card').forEach(card => {
        card.classList.remove('selected');
    });
    document.querySelectorAll('.intelligence-option').forEach(option => {
        option.classList.remove('selected');
    });
    document.querySelectorAll('input[name="extractionMode"]').forEach(radio => {
        radio.checked = false;
    });

    // Update status text to show nothing selected
    const statusText = document.getElementById('selectedMode');
    if (statusText) {
        statusText.textContent = 'Please select a marketplace format';
        statusText.style.color = '#6b7280';  // Gray color for unselected
    }
}

// Intelligence Engine Selection Functions
function selectIntelligenceMode(mode) {
    // Check if there are existing products and warn about format change
    const existingProducts = document.querySelectorAll('#resultsTable tbody tr');
    if (existingProducts.length > 0) {
        // Get current mode from the currently checked radio button for accuracy
        const currentRadio = document.querySelector('input[name="extractionMode"]:checked');
        const currentMode = currentRadio ? currentRadio.value : 'wsmarketplace';

        if (currentMode && currentMode !== mode) {
            const currentName = currentMode === 'justsell' ? 'JustSell' : 'WSMarketplace';
            const newName = mode === 'justsell' ? 'JustSell' : 'WSMarketplace';

            if (!confirm(`⚠️ FORMAT CHANGE WARNING\n\nYou currently have ${existingProducts.length} products imported using ${currentName} format.\n\nChanging to ${newName} will use a completely different CSV format (${currentName === 'justsell' ? '61' : '22'} columns vs ${mode === 'justsell' ? '61' : '22'} columns).\n\nThis will cause issues if you mix formats in the same session.\n\nRecommended: Finalize your current session first, then start a new session with ${newName}.\n\nDo you want to continue changing formats anyway?`)) {
                return; // User cancelled the format change
            }

            showWarning(`Format changed to ${newName}. Consider finalizing this session and starting fresh to avoid CSV format conflicts.`, 'Format Change Warning');
        }
    }

    // Clear all selections
    document.querySelectorAll('.intelligence-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Select the clicked mode - find the card by the parent onclick attribute
    let selectedCard;
    if (mode === 'wsmarketplace') {
        selectedCard = document.querySelector('.intelligence-option[onclick*="wsmarketplace"] .intelligence-card');
    } else if (mode === 'justsell') {
        selectedCard = document.querySelector('.intelligence-option[onclick*="justsell"] .intelligence-card');
    }

    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    // IMPORTANT: Update radio button - this is what gets sent to backend
    const radio = document.querySelector(`input[name="extractionMode"][value="${mode}"]`);
    if (radio) {
        radio.checked = true;
        // Force save settings to ensure the mode is stored
        const settings = getSettings();
        settings.extractionMode = mode;
        settings.userHasSelectedMode = true;
        localStorage.setItem('appSettings', JSON.stringify(settings));
    }

    // Update status text
    const statusText = document.getElementById('selectedMode');
    if (statusText) {
        const modeName = mode === 'justsell' ? 'JustSell PRO' : 'WSMarketplace PRO';
        statusText.textContent = modeName;
        statusText.style.color = '#10b981';  // Green color for selected
    }

    // Update marketplace-specific inventory defaults
    updateInventoryDefaults(mode);

    // Check if we should show format lock notice
    updateFormatLockNotice();

    // Save the selection immediately
    const settings = getSettings();
    settings.extractionMode = mode;
    settings.userHasSelectedMode = true;  // Flag that user made a conscious choice

    localStorage.setItem('appSettings', JSON.stringify(settings));
}

// Quiet version for loading settings without notifications
function selectIntelligenceModeQuiet(mode) {
    // Clear all selections
    document.querySelectorAll('.intelligence-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Select the clicked mode - find the card by the parent onclick attribute
    let selectedCard;
    if (mode === 'wsmarketplace') {
        selectedCard = document.querySelector('.intelligence-option[onclick*="wsmarketplace"] .intelligence-card');
    } else if (mode === 'justsell') {
        selectedCard = document.querySelector('.intelligence-option[onclick*="justsell"] .intelligence-card');
    }
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    // Update radio button
    const radio = document.querySelector(`input[name="extractionMode"][value="${mode}"]`);
    if (radio) {
        radio.checked = true;
    }

    // Update status text
    const statusText = document.getElementById('selectedMode');
    if (statusText) {
        const modeName = mode === 'justsell' ? 'JustSell PRO' : 'WSMarketplace PRO';
        statusText.textContent = modeName;
        statusText.style.color = '#10b981';  // Green color for selected
    }

    // Update inventory defaults quietly (no notifications)
    updateInventoryDefaultsQuiet(mode);
    updateFormatLockNotice();
}

// Quiet version for loading settings without notifications
function updateInventoryDefaultsQuiet(mode) {
    const defaultStock = document.getElementById('defaultStockMain');
    const defaultStatus = document.getElementById('defaultStatusMain');
    const defaultMinOrder = document.getElementById('defaultMinOrderMain');
    const defaultRFQ = document.getElementById('defaultRFQMain');
    const defaultCategory = document.getElementById('defaultCategoryMain');
    const defaultSupplier = document.getElementById('defaultSupplierMain');
    const defaultWeight = document.getElementById('defaultWeightMain');
    const defaultLeadTime = document.getElementById('defaultLeadTimeMain');
    const booleanSettings = document.getElementById('justSellBooleanSettings');

    if (mode === 'justsell') {
        // JustSell marketplace defaults (e-commerce focused)
        if (defaultStock) defaultStock.value = '50';
        if (defaultStatus) defaultStatus.value = 'Active';
        if (defaultMinOrder) defaultMinOrder.value = '1';
        if (defaultRFQ) defaultRFQ.value = 'N';
        if (defaultCategory) defaultCategory.value = 'Electronics';
        if (defaultSupplier) defaultSupplier.value = '';
        if (defaultWeight) defaultWeight.value = '0.3';
        if (defaultLeadTime) defaultLeadTime.value = '1';

        if (booleanSettings) booleanSettings.style.display = 'grid';

        const isFeatured = document.getElementById('isFeaturedMain');
        const continueSelling = document.getElementById('continueSellingMain');
        const published = document.getElementById('publishedMain');
        const requiresShipping = document.getElementById('requiresShippingMain');
        const taxable = document.getElementById('taxableMain');
        const euronics = document.getElementById('euronicsMain');
        if (isFeatured) isFeatured.value = 'FALSE';
        if (continueSelling) continueSelling.value = 'FALSE';
        if (published) published.value = 'TRUE';
        if (requiresShipping) requiresShipping.value = 'TRUE';
        if (taxable) taxable.value = 'TRUE';
        if (euronics) euronics.value = 'FALSE';
        // NO notification in quiet mode
    } else {
        // WSMarketplace defaults (wholesale focused)
        if (defaultStock) defaultStock.value = '10';
        if (defaultStatus) defaultStatus.value = 'Active';
        if (defaultMinOrder) defaultMinOrder.value = '5';
        if (defaultRFQ) defaultRFQ.value = 'Y';
        if (defaultCategory) defaultCategory.value = 'Vape';
        if (defaultSupplier) defaultSupplier.value = '';
        if (defaultWeight) defaultWeight.value = '0.5';
        if (defaultLeadTime) defaultLeadTime.value = '5';

        if (booleanSettings) booleanSettings.style.display = 'none';
        // NO notification in quiet mode
    }
}

// Update inventory defaults based on selected marketplace
function updateInventoryDefaults(mode) {
    const defaultStock = document.getElementById('defaultStockMain');
    const defaultStatus = document.getElementById('defaultStatusMain');
    const defaultMinOrder = document.getElementById('defaultMinOrderMain');
    const defaultRFQ = document.getElementById('defaultRFQMain');
    const defaultCategory = document.getElementById('defaultCategoryMain');
    const defaultSupplier = document.getElementById('defaultSupplierMain');
    const defaultWeight = document.getElementById('defaultWeightMain');
    const defaultLeadTime = document.getElementById('defaultLeadTimeMain');
    const booleanSettings = document.getElementById('justSellBooleanSettings');

    if (mode === 'justsell') {
        // JustSell marketplace defaults (e-commerce focused)
        if (defaultStock) defaultStock.value = '50';  // Higher stock for direct sales
        if (defaultStatus) defaultStatus.value = 'Active';  // Active for e-commerce
        if (defaultMinOrder) defaultMinOrder.value = '1';  // Lower minimum order
        if (defaultRFQ) defaultRFQ.value = 'N';  // RFQ not common in B2C
        if (defaultCategory) defaultCategory.value = 'Electronics';  // B2C category
        if (defaultSupplier) defaultSupplier.value = '';  // Clear for B2C
        if (defaultWeight) defaultWeight.value = '0.3';  // Lighter consumer products
        if (defaultLeadTime) defaultLeadTime.value = '1';  // Faster B2C delivery

        // Show and set JustSell-specific boolean defaults
        if (booleanSettings) booleanSettings.style.display = 'grid';

        // Set JustSell boolean defaults based on CSV analysis
        const isFeatured = document.getElementById('isFeaturedMain');
        const continueSelling = document.getElementById('continueSellingMain');
        const published = document.getElementById('publishedMain');
        const requiresShipping = document.getElementById('requiresShippingMain');
        const taxable = document.getElementById('taxableMain');
        const euronics = document.getElementById('euronicsMain');

        if (isFeatured) isFeatured.value = 'FALSE';
        if (continueSelling) continueSelling.value = 'FALSE';
        if (published) published.value = 'TRUE';
        if (requiresShipping) requiresShipping.value = 'TRUE';
        if (taxable) taxable.value = 'TRUE';
        if (euronics) euronics.value = 'FALSE';

        showInfo('Inventory defaults updated for JustSell marketplace (B2C e-commerce focused)', 'JustSell Settings');
    } else {
        // WSMarketplace defaults (wholesale focused)
        if (defaultStock) defaultStock.value = '10';  // Lower stock for wholesale
        if (defaultStatus) defaultStatus.value = 'Active';  // Active for wholesale
        if (defaultMinOrder) defaultMinOrder.value = '5';  // Higher minimum for wholesale
        if (defaultRFQ) defaultRFQ.value = 'Y';  // RFQ important for B2B
        if (defaultCategory) defaultCategory.value = 'Vape';  // B2B wholesale category
        if (defaultSupplier) defaultSupplier.value = '';  // Clear for user input
        if (defaultWeight) defaultWeight.value = '0.5';  // Standard weight
        if (defaultLeadTime) defaultLeadTime.value = '5';  // Longer B2B lead time

        // Hide JustSell-specific boolean settings
        if (booleanSettings) booleanSettings.style.display = 'none';

        showInfo('Inventory defaults updated for WSMarketplace (B2B wholesale focused)', 'WSMarketplace Settings');
    }
}

// Update format lock notice based on current session state
function updateFormatLockNotice() {
    const formatLockNotice = document.getElementById('formatLockNotice');
    const formatLockText = document.getElementById('formatLockText');
    const existingProducts = document.querySelectorAll('#resultsTable tbody tr');

    if (existingProducts.length > 0 && formatLockNotice && formatLockText) {
        const settings = getSettings();
        const currentMode = settings.extractionMode || 'wsmarketplace';
        const modeName = currentMode === 'justsell' ? 'JustSell' : 'WSMarketplace';

        formatLockNotice.style.display = 'block';
        formatLockText.textContent = `Format locked to ${modeName} (${existingProducts.length} products in session)`;
        formatLockText.style.color = '#ef4444';  // Red warning color
    } else if (formatLockNotice) {
        formatLockNotice.style.display = 'none';
    }
}

// Toggle inventory defaults section
function toggleInventoryDefaults() {
    const content = document.getElementById('inventoryDefaultsContent');
    const toggle = document.getElementById('inventoryToggle');

    if (content.style.display === 'none') {
        content.style.display = 'block';
        toggle.classList.remove('collapsed');
        toggle.setAttribute('aria-expanded', 'true');
    } else {
        content.style.display = 'none';
        toggle.classList.add('collapsed');
        toggle.setAttribute('aria-expanded', 'false');
    }
}

// Initialize intelligence engine on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Intelligence engine ready - marketplace selection will be loaded by window.onload');
});

// Help Modal Functions
function showHelp() {
    const modal = document.getElementById('helpModal');
    modal.style.display = 'block';
    setTimeout(() => {
        modal.classList.add('show');
    }, 10);
}

function closeHelp() {
    const modal = document.getElementById('helpModal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

// Documentation
function showDocs() {
    window.open('https://github.com/Uptivity/IntelliScrape-Pro', '_blank');
}

// Close modal when clicking outside
window.onclick = function(event) {
    const settingsModal = document.getElementById('settingsModal');
    const sessionsModal = document.getElementById('sessionsModal');

    if (event.target === settingsModal) {
        settingsModal.style.display = 'none';
    }
    if (event.target === sessionsModal) {
        sessionsModal.style.display = 'none';
    }
}

// Session Management Functions
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function showSessions() {
    const modal = document.getElementById('sessionsModal');
    modal.style.display = 'block';
    updateSessionDisplay();
}

function closeSessions() {
    document.getElementById('sessionsModal').style.display = 'none';
}

function updateSessionSummaryTable() {
    const summaryElement = document.getElementById('sessionSummary');
    if (!summaryElement) return;

    if (currentSession.products.length === 0) {
        summaryElement.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No products in current session</p>';
        return;
    }

    // Group products by brand
    const brandGroups = {};
    currentSession.products.forEach(product => {
        const brand = product.brand || 'Unknown';
        if (!brandGroups[brand]) {
            brandGroups[brand] = [];
        }
        brandGroups[brand].push(product);
    });

    // Create summary HTML
    let html = '<div class="brand-summary-list">';
    Object.entries(brandGroups).forEach(([brand, products]) => {
        html += `
            <div class="brand-summary-item">
                <div class="brand-header">
                    <span class="brand-name">${brand}</span>
                    <span class="brand-count">${products.length} products</span>
                </div>
            </div>`;
    });
    html += '</div>';

    summaryElement.innerHTML = html;
}

function updateSessionDisplay() {
    // Update active session info
    const sessionIdElement = document.getElementById('sessionId');
    const sessionStatusElement = document.getElementById('sessionStatus');

    if (sessionIdElement) {
        sessionIdElement.textContent = currentSession.id.substring(0, 20) + '...';
    }

    // Update product count in multiple places
    const productCount = currentSession.products.length;
    const sessionProductCountElement = document.getElementById('sessionProductCount');
    const sessionCountElement = document.getElementById('sessionCount');

    if (sessionProductCountElement) {
        sessionProductCountElement.textContent = productCount;
    }
    if (sessionCountElement) {
        sessionCountElement.textContent = productCount;
    }

    // Update status badge
    if (sessionStatusElement) {
        sessionStatusElement.textContent = currentSession.status === 'active' ? 'Active' : 'Finalized';
        sessionStatusElement.className = currentSession.status === 'active' ? 'status-badge active' : 'status-badge';
    }

    // Update brand and category counts
    const brands = new Set();
    const categories = new Set();

    currentSession.products.forEach(product => {
        // Check both uppercase and lowercase field names
        const brand = product.Brand || product.brand;
        const category = product.Category || product.category;
        if (brand) brands.add(brand);
        if (category) categories.add(category);
    });

    const sessionBrandCountElement = document.getElementById('sessionBrandCount');
    const sessionCategoryCountElement = document.getElementById('sessionCategoryCount');

    if (sessionBrandCountElement) {
        sessionBrandCountElement.textContent = brands.size;
    }
    if (sessionCategoryCountElement) {
        sessionCategoryCountElement.textContent = categories.size;
    }

    // Update session started time
    const sessionStartedElement = document.getElementById('sessionStarted');
    if (sessionStartedElement) {
        sessionStartedElement.textContent = new Date(currentSession.created).toLocaleString();
    }

    // Update session summary table
    updateSessionSummaryTable();

    // Update session indicator in status bar
    const sessionIndicator = document.getElementById('sessionIndicator');
    if (sessionIndicator) {
        sessionIndicator.textContent = `Session: ${currentSession.products.length} items`;
    }

    // Update total products counter
    if (document.getElementById('totalProducts')) {
        document.getElementById('totalProducts').textContent = currentSession.products.length;
    }

    // Update completed sessions list
    updateCompletedSessions();
}

function updateCompletedSessions() {
    const list = document.getElementById('completedList');

    // Check if element exists - if not, just return silently
    if (!list) {
        console.log('Completed sessions list element not found - skipping update');
        return;
    }

    if (completedSessions.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 40px;">No completed sessions yet</p>';
        return;
    }

    let html = '<div class="sessions-list">';
    completedSessions.forEach((session, index) => {
        const createdDate = new Date(session.createdAt);
        const completedDate = session.completedAt ? new Date(session.completedAt) : createdDate;
        const brands = [...new Set(session.products.map(p => p.Brand || p.brand).filter(Boolean))];
        const categories = [...new Set(session.products.map(p => p.Category || p.category).filter(Boolean))];
        const totalValue = session.products.reduce((sum, p) => {
            const price = parseFloat(p["Wholesale Price"] || p["Wholesale_Price"] || p.MSRP || p.Price || p.price) || 0;
            return sum + price;
        }, 0);

        html += `
            <div class="session-item detailed">
                <div class="session-header">
                    <div class="session-title">
                        <h4>${session.name || `Session ${index + 1}`}</h4>
                        <span class="session-id">ID: ${session.id ? session.id.substring(0, 8) : 'N/A'}</span>
                    </div>
                    <div class="session-actions">
                        <button class="action-btn download" onclick="downloadCompletedSession(${index})" title="Download CSV">
                            📥 Download
                        </button>
                        <button class="action-btn view" onclick="viewSessionDetails(${index})" title="View Details">
                            👁️ View
                        </button>
                        <button class="action-btn delete" onclick="deleteSession(${index})" title="Delete Session">
                            🗑️ Delete
                        </button>
                    </div>
                </div>
                <div class="session-stats">
                    <div class="stat-group">
                        <div class="stat">
                            <span class="stat-value">${session.products.length}</span>
                            <span class="stat-label">Products</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${brands.length}</span>
                            <span class="stat-label">Brands</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">${categories.length}</span>
                            <span class="stat-label">Categories</span>
                        </div>
                        <div class="stat">
                            <span class="stat-value">$${totalValue.toFixed(2)}</span>
                            <span class="stat-label">Total Value</span>
                        </div>
                    </div>
                </div>
                <div class="session-meta">
                    <div class="meta-item">
                        <span class="meta-label">Created:</span>
                        <span class="meta-value">${createdDate.toLocaleDateString()} ${createdDate.toLocaleTimeString()}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Completed:</span>
                        <span class="meta-value">${completedDate.toLocaleDateString()} ${completedDate.toLocaleTimeString()}</span>
                    </div>
                    ${brands.length > 0 ? `
                    <div class="meta-item">
                        <span class="meta-label">Top Brands:</span>
                        <span class="meta-value">${brands.slice(0, 3).join(', ')}${brands.length > 3 ? ` +${brands.length - 3} more` : ''}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    });
    html += '</div>';
    list.innerHTML = html;
}

function finalizeSession() {
    if (currentSession.products.length === 0) {
        showWarning('No products in current session', 'Session Empty');
        return;
    }

    // Update the modal with current session info
    const confirmProductCount = document.getElementById('confirmProductCount');
    if (confirmProductCount) {
        confirmProductCount.textContent = currentSession.products.length;
    }

    // Show the finalize modal
    const modal = document.getElementById('finalizeModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function performFinalization() {
    // Create CSV and download
    const csvContent = convertToCSV(currentSession.products);
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `products_${new Date().getTime()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);

    // Save to completed sessions
    const completedSessions = JSON.parse(localStorage.getItem('completedSessions') || '[]');
    const sessionData = {
        id: currentSession.id,
        timestamp: new Date().toISOString(),
        productCount: currentSession.products.length,
        products: currentSession.products
    };
    completedSessions.push(sessionData);
    localStorage.setItem('completedSessions', JSON.stringify(completedSessions));

    // Reset current session
    currentSession = {
        id: generateSessionId(),
        products: [],
        startTime: new Date()
    };
    localStorage.setItem('currentSession', JSON.stringify(currentSession));

    // Update UI
    updateDashboard();
    showSuccess(`Session finalized with ${sessionData.productCount} products`, 'Session Complete');
}

function showFinalizeModal() {
    const modal = document.getElementById('finalizeModal');
    const productCount = document.getElementById('confirmProductCount');
    const sessionNameInput = document.getElementById('finalizeSessionName');

    // Update product count
    productCount.textContent = currentSession.products.length;

    // Set default session name
    sessionNameInput.value = `Session_${new Date().toISOString().split('T')[0]}`;

    // Show modal
    modal.style.display = 'block';
}

function closeFinalizeModal() {
    document.getElementById('finalizeModal').style.display = 'none';
}

function confirmFinalization() {
    const sessionNameInput = document.getElementById('finalizeSessionName');
    const sessionName = sessionNameInput.value.trim() || `Session_${new Date().toISOString().split('T')[0]}_${Math.random().toString(36).substr(2, 4)}`;

    // Close modal
    closeFinalizeModal();

    if (currentSession.products.length === 0) {
        showWarning('No products to finalize', 'Session Empty');
        return;
    }

    // Generate SKUs for products that don't have them if auto-generate is enabled
    const autoGenerateSKU = document.getElementById('autoGenerateSKU')?.checked;
    if (autoGenerateSKU) {
        let skusGenerated = 0;
        currentSession.products.forEach((product, index) => {
            if (!product.SKU || product.SKU.trim() === '') {
                product.SKU = generateSKUFromName(product.Name || product.name || `Product`, index + 1);
                skusGenerated++;
            }
        });
        if (skusGenerated > 0) {
            console.log(`Generated ${skusGenerated} SKUs during finalization`);
        }
    }

    // Create CSV and download
    const csvContent = convertToCSV(currentSession.products);
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sessionName.replace(/[^a-z0-9]/gi, '_')}_products.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    // Mark session as completed
    currentSession.status = 'completed';
    currentSession.completedAt = new Date().toISOString();
    currentSession.name = sessionName;

    // Add summary stats to session
    const sessionProducts = currentSession.products.length;
    currentSession.summary = {
        totalProducts: sessionProducts,
        uniqueBrands: [...new Set(currentSession.products.map(p => p.brand || 'Unknown'))].length,
        categories: [...new Set(currentSession.products.map(p => p.category || 'Unknown'))].length,
        averagePrice: currentSession.products.reduce((sum, p) => sum + (parseFloat(p.price) || 0), 0) / sessionProducts || 0
    };

    // Save completed session to localStorage
    const completedSessions = JSON.parse(localStorage.getItem('completedSessions') || '[]');
    completedSessions.push(currentSession);
    localStorage.setItem('completedSessions', JSON.stringify(completedSessions));

    showSuccess(`Session "${sessionName}" has been finalized with ${sessionProducts} products`, 'Session Completed');

    // Reset current session for new work
    currentSession = {
        id: generateSessionId(),
        products: [],
        status: 'active',
        created: new Date().toISOString()
    };
    currentProducts = [];

    // Save new session
    localStorage.setItem('currentSession', JSON.stringify(currentSession));

    // Update UI
    updateSessionDisplay();
    updateCompletedSessions();

    // Clear the results display
    document.getElementById('scrapeResults').style.display = 'none';
    document.getElementById('productTable').innerHTML = '';

    showSuccess(`Session "${currentSession.name}" has been completed and saved. Ready for new session.`, 'Session Finalized');

    // Auto-download CSV of finalized session was already done above

    showInfo(`Session CSV automatically downloaded as "${currentSession.name}.csv"`, 'Auto Export');

    // Start new session
    currentSession = {
        id: generateSessionId(),
        products: [],
        status: 'active',
        createdAt: new Date().toISOString()
    };

    currentProducts = [];

    // Update UI
    updateSessionDisplay();
    displayProducts([]);
}

function clearSession() {
    if (confirm('Clear current session? This will remove all products from the active session.')) {
        currentSession.products = [];
        currentProducts = [];
        updateSessionDisplay();
        displayProducts([]);
    }
}

function downloadSession() {
    const csvContent = convertToCSV(currentSession.products);
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `session_${currentSession.id.substring(8, 20)}.csv`;
    a.click();
}

function downloadCompletedSession(index) {
    const session = completedSessions[index];
    const csvContent = convertToCSV(session.products);
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${session.name || 'session'}_${session.id?.substring(8, 20) || index}.csv`;
    a.click();
}

// View session details
function viewSessionDetails(index) {
    const session = completedSessions[index];
    const brands = [...new Set(session.products.map(p => p.Brand || p.brand).filter(Boolean))];
    const categories = [...new Set(session.products.map(p => p.Category || p.category).filter(Boolean))];

    let detailsHtml = `
        <div class="session-details">
            <h3>${session.name || `Session ${index + 1}`} Details</h3>

            <div class="details-section">
                <h4>📊 Overview</h4>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Total Products:</span>
                        <span class="detail-value">${session.products.length}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Unique Brands:</span>
                        <span class="detail-value">${brands.length}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Categories:</span>
                        <span class="detail-value">${categories.length}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Session ID:</span>
                        <span class="detail-value">${session.id || 'N/A'}</span>
                    </div>
                </div>
            </div>

            ${brands.length > 0 ? `
            <div class="details-section">
                <h4>🏷️ Brands</h4>
                <div class="brand-list">
                    ${brands.map(brand => `<span class="brand-tag">${brand}</span>`).join('')}
                </div>
            </div>
            ` : ''}

            ${categories.length > 0 ? `
            <div class="details-section">
                <h4>📁 Categories</h4>
                <div class="category-list">
                    ${categories.map(category => `<span class="category-tag">${category}</span>`).join('')}
                </div>
            </div>
            ` : ''}

            <div class="details-section">
                <h4>📋 Recent Products</h4>
                <div class="product-preview">
                    ${session.products.slice(0, 5).map(product => `
                        <div class="product-preview-item">
                            <strong>${product.Name || product.name || 'Unnamed Product'}</strong>
                            <span class="product-brand">${product.Brand || product.brand || 'No Brand'}</span>
                            <span class="product-price">${product.Price || product.price || 'No Price'}</span>
                        </div>
                    `).join('')}
                    ${session.products.length > 5 ? `<p class="more-products">... and ${session.products.length - 5} more products</p>` : ''}
                </div>
            </div>
        </div>
    `;

    document.getElementById('detailModalTitle').textContent = 'Session Details';
    document.getElementById('detailModalContent').innerHTML = detailsHtml;
    document.getElementById('detailModal').style.display = 'block';
}

// Delete session
function deleteSession(index) {
    const session = completedSessions[index];
    const sessionName = session.name || `Session ${index + 1}`;

    if (confirm(`Are you sure you want to delete "${sessionName}"? This action cannot be undone.`)) {
        completedSessions.splice(index, 1);
        localStorage.setItem('completedSessions', JSON.stringify(completedSessions));
        updateCompletedSessions();
        updateDashboard();
        showSuccess(`Session "${sessionName}" has been deleted`, 'Session Deleted');
    }
}

// Close detail modal
function closeDetailModal() {
    document.getElementById('detailModal').style.display = 'none';
}

function addMoreProducts() {
    // Scroll back to scraping section
    document.getElementById('scrapeUrls').scrollIntoView({ behavior: 'smooth' });
    document.getElementById('scrapeUrls').value = '';
    document.getElementById('scrapeUrls').focus();
}

// Configuration Tab Switching
function switchConfigTab(tabName) {
    // Remove active class from all tabs
    document.querySelectorAll('.config-tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Hide all content
    document.querySelectorAll('.config-content').forEach(content => {
        content.classList.remove('active');
    });

    // Activate selected tab
    event.target.closest('.config-tab').classList.add('active');

    // Show selected content with fade animation
    const content = document.getElementById(tabName + 'Config');
    setTimeout(() => {
        content.classList.add('active');
    }, 50);
}

// Session Tab Switching
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(tabName + 'Tab').classList.add('active');
}

// Update scraping to append to session
function handleScrapeCompleteWithSession(job) {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const btnText = scrapeBtn.querySelector('.btn-text');
    const btnSpinner = scrapeBtn.querySelector('.btn-spinner');

    // Hide stop button
    const stopBtn = document.getElementById('stopScrapeBtn');
    if (stopBtn) {
        stopBtn.style.display = 'none';
    }

    // Hide spinner
    btnSpinner.style.display = 'none';

    if (job.status === 'completed' && job.result) {
        const newProducts = job.result.products || [];

        console.log('Scraping completed. Products received:', newProducts.length);

        // Check if appending to session
        if (document.getElementById('appendToSession')?.checked) {
            // Append to existing session
            currentSession.products = [...currentSession.products, ...newProducts];
            currentProducts = currentSession.products;
        } else {
            // Replace current products
            currentSession.products = newProducts;
            currentProducts = newProducts;
        }

        // Apply configuration (including SKU generation) - but don't let it break the display
        try {
            applyConfigToProducts();
        } catch (error) {
            console.error('Error applying configuration:', error);
        }

        // Display the updated products with generated SKUs
        displayProducts(currentProducts);

        // Show success state
        btnText.textContent = '✓ Completed';
        scrapeBtn.style.background = '#10b981';

        // Update displays
        updateSessionDisplay();

        // Ensure results section is visible
        const resultsSection = document.getElementById('scrapeResults');
        if (resultsSection) {
            resultsSection.style.display = 'block';
        } else {
            console.error('Scrape results section not found!');
        }

        // Display products again to ensure they show
        displayProducts(currentProducts);

        // Update status message
        const statusElement = document.getElementById('scrapeStatus');
        if (statusElement) {
            statusElement.textContent = `Scraping complete! Added ${newProducts.length} products to session`;
        }

        showSuccess(`Successfully scraped ${newProducts.length} products and added to session`, 'Product Scraping Complete');

        // Reset job ID when scraping completes
        currentScrapeJobId = null;

        // Auto-save if enabled
        if (document.getElementById('autoSave').checked) {
            localStorage.setItem('currentSession', JSON.stringify(currentSession));
        }

        // Reset button after 3 seconds
        setTimeout(() => {
            scrapeBtn.disabled = false;
            scrapeBtn.classList.remove('loading');
            btnText.textContent = 'Execute Scraping';
            scrapeBtn.style.background = '';
        }, 3000);
    } else {
        // Hide stop button even on failure
        const stopBtnFail = document.getElementById('stopScrapeBtn');
        if (stopBtnFail) {
            stopBtnFail.style.display = 'none';
        }

        // Show error state
        btnText.textContent = '✕ Failed';
        scrapeBtn.style.background = '#ef4444';
        document.getElementById('scrapeStatus').textContent = 'Scraping failed: ' + (job.error || 'Unknown error');
        showError('Product scraping failed: ' + (job.error || 'Unknown error'), 'Scraping Failed');

        // Reset button after 3 seconds
        setTimeout(() => {
            scrapeBtn.disabled = false;
            scrapeBtn.classList.remove('loading');
            btnText.textContent = 'Execute Scraping';
            scrapeBtn.style.background = '';
        }, 3000);
    }
}

// Dashboard Functions
function updateDashboard() {
    // Safely update stats only if elements exist
    const dashboardTotal = document.getElementById('dashboardTotal');
    if (dashboardTotal) {
        dashboardTotal.textContent = currentSession.products.length;
    }

    const dashboardBrands = document.getElementById('dashboardBrands');
    if (dashboardBrands) {
        const brands = [...new Set(currentSession.products.map(p => p.Brand).filter(Boolean))];
        dashboardBrands.textContent = brands.length;
    }

    const dashboardCategories = document.getElementById('dashboardCategories');
    if (dashboardCategories) {
        const categories = [...new Set(currentSession.products.map(p => p.Category).filter(Boolean))];
        dashboardCategories.textContent = categories.length;
    }

    const dashboardSessions = document.getElementById('dashboardSessions');
    if (dashboardSessions) {
        dashboardSessions.textContent = completedSessions.length;
    }

    // Update session summary
    updateSessionSummary();
}

function updateSessionSummary() {
    const summary = document.getElementById('sessionSummary');
    if (!summary) return;

    if (currentSession.products.length === 0) {
        summary.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px;">No contents in current session</p>';
        return;
    }

    // Create summary by brand
    const brandGroups = {};
    currentSession.products.forEach(product => {
        const brand = product.Brand || 'Unknown';
        if (!brandGroups[brand]) {
            brandGroups[brand] = [];
        }
        brandGroups[brand].push(product);
    });

    let html = '<div class="brand-summary">';
    for (const [brand, products] of Object.entries(brandGroups)) {
        html += `
            <div class="brand-group">
                <strong>${brand}</strong>: ${products.length} products
            </div>
        `;
    }
    html += '</div>';
    summary.innerHTML = html;
}

// Smart Features
function initSmartFeatures() {
    // Smart paste with Ctrl+V - only when not in input/textarea/API fields
    document.addEventListener('paste', function(e) {
        const activeElement = document.activeElement;
        const homepageInput = document.getElementById('homepageUrls');
        const scrapeInput = document.getElementById('scrapeUrls');

        // Don't auto-paste if user is in any input field, textarea, or contenteditable
        if (activeElement.tagName === 'INPUT' ||
            activeElement.tagName === 'TEXTAREA' ||
            activeElement.contentEditable === 'true' ||
            activeElement.closest('.settings-content') || // Inside settings
            activeElement.closest('.verification-modal') || // Inside verification modal
            activeElement.closest('.export-section')) { // Inside export section
            return; // Let normal paste behavior happen
        }

        // Only auto-focus if truly not in any input and on main content area
        if (activeElement === document.body || activeElement.tagName === 'DIV') {
            // Detect which section is visible/active
            const settingsOpen = document.querySelector('.settings-content').style.display !== 'none';
            const extractResultsVisible = document.getElementById('extractResults').style.display !== 'none';

            // Don't auto-paste if settings are open
            if (settingsOpen) return;

            if (!extractResultsVisible) {
                // Phase 1: Homepage extraction
                homepageInput.focus();
                if (homepageInput.value && !homepageInput.value.endsWith('\n')) {
                    homepageInput.value += '\n';
                }
            } else {
                // Phase 2: Product scraping
                scrapeInput.focus();
                if (scrapeInput.value && !scrapeInput.value.endsWith('\n')) {
                    scrapeInput.value += '\n';
                }
            }
        }
    });

    // Smart pagination detection
    setupPaginationDetection();
}

function setupPaginationDetection() {
    const homepageInput = document.getElementById('homepageUrls');

    homepageInput.addEventListener('input', function() {
        detectPaginationPattern(this);
    });

    // Tab to accept suggestion
    homepageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Tab' && this.dataset.suggestion) {
            e.preventDefault();
            acceptPaginationSuggestion(this);
        }
    });
}

function detectPaginationPattern(input) {
    const lines = input.value.split('\n').filter(Boolean);
    if (lines.length < 1) return;

    const lastUrl = lines[lines.length - 1];

    // Detect pagination patterns
    const patterns = [
        /\/page\/(\d+)\/?$/i,           // /page/2/
        /[?&]page=(\d+)/i,              // ?page=2
        /\/p\/(\d+)\/?$/i,              // /p/2/
        /[?&]p=(\d+)/i,                 // ?p=2
        /\/(\d+)\/?$/                   // /2/
    ];

    for (const pattern of patterns) {
        const match = lastUrl.match(pattern);
        if (match) {
            const currentPage = parseInt(match[1]);
            const nextPage = currentPage + 1;
            const suggestion = lastUrl.replace(match[0], match[0].replace(currentPage, nextPage));

            // Show suggestion
            showPaginationSuggestion(input, suggestion);
            return;
        }
    }
}

function showPaginationSuggestion(input, suggestion) {
    // Store suggestion
    input.dataset.suggestion = suggestion;

    // Create or update suggestion overlay
    let overlay = document.getElementById('paginationSuggestion');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'paginationSuggestion';
        overlay.className = 'pagination-suggestion';
        input.parentElement.appendChild(overlay);
    }

    overlay.innerHTML = `
        <div class="suggestion-content">
            <span class="suggestion-text">Next: ${suggestion}</span>
            <span class="suggestion-hint">Press TAB to add</span>
        </div>
    `;
    overlay.style.display = 'block';
}

function acceptPaginationSuggestion(input) {
    if (input.dataset.suggestion) {
        input.value += '\n' + input.dataset.suggestion;
        delete input.dataset.suggestion;

        // Hide overlay
        const overlay = document.getElementById('paginationSuggestion');
        if (overlay) {
            overlay.style.display = 'none';
        }

        // Continue detection for next page
        detectPaginationPattern(input);
    }
}

// ============================================
// BATCH PROCESSING FUNCTIONS
// ============================================

function switchTab(tabName) {
    // Hide all tab contents
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Remove active from all tab buttons
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Show selected tab and activate button
    document.getElementById(tabName + 'Tab').classList.add('active');
    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
}

function processBatchEnhancements() {
    const settings = getSettings();
    const batchSKU = document.getElementById('batchGenerateSKU').checked;
    const batchDescription = document.getElementById('batchGenerateDescription').checked;

    if (!batchSKU && !batchDescription) {
        showError('Please select at least one enhancement option', 'No Options Selected');
        return;
    }

    if (batchDescription && !settings.groqKey) {
        showError('Groq API key required for description generation', 'API Key Missing');
        return;
    }

    // Show progress
    document.getElementById('batchProgress').style.display = 'block';
    document.getElementById('batchProcessBtn').disabled = true;

    // Get current session data
    const currentSession = JSON.parse(localStorage.getItem('currentSession') || '{"products": []}');

    if (currentSession.products.length === 0) {
        showError('No products in current session to process', 'No Data');
        document.getElementById('batchProgress').style.display = 'none';
        document.getElementById('batchProcessBtn').disabled = false;
        return;
    }

    processBatchData(currentSession.products, batchSKU, batchDescription, settings);
}

function uploadAndProcess() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.onchange = function(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                try {
                    const csvData = parseCSV(e.target.result);
                    const settings = getSettings();
                    const batchSKU = document.getElementById('batchGenerateSKU').checked;
                    const batchDescription = document.getElementById('batchGenerateDescription').checked;

                    if (!batchSKU && !batchDescription) {
                        showError('Please select at least one enhancement option', 'No Options Selected');
                        return;
                    }

                    document.getElementById('batchProgress').style.display = 'block';
                    document.getElementById('uploadProcessBtn').disabled = true;

                    processBatchData(csvData, batchSKU, batchDescription, settings, true);
                } catch (error) {
                    showError('Failed to parse CSV file: ' + error.message, 'Upload Error');
                }
            };
            reader.readAsText(file);
        }
    };
    input.click();
}

async function processBatchData(products, generateSKU, generateDescription, settings, isUpload = false) {
    try {
        updateBatchProgress('Initializing batch processing...', 0);

        const processedProducts = [];
        let processedCount = 0;
        let skuGenerated = 0;
        let descriptionsGenerated = 0;

        for (let i = 0; i < products.length; i++) {
            const product = { ...products[i] };

            // Update progress
            updateBatchProgress(`Processing product ${i + 1} of ${products.length}...`,
                              ((i + 1) / products.length) * 100);

            // Generate SKU if missing and enabled
            if (generateSKU && (!product.SKU || product.SKU.trim() === '')) {
                product.SKU = generateSKUFromName(product.Name || `PRODUCT${i + 1}`, i + 1);
                skuGenerated++;
            }

            // Generate description if missing and enabled
            if (generateDescription && (!product.Description || product.Description.trim() === '') && settings.groqKey) {
                try {
                    product.Description = await generateProductDescription(product, settings.groqKey);
                    descriptionsGenerated++;
                } catch (error) {
                    console.warn('Failed to generate description for product:', product.Name, error);
                }
            }

            processedProducts.push(product);
            processedCount++;
        }

        // Save processed data
        if (isUpload) {
            // For uploads, trigger download
            downloadCSVFile(processedProducts, 'processed_products.csv');
        } else {
            // Update current session
            const session = JSON.parse(localStorage.getItem('currentSession') || '{}');
            session.products = processedProducts;
            localStorage.setItem('currentSession', JSON.stringify(session));
            updateDashboard();
        }

        // Show completion message
        let message = `Processed ${processedCount} products successfully.`;
        if (skuGenerated > 0) message += ` Generated ${skuGenerated} SKUs.`;
        if (descriptionsGenerated > 0) message += ` Generated ${descriptionsGenerated} descriptions.`;

        showSuccess(message, 'Batch Processing Complete');

    } catch (error) {
        showError('Batch processing failed: ' + error.message, 'Processing Error');
    } finally {
        document.getElementById('batchProgress').style.display = 'none';
        document.getElementById('batchProcessBtn').disabled = false;
        document.getElementById('uploadProcessBtn').disabled = false;
    }
}

function updateBatchProgress(text, percentage) {
    document.getElementById('batchProgressText').textContent = text;
    document.getElementById('batchProgressBar').style.width = percentage + '%';
}

function generateSKUFromName(name, index) {
    if (!name) return `PRD${String(index).padStart(4, '0')}`;

    // Clean name and get prefix
    const cleanName = name.replace(/[^a-zA-Z\s]/g, '');
    const words = cleanName.split(/\s+/).filter(word => word.length > 0);
    let prefix = words.slice(0, 4).map(word => word[0]).join('').toUpperCase();

    if (!prefix) prefix = 'PRD';
    if (prefix.length < 3) prefix = prefix.padEnd(3, 'X');

    return `${prefix}${String(index).padStart(4, '0')}`;
}

async function generateProductDescription(product, groqKey) {
    const payload = {
        name: product.Name || 'Unknown Product',
        price: product.Price || '',
        brand: product.Brand || '',
        category: product.Category || '',
        specifications: product.Specifications || '',
        features: product.Features || ''
    };

    // Call Flask endpoint for description generation
    const response = await fetch('/api/generate-description', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            product_data: payload,
            groq_key: groqKey
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    return result.description || `Professional ${payload.name} offering quality and reliability.`;
}

function parseCSV(csvText) {
    const lines = csvText.split('\n');
    const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''));
    const products = [];

    for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim()) {
            const values = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
            const product = {};
            headers.forEach((header, index) => {
                product[header] = values[index] || '';
            });
            products.push(product);
        }
    }

    return products;
}

function downloadCSVFile(products, filename = 'products.csv') {
    if (products.length === 0) return;

    const headers = Object.keys(products[0]);
    let csv = headers.join(',') + '\n';

    products.forEach(product => {
        const row = headers.map(header => {
            const value = product[header] || '';
            return '"' + String(value).replace(/"/g, '""') + '"';
        });
        csv += row.join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

function getSettings() {
    const saved = localStorage.getItem('appSettings');
    return saved ? JSON.parse(saved) : {};
}

// Enhanced Card-style Toggle Functions
function toggleSKUGeneration() {
    const checkbox = document.getElementById('autoGenerateSKUMain');
    checkbox.checked = !checkbox.checked;
}

async function toggleAIDescriptions() {
    const checkbox = document.getElementById('autoGenerateDescriptionMain');
    const groqKeyInput = document.getElementById('groqKey');
    const groqKeyRequired = document.getElementById('groqKeyRequired');

    // If trying to ENABLE
    if (!checkbox.checked) {
        // Check if Groq key exists
        if (!groqKeyInput || !groqKeyInput.value.trim()) {
            // Show error message
            if (groqKeyRequired) {
                groqKeyRequired.style.display = 'block';
            }

            // Show professional notification
            showError('AI Description Generation requires a valid Groq API key. Please configure your API key in Settings to enable this feature.', 'API Key Required');
            return;
        }

        // Show loading state
        const originalText = 'Validating API key...';
        showInfo(originalText, 'Validating API Key');

        try {
            // Validate the API key
            const response = await fetch('/api/validate-key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: 'groq',
                    key: groqKeyInput.value.trim()
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (!data.valid) {
                // Show error message
                if (groqKeyRequired) {
                    groqKeyRequired.style.display = 'block';
                }
                showError('The provided Groq API key is invalid or has insufficient permissions. Please verify your API key in Settings and ensure it has access to the required models.', 'Invalid API Key');
                return;
            }

            // Hide error message if validation successful
            if (groqKeyRequired) {
                groqKeyRequired.style.display = 'none';
            }

            // Show success message
            showSuccess('AI Description Generation has been enabled successfully. Your product descriptions will now be automatically enhanced using AI.', 'Feature Activated');

        } catch (error) {
            console.error('Error validating API key:', error);

            // Show specific error based on the type
            if (error.message.includes('HTTP 400')) {
                showError('Invalid API request format. Please ensure your Groq API key is properly configured.', 'Configuration Error');
            } else if (error.message.includes('HTTP 401') || error.message.includes('HTTP 403')) {
                showError('Authentication failed. Please verify your Groq API key has the correct permissions.', 'Authentication Error');
            } else if (error.message.includes('HTTP 429')) {
                showError('API rate limit exceeded. Please wait a moment before trying again.', 'Rate Limit Error');
            } else if (error.message.includes('fetch')) {
                showError('Unable to connect to the validation service. Please check your internet connection and try again.', 'Connection Error');
            } else {
                showError('An unexpected error occurred while validating your API key. Please try again or contact support if the issue persists.', 'Validation Error');
            }
            return;
        }
    } else {
        // Hide error message when disabling
        if (groqKeyRequired) {
            groqKeyRequired.style.display = 'none';
        }

        // Show disable confirmation
        showInfo('AI Description Generation has been disabled. Product descriptions will no longer be automatically generated.', 'Feature Disabled');
    }

    // Toggle the checkbox
    checkbox.checked = !checkbox.checked;
}

// Stop functionality
let currentExtractJobId = null;
let currentScrapeJobId = null;

async function stopExtraction() {
    if (!currentExtractJobId) {
        showWarning('No extraction process is currently running', 'Nothing to Stop');
        return;
    }

    try {
        // Call the backend to cancel the job
        const response = await fetch(`${API_URL}/api/cancel-job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: currentExtractJobId })
        });

        if (response.ok) {
            // Reset UI state
            document.getElementById('extractProgress').style.display = 'none';
            document.getElementById('extractBtn').disabled = false;
            document.getElementById('extractBtn').querySelector('.btn-text').textContent = 'Initialize Extraction';
            document.getElementById('extractBtn').querySelector('.btn-spinner').style.display = 'none';
            document.getElementById('extractBtn').style.background = '';

            // Hide stop button
            const stopBtn = document.getElementById('stopExtractBtn');
            if (stopBtn) {
                stopBtn.style.display = 'none';
            }

            // Show any partial results if available
            const result = await response.json();
            if (result.partial_results && result.partial_results.length > 0) {
                document.getElementById('extractResults').style.display = 'block';
                document.getElementById('productUrls').value = result.partial_results.join('\n');
                document.getElementById('urlCount').textContent = `${result.partial_results.length} URLs found`;
                showInfo(`Extraction stopped. Found ${result.partial_results.length} URLs before stopping.`, 'Extraction Stopped');
            } else {
                showInfo('Extraction has been stopped successfully.', 'Extraction Stopped');
            }

            currentExtractJobId = null;
        } else {
            showError('Failed to stop extraction. Please try again.', 'Stop Failed');
        }
    } catch (error) {
        showError('Error stopping extraction: ' + error.message, 'Stop Error');
    }
}

async function stopScraping() {
    if (!currentScrapeJobId) {
        showWarning('No scraping process is currently running', 'Nothing to Stop');
        return;
    }

    try {
        // Call the backend to cancel the job
        const response = await fetch(`${API_URL}/api/cancel-job`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: currentScrapeJobId })
        });

        if (response.ok) {
            // Reset UI state
            document.getElementById('scrapeProgress').style.display = 'none';
            document.getElementById('scrapeBtn').disabled = false;
            document.getElementById('scrapeBtn').querySelector('.btn-text').textContent = 'Execute Scraping';
            document.getElementById('scrapeBtn').querySelector('.btn-spinner').style.display = 'none';
            document.getElementById('scrapeBtn').style.background = '';

            // Show any partial results if available
            const result = await response.json();
            if (result.partial_results && result.partial_results.length > 0) {
                // Display partial results
                currentProducts = result.partial_results;
                displayProducts(currentProducts);
                document.getElementById('scrapeResults').style.display = 'block';
                showInfo(`Scraping stopped. Successfully scraped ${result.partial_results.length} products before stopping.`, 'Scraping Stopped');
            } else {
                showInfo('Scraping has been stopped successfully.', 'Scraping Stopped');
            }

            currentScrapeJobId = null;
        } else {
            showError('Failed to stop scraping. Please try again.', 'Stop Failed');
        }
    } catch (error) {
        showError('Error stopping scraping: ' + error.message, 'Stop Error');
    }
}
