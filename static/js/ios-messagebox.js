// ios-messagebox.js - توابع نمایش پیام شبیه iOS
(function() {
    // ایجاد استایل CSS برای پیام‌ها
    const style = document.createElement('style');
    style.textContent = `
        .ios-messagebox-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            direction: ltr;
        }
        
        .ios-messagebox {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 13px;
            width: 90%;
            max-width: 320px;
            overflow: hidden;
            animation: ios-messagebox-fadein 0.2s ease;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .ios-messagebox-title {
            margin: 0;
            padding: 20px 20px 10px;
            font-size: 17px;
            font-weight: 600;
            text-align: center;
            color: #333;
        }
        
        .ios-messagebox-message {
            padding: 0 20px 20px;
            text-align: center;
            font-size: 14px;
            color: #555;
            line-height: 1.5;
        }
        
        .ios-messagebox-buttons {
            display: flex;
            border-top: 1px solid #E1E1E1;
        }
        
        .ios-messagebox-button {
            flex: 1;
            border: none;
            background: none;
            padding: 13px 0;
            font-size: 16px;
            font-weight: 600;
            color: #007AFF;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .ios-messagebox-button:hover {
            background-color: rgba(0,0,0,0.05);
        }
        
        .ios-messagebox-button:not(:last-child) {
            border-right: 1px solid #E1E1E1;
        }
        
        .ios-messagebox-button-cancel {
            color: #FF3B30;
        }
        
        @keyframes ios-messagebox-fadein {
            from { opacity: 0; transform: scale(1.2); }
            to { opacity: 1; transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
    
    // تابع نمایش پیام
    window.showIOSMessagebox = function(options) {
        const defaults = {
            title: 'Message',
            message: '',
            buttons: [
                {
                    text: 'OK',
                    onClick: () => {}
                }
            ]
        };
        
        const settings = Object.assign({}, defaults, options);
        
        // ایجاد المان‌های پیام
        const overlay = document.createElement('div');
        overlay.className = 'ios-messagebox-overlay';
        
        const messageBox = document.createElement('div');
        messageBox.className = 'ios-messagebox';
        
        const title = document.createElement('h3');
        title.className = 'ios-messagebox-title';
        title.textContent = settings.title;
        
        const message = document.createElement('div');
        message.className = 'ios-messagebox-message';
        message.textContent = settings.message;
        
        const buttons = document.createElement('div');
        buttons.className = 'ios-messagebox-buttons';
        
        // افزودن دکمه‌ها
        settings.buttons.forEach((button, index) => {
            const btn = document.createElement('button');
            btn.className = 'ios-messagebox-button';
            
            if (button.isCancel) {
                btn.classList.add('ios-messagebox-button-cancel');
            }
            
            btn.textContent = button.text;
            btn.addEventListener('click', () => {
                closeMessagebox();
                if (typeof button.onClick === 'function') {
                    button.onClick();
                }
            });
            
            buttons.appendChild(btn);
        });
        
        // ترکیب همه المان‌ها
        messageBox.appendChild(title);
        messageBox.appendChild(message);
        messageBox.appendChild(buttons);
        overlay.appendChild(messageBox);
        document.body.appendChild(overlay);
        
        // تابع بستن پیام
        function closeMessagebox() {
            document.body.removeChild(overlay);
        }
        
        // بستن با کلیک روی overlay (اختیاری)
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeMessagebox();
            }
        });
        
        return {
            close: closeMessagebox
        };
    };
    
    // تابع نمایش پیام موفقیت
    window.showSuccessMessage = function(message, callback) {
        return showIOSMessagebox({
            title: 'Success',
            message: message,
            buttons: [
                {
                    text: 'OK',
                    onClick: callback || function() {}
                }
            ]
        });
    };
    
    // تابع نمایش پیام خطا
    window.showErrorMessage = function(message, callback) {
        return showIOSMessagebox({
            title: 'Error',
            message: message,
            buttons: [
                {
                    text: 'OK',
                    onClick: callback || function() {}
                }
            ]
        });
    };
    
})(); 