// phone-modal.js - Script to handle the phone modal
document.addEventListener('DOMContentLoaded', function() {
    console.log('Phone modal script loaded');
    
    // Check if the phone modal should be shown (this variable will be set by Django)
    if (typeof showPhoneModal !== 'undefined' && showPhoneModal === true) {
        console.log("Show phone modal flag is true");
        
        // Use setTimeout to ensure all components are loaded
        setTimeout(function() {
            try {
                var phoneModalEl = document.getElementById('phoneNumberModal');
                if (phoneModalEl) {
                    console.log("Modal element found, attempting to open");
                    var phoneModal = new bootstrap.Modal(phoneModalEl, {
                        backdrop: 'static',
                        keyboard: false
                    });
                    phoneModal.show();
                    
                    // Auto focus the input field with a small delay for better UX
                    setTimeout(() => {
                        document.getElementById('phoneNumberInput').focus();
                    }, 500);
                } else {
                    console.error("Phone modal element not found");
                }
            } catch (e) {
                console.error("Error showing modal:", e);
            }
        }, 1000);
    }

    // Manage phone number input for automatic formatting
    var phoneInput = document.getElementById('phoneNumberInput');
    if (phoneInput) {
        phoneInput.addEventListener('input', function(e) {
            // Remove all non-numeric characters
            let value = this.value.replace(/\D/g, '');
            
            // Limit to 15 digits (international standard)
            if (value.length > 15) {
                value = value.slice(0, 15);
            }
            
            // Update field value
            this.value = value;
        });
    }

    // Handle form submission
    var phoneNumberForm = document.getElementById('phoneNumberForm');
    if (phoneNumberForm) {
        phoneNumberForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            var phoneNumberInput = document.getElementById('phoneNumberInput');
            var phoneNumberError = document.getElementById('phoneNumberError');
            var phoneNumber = phoneNumberInput.value.trim();
            var submitButton = document.getElementById('phoneSubmitBtn');
            
            // Validate international phone number (basic validation)
            var phoneRegex = /^\+?[1-9]\d{1,14}$/;
            
            // Simple validation
            if (!phoneNumber) {
                phoneNumberInput.classList.add('is-invalid');
                phoneNumberError.textContent = 'Please enter your phone number';
                animateErrorShake(phoneInput);
                return;
            }
            
            // Validate phone number format
            if (!phoneRegex.test(phoneNumber)) {
                phoneNumberInput.classList.add('is-invalid');
                phoneNumberError.textContent = 'Please enter a valid phone number';
                animateErrorShake(phoneInput);
                return;
            }
            
            // Show loading state
            submitButton.classList.add('loading');
            submitButton.disabled = true;
            phoneNumberInput.classList.remove('is-invalid');
            
            console.log("Sending phone number:", phoneNumber);
            
            // Send form using fetch API
            fetch(submitPhoneUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: new URLSearchParams({
                    'phone_number': phoneNumber
                })
            })
            .then(response => {
                console.log("Response status:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("Server response:", data);
                
                // End loading state
                submitButton.classList.remove('loading');
                submitButton.disabled = false;
                
                if (data.success) {
                    // Add success class to form
                    phoneNumberInput.classList.add('is-valid');
                    
                    // Success animation
                    animateSuccess(phoneNumberForm, function() {
                        // Show success message with a success box similar to iOS
                        if (typeof showSuccessMessage === 'function') {
                            showSuccessMessage(data.message);
                        }
                        
                        // Refresh the page instead of closing the modal
                        setTimeout(function() {
                            window.location.reload();
                        }, 1000);
                    });
                } else {
                    // Show error with animation
                    phoneNumberInput.classList.add('is-invalid');
                    phoneNumberError.textContent = data.message;
                    animateErrorShake(phoneInput);
                    console.error("Error from server:", data.message);
                    
                    // Show error message with a success box similar to iOS
                    if (typeof showErrorMessage === 'function') {
                        showErrorMessage(data.message);
                    }
                }
            })
            .catch(error => {
                console.error('Error in fetch request:', error);
                
                // End loading state
                submitButton.classList.remove('loading');
                submitButton.disabled = false;
                
                phoneNumberInput.classList.add('is-invalid');
                phoneNumberError.textContent = 'Error sending request';
                animateErrorShake(phoneInput);
                
                // Show error message with a success box similar to iOS
                if (typeof showErrorMessage === 'function') {
                    showErrorMessage('There was an issue connecting to the server. Please try again');
                }
            });
        });
    } else {
        console.log("Phone form element not found");
    }
    
    // Error shake animation
    function animateErrorShake(element) {
        element.classList.add('shake');
        setTimeout(() => {
            element.classList.remove('shake');
        }, 600);
    }
    
    // Success animation
    function animateSuccess(formElement, callback) {
        var successOverlay = document.createElement('div');
        successOverlay.className = 'success-animation-overlay';
        successOverlay.innerHTML = '<div class="success-checkmark"><div class="check-icon"><span class="icon-line line-tip"></span><span class="icon-line line-long"></span><div class="icon-circle"></div><div class="icon-fix"></div></div></div>';
        
        formElement.appendChild(successOverlay);
        
        setTimeout(() => {
            if (callback && typeof callback === 'function') {
                callback();
            }
            
            // Remove animation element after callback
            setTimeout(() => {
                if (formElement.contains(successOverlay)) {
                    formElement.removeChild(successOverlay);
                }
            }, 300);
        }, 1200);
    }
});

// Add styles to the page
(function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
            20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        
        .shake {
            animation: shake 0.6s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
        }
        
        .success-animation-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.9);
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
        }
        
        .success-checkmark {
            width: 80px;
            height: 80px;
            margin: 0 auto;
        }
        
        .check-icon {
            width: 80px;
            height: 80px;
            position: relative;
            border-radius: 50%;
            box-sizing: content-box;
            border: 4px solid #4CAF50;
        }
        
        .check-icon::before {
            top: 3px;
            left: -2px;
            width: 30px;
            transform-origin: 100% 50%;
            border-radius: 100px 0 0 100px;
        }
        
        .check-icon::after {
            top: 0;
            left: 30px;
            width: 60px;
            transform-origin: 0 50%;
            border-radius: 0 100px 100px 0;
            animation: rotate-circle 4.25s ease-in;
        }
        
        .check-icon::before, .check-icon::after {
            content: '';
            height: 100px;
            position: absolute;
            background: #FFFFFF;
            transform: rotate(-45deg);
        }
        
        .check-icon .icon-line {
            height: 5px;
            background-color: #4CAF50;
            display: block;
            border-radius: 2px;
            position: absolute;
            z-index: 10;
        }
        
        .check-icon .icon-line.line-tip {
            top: 46px;
            left: 14px;
            width: 25px;
            transform: rotate(45deg);
            animation: icon-line-tip 0.75s;
        }
        
        .check-icon .icon-line.line-long {
            top: 38px;
            right: 8px;
            width: 47px;
            transform: rotate(-45deg);
            animation: icon-line-long 0.75s;
        }
        
        .check-icon .icon-circle {
            top: -4px;
            left: -4px;
            z-index: 10;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            position: absolute;
            box-sizing: content-box;
            border: 4px solid rgba(76, 175, 80, 0.3);
        }
        
        .check-icon .icon-fix {
            top: 8px;
            width: 5px;
            left: 26px;
            z-index: 1;
            height: 85px;
            position: absolute;
            transform: rotate(-45deg);
            background-color: #FFFFFF;
        }
        
        @keyframes rotate-circle {
            0% { transform: rotate(-45deg); }
            5% { transform: rotate(-45deg); }
            12% { transform: rotate(-405deg); }
            100% { transform: rotate(-405deg); }
        }
        
        @keyframes icon-line-tip {
            0% { width: 0; left: 1px; top: 19px; }
            54% { width: 0; left: 1px; top: 19px; }
            70% { width: 50px; left: -8px; top: 37px; }
            84% { width: 17px; left: 21px; top: 48px; }
            100% { width: 25px; left: 14px; top: 45px; }
        }
        
        @keyframes icon-line-long {
            0% { width: 0; right: 46px; top: 54px; }
            65% { width: 0; right: 46px; top: 54px; }
            84% { width: 55px; right: 0px; top: 35px; }
            100% { width: 47px; right: 8px; top: 38px; }
        }
    `;
    document.head.appendChild(style);
})();

// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
} 