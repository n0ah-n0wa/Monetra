"""Access log middleware tests."""

import logging

from app.main import create_app
from httpx import ASGITransport, AsyncClient


async def test_access_log_emits_structured_event(app_settings, caplog) -> None:
    settings = app_settings.model_copy(update={"access_log_skip_paths": []})
    application = create_app(settings=settings)

    with caplog.at_level(logging.INFO):
        transport = ASGITransport(app=application)
        async with (
            AsyncClient(transport=transport, base_url="http://test") as client,
            application.router.lifespan_context(application),
        ):
            logging.getLogger().addHandler(caplog.handler)
            response = await client.get(
                "/health",
                headers={"X-Request-ID": "access-1"},
            )

    assert response.status_code == 200
    access_records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "http.request.completed"
    ]
    assert access_records
    record = access_records[-1]
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0


async def test_access_log_skips_configured_paths(app_settings, caplog) -> None:
    settings = app_settings.model_copy(update={"access_log_skip_paths": ["/health"]})
    application = create_app(settings=settings)

    with caplog.at_level(logging.INFO):
        transport = ASGITransport(app=application)
        async with (
            AsyncClient(transport=transport, base_url="http://test") as client,
            application.router.lifespan_context(application),
        ):
            logging.getLogger().addHandler(caplog.handler)
            await client.get("/health")

    access_records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "http.request.completed"
    ]
    assert access_records == []
