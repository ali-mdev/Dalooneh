# Project Structure Documentation

This document provides a detailed overview of the Dalooneh project structure and architecture.

## Directory Structure

```
Dalooneh/
├── customers/                 # Customer management app
│   ├── __init__.py
│   ├── admin.py              # Django admin configuration
│   ├── apps.py               # App configuration
│   ├── forms.py              # Customer forms
│   ├── migrations/           # Database migrations
│   ├── models.py             # Customer models
│   ├── templatetags/         # Custom template tags
│   ├── tests.py              # Unit tests
│   ├── urls.py               # URL routing
│   └── views.py              # Customer views
│
├── menu/                     # Menu management app
│   ├── __init__.py
│   ├── admin.py              # Menu admin
│   ├── apps.py               # App configuration
│   ├── forms.py              # Menu forms
│   ├── management/           # Custom management commands
│   ├── migrations/           # Database migrations
│   ├── models.py             # Menu models (Category, Product)
│   ├── templates/            # Menu templates
│   ├── templatetags/         # Custom template tags
│   ├── tests.py              # Unit tests
│   ├── urls.py               # URL routing
│   └── views.py              # Menu views
│
├── notifications/            # Real-time notifications app
│   ├── __init__.py
│   ├── apps.py               # App configuration
│   ├── consumers.py          # WebSocket consumers
│   ├── migrations/           # Database migrations
│   ├── models.py             # Notification models
│   ├── routing.py            # WebSocket routing
│   ├── signals.py            # Django signals
│   ├── templates/            # Notification templates
│   ├── tests.py              # Unit tests
│   ├── urls.py               # URL routing
│   └── views.py              # Notification views
│
├── orders/                   # Order management app
│   ├── __init__.py
│   ├── admin.py              # Order admin
│   ├── apps.py               # App configuration
│   ├── migrations/           # Database migrations
│   ├── models.py             # Order models
│   ├── tests.py              # Unit tests
│   ├── urls.py               # URL routing
│   └── views.py              # Order views
│
├── staff/                    # Staff management app
│   ├── __init__.py
│   ├── admin.py              # Staff admin
│   ├── apps.py               # App configuration
│   ├── management/           # Custom management commands
│   ├── migrations/           # Database migrations
│   ├── models.py             # Staff models
│   ├── tests.py              # Unit tests
│   ├── urls.py               # URL routing
│   └── views.py              # Staff views
│
├── tables/                   # Table management app
│   ├── __init__.py
│   ├── admin.py              # Table admin
│   ├── apps.py               # App configuration
│   ├── forms.py              # Table forms
│   ├── management/           # Custom management commands
│   ├── middleware.py         # Custom middleware
│   ├── migrations/           # Database migrations
│   ├── models.py             # Table models
│   ├── templates/            # Table templates
│   ├── templatetags/         # Custom template tags
│   ├── tests.py              # Unit tests
│   ├── urls.py               # URL routing
│   └── views.py              # Table views
│
├── Dalooneh/                 # Main Django project
│   ├── __init__.py
│   ├── asgi.py               # ASGI configuration
│   ├── decorators.py         # Custom decorators
│   ├── middleware.py         # Custom middleware
│   ├── settings.py           # Django settings
│   ├── settings_sqlite.py    # SQLite-specific settings
│   ├── urls.py               # Main URL configuration
│   ├── views.py              # Main views
│   └── wsgi.py               # WSGI configuration
│
├── templates/                # Global templates
│   ├── base.html             # Base template
│   ├── index.html            # Home page
│   ├── customers/            # Customer templates
│   ├── menu/                 # Menu templates
│   ├── orders/               # Order templates
│   ├── staff/                # Staff templates
│   └── tables/               # Table templates
│
├── static/                   # Static files
│   ├── css/                  # Stylesheets
│   ├── js/                   # JavaScript files
│   │   ├── sw.js             # Service Worker for PWA
│   │   └── pwa-install.js    # PWA installation script
│   ├── images/               # Images and icons
│   │   └── icons/            # PWA app icons
│   ├── fonts/                # Font files
│   ├── sounds/               # Audio files
│   └── manifest.json         # PWA manifest file
│
├── media/                    # User uploaded files
│   ├── categories/           # Category images
│   ├── products/             # Product images
│   └── qrcodes/              # Generated QR codes
│
├── logs/                     # Application logs
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # SQLite database (not in git)
└── README.md                # Project documentation
```

## App Responsibilities

### customers/
- Customer registration and management
- Loyalty program and discounts
- Customer history tracking
- Phone number validation

### menu/
- Menu categories and items
- Product management with images
- Inventory tracking
- Price management

### notifications/
- Real-time WebSocket notifications
- Order status updates
- System notifications
- Notification templates

### orders/
- Order processing and management
- Order status tracking
- Payment processing
- Sales analytics

### staff/
- Staff user management
- Role-based access control
- Staff activity tracking
- Authentication and authorization

### tables/
- Table management
- QR code generation
- Session management
- Cart functionality

## Key Models

### Customer Models
- `Customer`: Customer information and loyalty data
- `CustomerDiscount`: Loyalty discount tracking

### Menu Models
- `Category`: Menu categories
- `Product`: Menu items with images and details
- `Inventory`: Stock management

### Order Models
- `Order`: Order information
- `OrderItem`: Individual items in orders
- `Payment`: Payment records

### Table Models
- `Table`: Table information and QR codes
- `Session`: Active customer sessions

## Middleware

- `TableAuthMiddleware`: Table session authentication
- `ManagementAccessMiddleware`: Management panel access control

## Custom Management Commands

- `create_staff_user`: Create staff users
- `fix_empty_slugs`: Fix empty slugs in menu items
- `cleanup_carts`: Clean up expired cart sessions

## Template Tags

- `customer_tags`: Customer-related template tags
- `custom_price`: Price formatting
- `price_format`: Price display formatting
- `custom_filters`: Custom template filters
- `price_filters`: Price-related filters

## Security Features

- CSRF protection
- Authentication middleware
- Role-based access control
- Secure file uploads
- Environment-based configuration

## PWA Features

- Progressive Web App with offline capabilities
- Service Worker for caching and offline functionality
- Web App Manifest for app-like experience
- Installable on any device
- Push notifications support

## Real-time Features

- WebSocket support via Django Channels
- Real-time order notifications
- Live order status updates
- Instant cart updates

This structure follows Django best practices and provides a clean separation of concerns for each app.
