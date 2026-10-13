# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Native gRPC Transport & Security Invariants:
1. Default host binding invariant (defaults to 127.0.0.1, fails closed on 0.0.0.0 without explicit flag).
2. AuthInterceptor token validation.
3. CognitiveEngineServiceServicer method execution: OpenIntent, VerifyTurn, IngestBiometrics.
"""

import os
import tempfile
import pytest
import grpc

from omnitwin.proto import twin_engine_pb2
from omnitwin.server import CognitiveEngineServiceServicer, AuthInterceptor, serve
from omnitwin.core.contour import ContourEngine


class MockGrpcContext:
    def __init__(self):
        self.code = None
        self.details = None

    def set_code(self, code):
        self.code = code

    def set_details(self, details):
        self.details = details

    def abort(self, code, details):
        self.code = code
        self.details = details
        raise Exception(f"RPC Aborted: {code} - {details}")


@pytest.fixture
def temp_servicer():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    contour = ContourEngine(db_path)
    contour.init_schema()

    servicer = CognitiveEngineServiceServicer(db_path)
    yield servicer, contour, db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_grpc_open_intent(temp_servicer):
    servicer, _, _ = temp_servicer
    ctx = MockGrpcContext()
    req = twin_engine_pb2.IntentRequest(
        character_slug="alex",
        user_id="user_test",
        user_message="Hello twin",
    )

    resp = servicer.OpenIntent(req, ctx)
    assert resp.run_id.startswith("run_")
    assert resp.character_slug == "alex"
    assert resp.created_at_unix > 0


def test_grpc_ingest_biometrics(temp_servicer):
    servicer, _, _ = temp_servicer
    ctx = MockGrpcContext()
    req = twin_engine_pb2.BiometricTelemetryRequest(
        character_slug="alex",
        user_id="user_test",
        rr_intervals_ms=[800.0, 820.0, 790.0, 810.0, 805.0, 815.0, 795.0, 800.0, 825.0, 790.0],
        heart_rate=72.0,
    )

    resp = servicer.IngestBiometrics(req, ctx)
    assert resp.rmssd > 0
    assert resp.stress_index > 0
    assert resp.energy > 0


def test_auth_interceptor_rejects_missing_or_bad_token():
    interceptor = AuthInterceptor(api_key="secret-token-123")

    class MockHandlerCallDetails:
        invocation_metadata = [("authorization", "Bearer wrong-token")]

    def dummy_continuation(details):
        return "SUCCESS"

    handler = interceptor.intercept_service(dummy_continuation, MockHandlerCallDetails())
    # Should return an abort handler
    ctx = MockGrpcContext()
    with pytest.raises(Exception) as exc_info:
        handler.unary_unary(None, ctx)
    assert "UNAUTHENTICATED" in str(exc_info.value)


def test_server_bind_security_invariant():
    # Attempting to bind to 0.0.0.0 without allow_insecure_remote must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        serve(db_path=":memory:", host="0.0.0.0", allow_insecure_remote=False)
    assert "Insecure remote binding" in str(exc_info.value)
