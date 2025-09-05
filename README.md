# Dalooneh - Restaurant Menu System

[![Django](https://img.shields.io/badge/Django-5.2.1+-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Digital restaurant menu system with QR code ordering and management panel.

## Features

### Customer Side
- QR code scanning for table access
- Digital menu with categories
- Shopping cart with notes
- Customer loyalty discounts
- Real-time order tracking

### Management Panel
- Order management
- Menu item management
- Customer database
- Sales reports
- Staff management

### Technical
- PWA with offline support
- Real-time notifications
- Responsive design
- Multi-language support

## Quick Start

1. **Clone and setup**
   ```bash
   git clone https://github.com/yourusername/dalooneh.git
   cd dalooneh
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure and run**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

3. **Access**
   - Menu: http://localhost:8000/
   - Admin: http://localhost:8000/management/login/

## Project Structure

```
Dalooneh/
├── customers/          # Customer management
├── menu/              # Menu management
├── notifications/     # Real-time notifications
├── orders/           # Order management
├── staff/            # Staff management
├── tables/           # Table management
├── Dalooneh/         # Main settings
├── templates/        # HTML templates
├── static/           # Static files
└── media/            # Uploaded files
```

## Configuration

Copy `env.example` to `.env` and update settings:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Usage

### Customers
1. Scan table QR code
2. Enter phone number
3. Browse menu and add items
4. Place order and track status

### Staff
1. Login to management panel
2. Manage orders and menu
3. View reports and analytics

## PWA Features

- Installable on mobile devices
- Offline menu browsing
- App-like experience
- Fast loading with caching

## Security

- CSRF protection
- Authentication middleware
- Secure file uploads

## Technologies

- Django 5.2.1
- PWA with Service Worker
- SQLite/PostgreSQL
- Django Channels
- Bootstrap 5
- jQuery

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file.

## Support

Create an issue on GitHub for support.

## Deployment

See `DEPLOYMENT.md` for deployment instructions.
