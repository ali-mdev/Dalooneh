// Cart utility functions
document.addEventListener('DOMContentLoaded', function() {
    console.log('cart.js loaded and ready for use');
    
    // Debug: Check cart counter on page load
    testCartCounter();
    
    // Initialize cart count display when page loads
    updateCartCountDisplay();
    
    // Listen for custom event when cart is updated
    document.addEventListener('cartUpdated', function(event) {
        console.log('cartUpdated event received in cart.js:', event.detail);
        if (event.detail && event.detail.cartCount !== undefined) {
            updateCartCountElement(event.detail.cartCount);
        } else {
            // If no count provided in event, fetch the current count
            fetchCartCount();
        }
    });
    
    // Setup event listeners for add-to-cart buttons
    setupAddToCartListeners();
});

// Test function for cart counter
function testCartCounter() {
    console.log('Testing cart counter...');
    const cartCountElement = document.getElementById('cart-count');
    
    if (!cartCountElement) {
        console.error('Cart count element not found!');
        return;
    }
    
    console.log('Cart count element found:');
    console.log('- Current text:', cartCountElement.textContent);
    console.log('- Element type:', cartCountElement.tagName);
    console.log('- Classes:', cartCountElement.className);
    console.log('- Display state:', cartCountElement.style.display);
    console.log('- Computed display state:', window.getComputedStyle(cartCountElement).display);
    
    // Attempt to manually change display state
    console.log('Attempting to force display of cart counter...');
    cartCountElement.style.display = 'flex';
    cartCountElement.textContent = '99';
    
    // Re-check after change
    setTimeout(() => {
        console.log('Re-checking state after manual change:');
        console.log('- New text:', cartCountElement.textContent);
        console.log('- New display state:', cartCountElement.style.display);
        console.log('- New computed display state:', window.getComputedStyle(cartCountElement).display);
    }, 500);
}

// Update cart count when page loads
function updateCartCountDisplay() {
    console.log('Calling updateCartCountDisplay function');
    fetchCartCount();
}

// Fetch the current cart count from the server
function fetchCartCount() {
    console.log('Calling fetchCartCount function - Requesting cart product count from server');
    
    fetch('/tables/get-cart-count/', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('Response received from server:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Data received from server for cart count:', data);
        updateCartCountElement(data.cart_count);
    })
    .catch(error => {
        console.error('Error fetching cart count:', error);
    });
}

// Update the cart count element in the DOM
function updateCartCountElement(count) {
    console.log('Updating cart count element with value:', count);
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
        console.log('Cart count element found, previous state:', cartCountElement.textContent, cartCountElement.style.display);
        
        // Update the count
        cartCountElement.textContent = count;
        
        // Show/hide based on count
        if (count > 0) {
            cartCountElement.style.display = 'flex';
            console.log('Displaying cart count');
        } else {
            cartCountElement.style.display = 'none';
            console.log('Hiding cart count');
        }
        
        console.log('New cart count state:', cartCountElement.textContent, cartCountElement.style.display);
    } else {
        console.error('Cart count element (cart-count) not found!');
    }
}

// Setup event listeners for add-to-cart buttons
function setupAddToCartListeners() {
    // This is only for add-to-cart forms that may not already have listeners
    const forms = document.querySelectorAll('.add-to-cart-form:not(.has-listeners)');
    console.log(`Setting up ${forms.length} add-to-cart forms`);
    
    forms.forEach(form => {
        form.classList.add('has-listeners');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const productId = this.getAttribute('data-product-id');
            const quantity = document.getElementById('qty-' + productId)?.value || 1;
            const submitBtn = this.querySelector('.add-to-cart-btn');
            
            console.log(`Adding product ${productId} with quantity ${quantity} to cart`);
            
            // Disable the submit button during the request
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = '...';
            }
            
            // Get the CSRF token from the cookie
            const csrftoken = getCookie('csrftoken');
            
            // Prepare form data
            const formData = new FormData();
            formData.append('product_id', productId);
            formData.append('quantity', quantity);
            
            // Make the AJAX request
            fetch('/tables/add-to-cart/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                console.log('Add to cart response:', data);
                if (data.success) {
                    // Dispatch event to update cart count
                    console.log('Dispatching cartUpdated event with value:', data.cart_count);
                    document.dispatchEvent(new CustomEvent('cartUpdated', {
                        detail: { cartCount: data.cart_count }
                    }));
                    
                    // Show success message if showNotification function exists
                    if (typeof showNotification === 'function') {
                        showNotification(
                            'Dalooneh',
                            'Product added to your cart',
                            'success',
                            {
                                url: "/tables/cart/",
                                text: "View Cart"
                            }
                        );
                    }
                } else {
                    // Show error message if showNotification function exists
                    if (typeof showNotification === 'function') {
                        showNotification(
                            'Dalooneh',
                            data.message || 'Sorry, it is not possible to add to cart',
                            'error'
                        );
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (typeof showNotification === 'function') {
                    showNotification(
                        'Dalooneh',
                        'There was an issue connecting to the server. Please try again',
                        'error'
                    );
                }
            })
            .finally(() => {
                // Re-enable the button
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Add to Cart';
                }
            });
        });
    });
}

// Helper function to get cookie
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