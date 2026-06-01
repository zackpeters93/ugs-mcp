import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from ugs_mcp.ugs_client import send_gcode, get_status, is_pendant_reachable


@pytest.mark.asyncio
async def test_send_gcode_calls_correct_endpoint():
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("ugs_mcp.ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await send_gcode("G21")

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "sendGcode" in call_args[0][0]
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_send_gcode_returns_error_on_failure():
    with patch("ugs_mcp.ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_class.return_value = mock_client

        result = await send_gcode("G21")

    assert result["status"] == "error"
    assert "message" in result


@pytest.mark.asyncio
async def test_get_status_parses_response():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={
        "machineCoord": {"x": 0.0, "y": 0.0, "z": 0.0},
        "workCoord": {"x": 0.0, "y": 0.0, "z": 0.0},
        "state": "Idle",
        "feedSpeed": 0,
        "spindleSpeed": 0,
    })

    with patch("ugs_mcp.ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await get_status()

    assert result["state"] == "Idle"
    assert "machine_position" in result
    assert "work_position" in result


@pytest.mark.asyncio
async def test_is_pendant_reachable_true():
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("ugs_mcp.ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await is_pendant_reachable()

    assert result is True


@pytest.mark.asyncio
async def test_is_pendant_reachable_false_on_error():
    with patch("ugs_mcp.ugs_client.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_client_class.return_value = mock_client

        result = await is_pendant_reachable()

    assert result is False
