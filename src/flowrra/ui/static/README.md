# Flowrra UI Static Files

This directory contains static assets (CSS, JavaScript) for the Flowrra web UI.

## Available Assets

- `style.css` - Main stylesheet with custom design system
- `app.js` - JavaScript for interactive features

## Design

The UI uses:
- Minimal, clean design with custom CSS variables
- No external CSS frameworks (fully self-contained)
- Vanilla JavaScript (no framework dependencies)
- Responsive layout for mobile/desktop
- Auto-refresh capability for live updates
- API helper functions for dynamic interactions

## JavaScript API

The `app.js` file exports `window.FlowrraUI` with the following methods:

- `fetchAPI(endpoint)` - GET request to API
- `postAPI(endpoint, data)` - POST request to API
- `putAPI(endpoint, data)` - PUT request to API
- `deleteAPI(endpoint)` - DELETE request to API
- `formatDatetime(isoString)` - Format datetime for display
- `formatDuration(seconds)` - Format duration in seconds
- `getStatusColor(status)` - Get CSS color class for status
- `showNotification(message, type)` - Show notification
- `copyToClipboard(text)` - Copy text to clipboard
- `enableAutoRefresh()` - Enable auto-refresh
- `disableAutoRefresh()` - Disable auto-refresh
