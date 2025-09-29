/**
 * IntelliScrape Pro - Marketplace Integration Script
 * Version: 1.0.0
 *
 * Instructions for Marketplace Integration:
 * 1. Replace SCRAPER_URL with your deployed scraper URL
 * 2. Update MARKETPLACE_API with your API endpoint
 * 3. Modify getAuthToken() to match your auth system
 * 4. Add this script to your marketplace pages where scraping is needed
 */

(function() {
    'use strict';

    // ============= CONFIGURATION =============
    const CONFIG = {
        SCRAPER_URL: 'https://intelliscrape-pro.onrender.com/popup',  // Change this to your deployment URL
        MARKETPLACE_API: '/api/products/import',  // Your marketplace import endpoint
        BUTTON_TEXT: '🔍 Scrape Products',
        BUTTON_CLASS: 'btn btn-primary scraper-btn',  // Match your UI framework classes
        POPUP_WIDTH: 900,
        POPUP_HEIGHT: 700
    };

    // ============= POPUP MANAGEMENT =============
    let scraperPopup = null;
    let checkInterval = null;

    function openScraper() {
        // Calculate center position
        const left = (screen.width - CONFIG.POPUP_WIDTH) / 2;
        const top = (screen.height - CONFIG.POPUP_HEIGHT) / 2;

        // Open popup
        scraperPopup = window.open(
            `${CONFIG.SCRAPER_URL}?origin=${encodeURIComponent(window.location.origin)}&marketplace=justsell`,
            'intelliscrape',
            `width=${CONFIG.POPUP_WIDTH},height=${CONFIG.POPUP_HEIGHT},left=${left},top=${top},` +
            'toolbar=no,menubar=no,scrollbars=yes,resizable=yes'
        );

        // Check if popup was blocked
        if (!scraperPopup || scraperPopup.closed || typeof scraperPopup.closed === 'undefined') {
            handlePopupBlocked();
            return;
        }

        // Monitor popup status
        checkInterval = setInterval(() => {
            if (scraperPopup.closed) {
                clearInterval(checkInterval);
                console.log('Scraper popup was closed');
            }
        }, 1000);

        // Show loading indicator
        showNotification('Scraper opened. Please complete the scraping process.', 'info');
    }

    // ============= POPUP BLOCKER HANDLING =============
    function handlePopupBlocked() {
        const fallbackHTML = `
            <div class="popup-blocked-modal" style="
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                z-index: 10000;
                max-width: 400px;
            ">
                <h3>Popup Blocked</h3>
                <p>Your browser blocked the scraper popup. Please choose an option:</p>
                <button onclick="window.open('${CONFIG.SCRAPER_URL}', '_blank')">
                    Open in New Tab
                </button>
                <button onclick="this.parentElement.remove()">
                    Cancel
                </button>
                <p style="margin-top: 10px; font-size: 12px;">
                    To prevent this, allow popups from this site in your browser settings.
                </p>
            </div>
        `;

        const modal = document.createElement('div');
        modal.innerHTML = fallbackHTML;
        document.body.appendChild(modal.firstElementChild);
    }

    // ============= MESSAGE HANDLING =============
    window.addEventListener('message', function(event) {
        // Security: Verify the origin
        const scraperOrigin = new URL(CONFIG.SCRAPER_URL).origin;
        if (event.origin !== scraperOrigin) {
            console.warn('Received message from unknown origin:', event.origin);
            return;
        }

        // Handle different message types
        if (event.data && event.data.type) {
            switch (event.data.type) {
                case 'SCRAPER_DATA':
                    handleScrapedData(event.data.payload);
                    break;
                case 'SCRAPER_PROGRESS':
                    updateProgress(event.data.payload);
                    break;
                case 'SCRAPER_ERROR':
                    handleError(event.data.payload);
                    break;
                case 'SCRAPER_READY':
                    console.log('Scraper is ready');
                    break;
                default:
                    console.log('Unknown message type:', event.data.type);
            }
        }
    });

    // ============= DATA PROCESSING =============
    function handleScrapedData(data) {
        if (data.status === 'complete') {
            // Close popup if still open
            if (scraperPopup && !scraperPopup.closed) {
                scraperPopup.close();
            }

            // Show success notification
            showNotification(`Scraped ${data.products.length} products. Importing...`, 'success');

            // Send to marketplace API
            importProducts(data.products);
        }
    }

    function importProducts(products) {
        fetch(CONFIG.MARKETPLACE_API, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + getAuthToken(),
                'X-CSRF-Token': getCSRFToken()
            },
            body: JSON.stringify({
                products: products,
                source: 'intelliscrape',
                timestamp: new Date().toISOString()
            })
        })
        .then(response => {
            if (!response.ok) throw new Error('Import failed');
            return response.json();
        })
        .then(result => {
            showNotification(
                `Successfully imported ${result.count} products!`,
                'success'
            );

            // Refresh product list if function exists
            if (typeof window.refreshProductList === 'function') {
                window.refreshProductList();
            }

            // Trigger custom event for other components
            window.dispatchEvent(new CustomEvent('products-imported', {
                detail: result
            }));
        })
        .catch(error => {
            console.error('Import failed:', error);
            showNotification(
                'Failed to import products. Please try again.',
                'error'
            );
        });
    }

    // ============= UI UPDATES =============
    function updateProgress(data) {
        // Update progress bar if it exists
        const progressBar = document.querySelector('.scraper-progress');
        if (progressBar) {
            progressBar.style.width = `${data.percentage}%`;
            progressBar.textContent = `${data.current}/${data.total}`;
        }
    }

    function handleError(error) {
        showNotification(
            `Scraping error: ${error.message}`,
            'error'
        );

        if (scraperPopup && !scraperPopup.closed) {
            scraperPopup.close();
        }
    }

    // ============= NOTIFICATIONS =============
    function showNotification(message, type = 'info') {
        // Try to use existing notification system
        if (window.showToast) {
            window.showToast(message, type);
        } else if (window.toastr) {
            window.toastr[type](message);
        } else {
            // Fallback to simple notification
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                background: ${type === 'error' ? '#f44336' : type === 'success' ? '#4CAF50' : '#2196F3'};
                color: white;
                border-radius: 4px;
                z-index: 9999;
                animation: slideIn 0.3s ease;
            `;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    }

    // ============= AUTHENTICATION =============
    function getAuthToken() {
        // Try different methods to get auth token
        return localStorage.getItem('auth_token') ||
               sessionStorage.getItem('auth_token') ||
               document.querySelector('meta[name="auth-token"]')?.content ||
               getCookie('auth_token');
    }

    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content ||
               getCookie('csrf_token');
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }

    // ============= INITIALIZATION =============
    function init() {
        // Create scraper button
        const button = document.createElement('button');
        button.innerText = CONFIG.BUTTON_TEXT;
        button.className = CONFIG.BUTTON_CLASS;
        button.onclick = openScraper;

        // Find best location for button
        const locations = [
            '.product-actions',
            '.toolbar',
            '.page-actions',
            '.content-header',
            '#main-content'
        ];

        let buttonAdded = false;
        for (const selector of locations) {
            const container = document.querySelector(selector);
            if (container) {
                container.appendChild(button);
                buttonAdded = true;
                console.log('Scraper button added to', selector);
                break;
            }
        }

        if (!buttonAdded) {
            console.warn('Could not find suitable location for scraper button');
            // Add floating button as fallback
            button.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
            `;
            document.body.appendChild(button);
        }

        // Add CSS for animations
        if (!document.querySelector('#scraper-styles')) {
            const style = document.createElement('style');
            style.id = 'scraper-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
                .scraper-btn {
                    transition: all 0.3s ease;
                }
                .scraper-btn:hover {
                    transform: scale(1.05);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose functions for manual use
    window.IntelliScrape = {
        open: openScraper,
        importProducts: importProducts,
        config: CONFIG
    };

})();