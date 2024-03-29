"""
"""
import json

import mock

from ..webapp import heartbeats


class TestHeartbeats:
    """
    ensure existing methods work and break in expected ways
    """

    async def test_heartbeat_invalidbody(self):
        """
        ensure we get a 301 with no allocation_id
        """
        request = {}
        body = {}
        resp = await heartbeats.heartbeat(request, body)
        assert resp.status == 400
        assert json.loads(resp.text) == {
            "status": 400,
            "reason": "'allocation_id' missing from body",
        }

    async def test_heartbeat_happypath(self):
        """
        ensure we get an expected response with valid data
        """
        request = {}
        body = {"allocation_id": "1234"}
        heartbeats.update_expires = mock.AsyncMock(return_value=None)
        resp = await heartbeats.heartbeat(request, body)
        heartbeats.update_expires.assert_called_once()
        assert resp.status == 200
        assert json.loads(resp.text) == {"status": 200}
