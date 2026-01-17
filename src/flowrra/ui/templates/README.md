# Flowrra UI Templates

This directory contains HTML templates for the Flowrra web UI.

## Directory Structure

```
templates/
├── README.md              # This file
├── base.html             # Flask/Jinja2 base template
├── dashboard.html        # Flask/Jinja2 dashboard
├── tasks.html            # Flask/Jinja2 tasks page
├── schedules.html        # Flask/Jinja2 schedules page
└── django/               # Django-specific templates
    ├── base.html         # Django base template
    ├── dashboard.html    # Django dashboard
    ├── tasks.html        # Django tasks page
    └── schedules.html    # Django schedules page
```

## Why Two Sets of Templates?

Flask/FastAPI and Django use different template engines with incompatible syntax:

**Flask/Jinja2 Syntax**:
```jinja
{{ task.id[:8] }}
{{ task.error[:100] if task.error else 'N/A' }}
```

**Django Template Syntax**:
```django
{{ task.id|slice:":8" }}
{% if task.error %}{{ task.error|slice:":100" }}{% else %}N/A{% endif %}
```

## Template Usage

### Flask/FastAPI
Uses templates from the root directory:
- `base.html`
- `dashboard.html`
- `tasks.html`
- `schedules.html`

### Django
Uses templates from the `django/` subdirectory:
- `django/base.html`
- `django/dashboard.html`
- `django/tasks.html`
- `django/schedules.html`

## Custom Filters

### Flask/FastAPI (Jinja2)
Registered in `flask.py` or `fastapi.py`:
- `format_datetime` - Format datetime objects for display
- `format_duration` - Format duration in seconds to human-readable string
- `status_color` - Get CSS color class for task status

### Django
Passed as context variables in `django.py`:
- `format_datetime` - Format datetime objects for display
- `format_duration` - Format duration in seconds to human-readable string
- `get_status_color` - Get CSS color class for task status
