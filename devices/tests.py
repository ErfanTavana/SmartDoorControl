import json

from django.test import TestCase

from devices import views
from devices.models import Device, DeviceLog
from households.models import Building


class IngestLogTests(TestCase):
    def setUp(self):
        self.building = Building.objects.create(title="Test Building")
        self.device = Device.objects.create(
            building=self.building, api_token="test-device-token"
        )

    def _headers(self):
        return {"HTTP_X_DEVICE_TOKEN": self.device.api_token}

    def test_ingest_log_enriches_metadata(self):
        payload = {"message": "testing serialization", "metadata": "raw"}

        response = self.client.post(
            "/api/device/logs/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._headers(),
        )

        self.assertEqual(response.status_code, 200)
        log = DeviceLog.objects.get(device=self.device)
        self.assertEqual(log.metadata.get("value"), "raw")
        self.assertIn("remote_addr", log.metadata)
        self.assertIn("user_agent", log.metadata)

    def test_sanitize_metadata_handles_non_serializable(self):
        class CustomDetail:
            def __str__(self):
                return "custom-detail"

        raw_metadata = {
            "detail": CustomDetail(),
            "nested": {"items": {1, 2}},
            "list": ("a", "b"),
        }

        sanitized = views._sanitize_metadata(raw_metadata)

        self.assertEqual(sanitized["detail"], "custom-detail")
        self.assertEqual(sanitized["nested"], {"items": [1, 2]})
        self.assertEqual(sanitized["list"], ["a", "b"])
