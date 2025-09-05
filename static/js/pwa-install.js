// PWA Installation and Service Worker Registration
class PWAInstaller {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.init();
    }

    init() {
        // Register service worker
        this.registerServiceWorker();
        
        // Handle install prompt
        this.handleInstallPrompt();
        
        // Check if already installed
        this.checkInstallStatus();
        
        // Add install button if needed
        this.addInstallButton();
    }

    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/js/sw.js', {
                    scope: '/'
                });
                
                console.log('PWA: Service Worker registered successfully:', registration);
                
                // Handle updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            this.showUpdateNotification();
                        }
                    });
                });
                
            } catch (error) {
                console.error('PWA: Service Worker registration failed:', error);
            }
        } else {
            console.log('PWA: Service Worker not supported');
        }
    }

    handleInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            console.log('PWA: Install prompt triggered');
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });

        window.addEventListener('appinstalled', () => {
            console.log('PWA: App installed successfully');
            this.isInstalled = true;
            this.hideInstallButton();
            this.showInstalledMessage();
        });
    }

    checkInstallStatus() {
        // Check if running in standalone mode (installed)
        if (window.matchMedia('(display-mode: standalone)').matches || 
            window.navigator.standalone === true) {
            this.isInstalled = true;
            console.log('PWA: App is running in standalone mode');
        }
    }

    addInstallButton() {
        // Create install button if it doesn't exist
        if (!document.getElementById('pwa-install-btn') && !this.isInstalled) {
            const installBtn = document.createElement('button');
            installBtn.id = 'pwa-install-btn';
            installBtn.className = 'btn btn-primary pwa-install-button';
            installBtn.innerHTML = `
                <i class="bi bi-download me-2"></i>
                Install App
            `;
            installBtn.style.cssText = `
                position: fixed;
                bottom: 80px;
                right: 20px;
                z-index: 1000;
                border-radius: 25px;
                padding: 12px 20px;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba(3, 63, 56, 0.3);
                background: linear-gradient(135deg, #033F38, #065951);
                border: none;
                color: white;
                display: none;
                animation: slideInUp 0.5s ease;
            `;
            
            installBtn.addEventListener('click', () => this.installApp());
            document.body.appendChild(installBtn);
        }
    }

    showInstallButton() {
        const installBtn = document.getElementById('pwa-install-btn');
        if (installBtn && !this.isInstalled) {
            installBtn.style.display = 'block';
        }
    }

    hideInstallButton() {
        const installBtn = document.getElementById('pwa-install-btn');
        if (installBtn) {
            installBtn.style.display = 'none';
        }
    }

    async installApp() {
        if (!this.deferredPrompt) {
            console.log('PWA: No install prompt available');
            return;
        }

        try {
            this.deferredPrompt.prompt();
            const { outcome } = await this.deferredPrompt.userChoice;
            
            if (outcome === 'accepted') {
                console.log('PWA: User accepted the install prompt');
            } else {
                console.log('PWA: User dismissed the install prompt');
            }
            
            this.deferredPrompt = null;
            this.hideInstallButton();
            
        } catch (error) {
            console.error('PWA: Error during installation:', error);
        }
    }

    showUpdateNotification() {
        // Show update notification using your existing notification system
        if (typeof showIOSMessage === 'function') {
            showIOSMessage('Update available', 'To get the latest features, please reload the page.', 'info', [
                {
                    text: 'Reload',
                    style: 'primary',
                    handler: () => window.location.reload()
                },
                {
                    text: 'Later',
                    style: 'secondary'
                }
            ]);
        } else {
            // Fallback notification
            if (confirm('A new version is available. Would you like to reload the page?')) {
                window.location.reload();
            }
        }
    }

    showInstalledMessage() {
        if (typeof showIOSMessage === 'function') {
            showIOSMessage('Installed!', 'The Dalooneh app was installed successfully.', 'success');
        }
    }

    // Request notification permission
    async requestNotificationPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            console.log('PWA: Notification permission:', permission);
            return permission === 'granted';
        }
        return false;
    }

    // Subscribe to push notifications
    async subscribeToPushNotifications() {
        if ('serviceWorker' in navigator && 'PushManager' in window) {
            try {
                const registration = await navigator.serviceWorker.ready;
                const subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: this.urlBase64ToUint8Array('YOUR_VAPID_PUBLIC_KEY') // Replace with your VAPID key
                });
                
                console.log('PWA: Push subscription:', subscription);
                // Send subscription to your server
                await this.sendSubscriptionToServer(subscription);
                
            } catch (error) {
                console.error('PWA: Error subscribing to push notifications:', error);
            }
        }
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push-subscription/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(subscription)
            });
            
            if (response.ok) {
                console.log('PWA: Subscription sent to server successfully');
            }
        } catch (error) {
            console.error('PWA: Error sending subscription to server:', error);
        }
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
}

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInUp {
        from {
            transform: translateY(100px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    .pwa-install-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(3, 63, 56, 0.4) !important;
    }
    
    .pwa-install-button:active {
        transform: translateY(0);
    }
`;
document.head.appendChild(style);

// Initialize PWA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const pwaInstaller = new PWAInstaller();
    
    // Make it globally accessible
    window.pwaInstaller = pwaInstaller;
    
    // Request notification permission after a delay
    setTimeout(() => {
        pwaInstaller.requestNotificationPermission();
    }, 3000);
});

// Handle online/offline status
window.addEventListener('online', () => {
    console.log('PWA: Back online');
    if (typeof showIOSMessage === 'function') {
        showIOSMessage('Connection Restored', 'You are back online!', 'success');
    }
});

window.addEventListener('offline', () => {
    console.log('PWA: Gone offline');
    if (typeof showIOSMessage === 'function') {
        showIOSMessage('Connection Lost', 'You are offline. Some features may be limited.', 'warning');
    }
}); 