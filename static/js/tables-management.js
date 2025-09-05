/**
 * Tables Management JS
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Flatpickr for date pickers
    try {
        flatpickr('.date-picker', {
            dateFormat: 'Y-m-d',
            locale: 'en',
            position: 'auto right'
        });
    } catch (e) {
        console.warn('Flatpickr not loaded:', e);
    }
    
    // QR Code generation for a single table
    const generateQrButtons = document.querySelectorAll('.generate-qr-button');
    if (generateQrButtons.length > 0) {
        generateQrButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const tableId = this.getAttribute('data-table-id');
                if (!tableId) {
                    alert('Table ID is invalid.');
                    return;
                }
                
                // Show loading state
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
                this.disabled = true;
                
                // Redirect to QR generation URL
                window.location.href = `/tables/management/generate-qr/?table_id=${tableId}`;
            });
        });
    }
    
    // Generate all QR codes button
    const generateAllQrButton = document.getElementById('generate-all-qr');
    if (generateAllQrButton) {
        generateAllQrButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            if (!confirm('Are you sure you want to generate QR codes for all active tables?')) {
                return;
            }
            
            // Show loading state
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            this.disabled = true;
            
            // Redirect to generate all QR codes URL
            window.location.href = '/tables/management/generate-all-qr/';
        });
    }
    
    // Print QR code button
    const printQrButtons = document.querySelectorAll('.print-qr-button');
    if (printQrButtons.length > 0) {
        printQrButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const imgSrc = this.getAttribute('data-qr-src');
                if (!imgSrc) {
                    alert('You must generate a QR code first.');
                    return;
                }
                
                // Create print window
                const printWindow = window.open('', '_blank');
                const tableNumber = this.getAttribute('data-table-number');
                
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Print Table ${tableNumber} QR Code</title>
                        <style>
                            body {
                                font-family: 'Vazirmatn', sans-serif;
                                text-align: center;
                                padding: 20px;
                            }
                            .qr-container {
                                margin: 0 auto;
                                max-width: 400px;
                            }
                            .qr-image {
                                width: 100%;
                                max-width: 300px;
                                height: auto;
                            }
                            .qr-title {
                                font-size: 24px;
                                margin-bottom: 20px;
                            }
                            .qr-table-number {
                                font-size: 36px;
                                font-weight: bold;
                                margin: 20px 0;
                            }
                            .qr-instructions {
                                margin-top: 20px;
                                font-size: 14px;
                                color: #666;
                            }
                            @media print {
                                .no-print {
                                    display: none;
                                }
                            }
                        </style>
                    </head>
                    <body>
                        <div class="qr-container">
                            <div class="qr-title">Scan to View</div>
                            <div class="qr-table-number">Table ${tableNumber}</div>
                            <img src="${imgSrc}" alt="QR Code for Table ${tableNumber}" class="qr-image">
                            <div class="qr-instructions">
                                Scan the QR code to view the menu and place an order
                            </div>
                            <button class="no-print" style="margin-top: 30px; padding: 10px 20px;" onclick="window.print()">Print</button>
                        </div>
                        <script>
                            // Auto print
                            window.onload = function() {
                                setTimeout(function() {
                                    window.print();
                                }, 500);
                            };
                        </script>
                    </body>
                    </html>
                `);
                
                printWindow.document.close();
            });
        });
    }
    
    // Toggle table status
    const toggleStatusButtons = document.querySelectorAll('.toggle-table-status');
    if (toggleStatusButtons.length > 0) {
        toggleStatusButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const tableId = this.getAttribute('data-table-id');
                if (!tableId) {
                    alert('Table ID is invalid.');
                    return;
                }
                
                const isActive = this.getAttribute('data-is-active') === 'true';
                const statusText = isActive ? 'Deactivate' : 'Activate';
                
                if (!confirm(`Are you sure you want to ${statusText} table ${tableNumber}?`)) {
                    return;
                }
                
                // Redirect to toggle status URL
                window.location.href = `/tables/management/tables/${tableId}/toggle-status/`;
            });
        });
    }
    
    // Free table buttons
    const freeTableButtons = document.querySelectorAll('.free-table-button');
    if (freeTableButtons.length > 0) {
        freeTableButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const tableId = this.getAttribute('data-table-id');
                if (!tableId) {
                    alert('Table ID is invalid.');
                    return;
                }
                
                if (!confirm('Are you sure you want to free this table? This will deactivate active sessions.')) {
                    return;
                }
                
                // Redirect to free table URL
                window.location.href = `/tables/management/tables/${tableId}/free/`;
            });
        });
    }
    
    // Deactivate session buttons
    const deactivateSessionButtons = document.querySelectorAll('.deactivate-session');
    if (deactivateSessionButtons.length > 0) {
        deactivateSessionButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const sessionId = this.getAttribute('data-id');
                if (!sessionId) {
                    alert('Session ID is invalid.');
                    return;
                }
                
                if (!confirm('Are you sure you want to deactivate this session?')) {
                    return;
                }
                
                // Get the return URL
                const tableId = this.getAttribute('data-table-id');
                let returnUrl = '';
                
                if (tableId) {
                    returnUrl = `?session_id=${sessionId}&return_to=detail&table_id=${tableId}`;
                } else {
                    returnUrl = `?session_id=${sessionId}&return_to=detail`;
                }
                
                // Redirect to deactivate session URL
                window.location.href = `/tables/management/sessions/deactivate/${returnUrl}`;
            });
        });
    }
}); 