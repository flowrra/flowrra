"""Tests for Django UI adapter."""

import pytest
import os

# Check if Django is available
django_available = True
try:
    import django
    from django.conf import settings
    from django.test import RequestFactory, override_settings
    from flowrra.ui.django import DjangoAdapter, get_urls

    # Configure Django settings if not already configured
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            SECRET_KEY='test-secret-key',
            ROOT_URLCONF='',
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
            ],
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [
                    os.path.join(os.path.dirname(__file__), '../src/flowrra/ui/templates'),
                ],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.request',
                    ],
                },
            }],
            MIDDLEWARE=[],
        )
        django.setup()

except ImportError:
    django_available = False

from flowrra import Flowrra, Config, ExecutorConfig

pytestmark = pytest.mark.skipif(
    not django_available,
    reason="Django not installed (pip install flowrra[ui-django])"
)


@pytest.fixture
def app():
    """Create Flowrra app."""
    config = Config(executor=ExecutorConfig(num_workers=2))
    app = Flowrra(config=config)

    @app.task()
    async def test_task(x: int):
        """Test IO-bound task."""
        return x * 2

    @app.task(max_retries=3)
    async def retry_task(n: int):
        """Test task with retries."""
        return n + 1

    return app


@pytest.fixture
async def running_app(app):
    """Create and start Flowrra app."""
    await app.start()
    yield app
    await app.stop()


@pytest.fixture
def request_factory():
    """Create Django request factory."""
    return RequestFactory()


class TestAdapterCreation:
    """Test adapter initialization."""

    def test_adapter_creation(self, app):
        """Test creating Django adapter."""
        adapter = DjangoAdapter(app)
        assert adapter.flowrra is app
        assert adapter.manager is not None

    def test_adapter_has_templates_dir(self, app):
        """Test adapter has templates directory configured."""
        adapter = DjangoAdapter(app)
        assert adapter.templates_dir.exists()

    def test_get_routes_returns_url_patterns(self, app):
        """Test get_routes returns Django URL patterns."""
        adapter = DjangoAdapter(app)
        urlpatterns = adapter.get_routes()
        assert isinstance(urlpatterns, list)
        assert len(urlpatterns) > 0

    def test_get_urls_helper(self, app):
        """Test get_urls convenience function."""
        urlpatterns = get_urls(app)
        assert isinstance(urlpatterns, list)
        assert len(urlpatterns) > 0


class TestURLPatterns:
    """Test URL pattern configuration."""

    def test_url_patterns_count(self, app):
        """Test correct number of URL patterns."""
        adapter = DjangoAdapter(app)
        urlpatterns = adapter.get_routes()
        # Should have HTML pages + API endpoints
        assert len(urlpatterns) >= 10

    def test_url_pattern_names(self, app):
        """Test URL patterns have correct names."""
        adapter = DjangoAdapter(app)
        urlpatterns = adapter.get_routes()

        names = [pattern.name for pattern in urlpatterns if hasattr(pattern, 'name')]
        expected_names = [
            'flowrra_dashboard',
            'flowrra_tasks',
            'flowrra_schedules',
            'flowrra_api_stats',
            'flowrra_api_health',
        ]

        for expected in expected_names:
            assert expected in names, f"URL name '{expected}' not found"


class TestHTMLViews:
    """Test HTML view functions."""

    @pytest.mark.asyncio
    async def test_dashboard_view(self, running_app, request_factory):
        """Test dashboard view renders."""
        from django.urls import resolve

        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        # Find dashboard view
        dashboard_pattern = [p for p in urlpatterns if p.name == 'flowrra_dashboard'][0]
        view_func = dashboard_pattern.callback

        request = request_factory.get('/')
        response = view_func(request)

        assert response.status_code == 200
        assert b'Dashboard' in response.content

    @pytest.mark.asyncio
    async def test_tasks_view(self, running_app, request_factory):
        """Test tasks view renders."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        tasks_pattern = [p for p in urlpatterns if p.name == 'flowrra_tasks'][0]
        view_func = tasks_pattern.callback

        request = request_factory.get('/tasks/')
        response = view_func(request)

        assert response.status_code == 200
        assert b'Tasks' in response.content

    @pytest.mark.asyncio
    async def test_schedules_view(self, running_app, request_factory):
        """Test schedules view renders."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        schedules_pattern = [p for p in urlpatterns if p.name == 'flowrra_schedules'][0]
        view_func = schedules_pattern.callback

        request = request_factory.get('/schedules/')
        response = view_func(request)

        assert response.status_code == 200
        assert b'Schedules' in response.content


class TestAPIViews:
    """Test API view functions."""

    @pytest.mark.asyncio
    async def test_api_stats_view(self, running_app, request_factory):
        """Test API stats view."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        stats_pattern = [p for p in urlpatterns if p.name == 'flowrra_api_stats'][0]
        view_func = stats_pattern.callback

        request = request_factory.get('/api/stats/')
        response = view_func(request)

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'

        import json
        data = json.loads(response.content)
        assert 'app' in data
        assert 'executors' in data
        assert 'tasks' in data

    @pytest.mark.asyncio
    async def test_api_health_view(self, running_app, request_factory):
        """Test API health view."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        health_pattern = [p for p in urlpatterns if p.name == 'flowrra_api_health'][0]
        view_func = health_pattern.callback

        request = request_factory.get('/api/health/')
        response = view_func(request)

        assert response.status_code == 200

        import json
        data = json.loads(response.content)
        assert 'healthy' in data
        assert 'timestamp' in data

    @pytest.mark.asyncio
    async def test_api_list_tasks_view(self, running_app, request_factory):
        """Test API list tasks view."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        tasks_pattern = [p for p in urlpatterns if p.name == 'flowrra_api_tasks_list'][0]
        view_func = tasks_pattern.callback

        request = request_factory.get('/api/tasks/')
        response = view_func(request)

        assert response.status_code == 200

        import json
        data = json.loads(response.content)
        assert isinstance(data, list)
        assert len(data) > 0


class TestStaticFiles:
    """Test static file paths."""

    def test_css_file_exists(self, app):
        """Test CSS file exists."""
        adapter = DjangoAdapter(app)
        css_file = adapter.static_dir / "style.css"
        assert css_file.exists()

    def test_js_file_exists(self, app):
        """Test JavaScript file exists."""
        adapter = DjangoAdapter(app)
        js_file = adapter.static_dir / "app.js"
        assert js_file.exists()

    def test_static_dir_property(self, app):
        """Test static_dir property returns correct path."""
        adapter = DjangoAdapter(app)
        assert adapter.static_dir.exists()
        assert adapter.static_dir.is_dir()


class TestTemplateIntegration:
    """Test template rendering with real data."""

    @pytest.mark.asyncio
    async def test_dashboard_shows_stats(self, running_app, request_factory):
        """Test dashboard displays system stats."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        dashboard_pattern = [p for p in urlpatterns if p.name == 'flowrra_dashboard'][0]
        view_func = dashboard_pattern.callback

        request = request_factory.get('/')
        response = view_func(request)
        content = response.content.decode()

        # Check for key elements
        assert 'Running' in content or 'Stopped' in content
        assert 'IO Executor' in content
        assert 'Registered Tasks' in content

    @pytest.mark.asyncio
    async def test_tasks_page_shows_registered_tasks(self, running_app, request_factory):
        """Test tasks page shows registered tasks."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        tasks_pattern = [p for p in urlpatterns if p.name == 'flowrra_tasks'][0]
        view_func = tasks_pattern.callback

        request = request_factory.get('/tasks/')
        response = view_func(request)
        content = response.content.decode()

        # Should show our test tasks
        assert 'test_task' in content
        assert 'retry_task' in content


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_404_for_invalid_task(self, running_app, request_factory):
        """Test 404 response for non-existent task."""
        from django.http import Http404

        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        task_pattern = [p for p in urlpatterns if p.name == 'flowrra_api_task_detail'][0]
        view_func = task_pattern.callback

        request = request_factory.get('/api/tasks/invalid/')

        with pytest.raises(Http404):
            view_func(request, task_name='invalid_task_name')

    @pytest.mark.asyncio
    async def test_404_for_invalid_schedule(self, running_app, request_factory):
        """Test 404 response for non-existent schedule."""
        from django.http import Http404

        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        schedule_pattern = [p for p in urlpatterns if p.name == 'flowrra_api_schedule_detail'][0]
        view_func = schedule_pattern.callback

        request = request_factory.get('/api/schedules/invalid/')

        with pytest.raises(Http404):
            view_func(request, schedule_id='invalid_schedule_id')


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_ui_workflow(self, running_app, request_factory):
        """Test complete UI workflow."""
        adapter = DjangoAdapter(running_app)
        urlpatterns = adapter.get_routes()

        # Get view functions
        dashboard_view = [p for p in urlpatterns if p.name == 'flowrra_dashboard'][0].callback
        stats_view = [p for p in urlpatterns if p.name == 'flowrra_api_stats'][0].callback
        tasks_view = [p for p in urlpatterns if p.name == 'flowrra_tasks'][0].callback
        health_view = [p for p in urlpatterns if p.name == 'flowrra_api_health'][0].callback

        # 1. Access dashboard
        request = request_factory.get('/')
        response = dashboard_view(request)
        assert response.status_code == 200

        # 2. Check API stats
        request = request_factory.get('/api/stats/')
        response = stats_view(request)
        assert response.status_code == 200

        import json
        stats = json.loads(response.content)
        assert stats['app']['running'] is True

        # 3. View tasks page
        request = request_factory.get('/tasks/')
        response = tasks_view(request)
        assert response.status_code == 200

        # 4. Health check
        request = request_factory.get('/api/health/')
        response = health_view(request)
        assert response.status_code == 200

        health = json.loads(response.content)
        assert health['healthy'] is True

    @pytest.mark.asyncio
    async def test_adapter_with_stopped_app(self, app, request_factory):
        """Test UI works with stopped app."""
        adapter = DjangoAdapter(app)
        urlpatterns = adapter.get_routes()

        # Get view functions
        dashboard_view = [p for p in urlpatterns if p.name == 'flowrra_dashboard'][0].callback
        stats_view = [p for p in urlpatterns if p.name == 'flowrra_api_stats'][0].callback

        # App is not started
        request = request_factory.get('/')
        response = dashboard_view(request)
        assert response.status_code == 200

        # Stats should show app not running
        request = request_factory.get('/api/stats/')
        response = stats_view(request)
        assert response.status_code == 200

        import json
        stats = json.loads(response.content)
        assert stats['app']['running'] is False
