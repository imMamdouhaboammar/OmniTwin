# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import sys
import time
from typing import Optional

import grpc
from omnitwin.proto import twin_engine_pb2, twin_engine_pb2_grpc
from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner
from omnitwin.core.generator import CognitiveGenerator
from omnitwin.core.biometrics import BiometricProcessor
from omnitwin.adapters.llm_provider import (
    BaseLLMProvider,
    get_default_provider,
    PiGatewayProvider,
    OpenRouterProvider,
    GoogleVertexGeminiProvider,
    OfflineSimulatorProvider,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OmniTwin.gRPCServer")


class AuthInterceptor(grpc.ServerInterceptor):
    """Optional bearer token authentication interceptor."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def intercept_service(self, continuation, handler_call_details):
        if not self.api_key:
            return continuation(handler_call_details)

        metadata = dict(handler_call_details.invocation_metadata)
        token = metadata.get("authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]

        if token != self.api_key:
            def abort(request, context):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid or missing API key")
            return grpc.unary_unary_rpc_method_handler(abort)

        return continuation(handler_call_details)


class CognitiveEngineServiceServicer(twin_engine_pb2_grpc.CognitiveEngineServiceServicer):
    """
    gRPC Server implementing the native east-west CognitiveEngineService.
    Serves Intent Opening, Delivery Slicing, Turn Verification, and State Reductions.
    """

    def __init__(self, db_path: str, provider: Optional[BaseLLMProvider] = None):
        self.db_path = db_path
        self.contour = ContourEngine(db_path)
        self.reducer = StateReducer(db_path)
        self.planner = TurnPlanner(self.contour, self.reducer)
        self.bio_processor = BiometricProcessor()
        self.provider = provider if provider is not None else get_default_provider()

    def OpenIntent(self, request, context):
        try:
            pid = request.character_slug or "default"
            run_id = self.contour.open_intent(
                persona_id=pid,
                user_id=request.user_id,
                user_message=request.user_message,
            )
            return twin_engine_pb2.IntentResponse(
                run_id=run_id,
                character_slug=pid,
                created_at_unix=int(time.time()),
            )
        except Exception as e:
            logger.error(f"OpenIntent error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.IntentResponse()

    def CompileDelivery(self, request, context):
        try:
            pid = request.character_slug or "default"
            plan = self.planner.plan_turn(
                persona_id=pid,
                user_id=request.user_id,
                user_message=request.user_message,
            )
            raw_eps = plan.get("delivery", {}).get("delivered_eps", []) or plan.get("delivery", {}).get("extract_points", [])
            proto_eps = []
            for ep in raw_eps:
                proto_eps.append(
                    twin_engine_pb2.ExtractPoint(
                        id=ep.get("id", ""),
                        meta_id=ep.get("meta_id", ""),
                        group=ep.get("grp", ep.get("group", "")),
                        vector=ep.get("vector", ""),
                        text=ep.get("text", ""),
                        confidence_score=float(ep.get("confidence", 0.0)),
                    )
                )

            return twin_engine_pb2.DeliverySlice(
                run_id=plan.get("run_id", ""),
                extract_points=proto_eps,
                chosen_social_move=twin_engine_pb2.SocialMove.SOCIAL_MOVE_ANSWER,
                state_summary=json.dumps(plan.get("current_state", {})),
            )
        except Exception as e:
            logger.error(f"CompileDelivery error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.DeliverySlice()

    def VerifyTurn(self, request, context):
        try:
            cited_ids = list(request.cited_ep_ids)
            ok, missing, reason = self.contour.verify_turn(
                run_id=request.run_id,
                cited_ep_ids=cited_ids,
                raw_response=request.proposed_answer,
                check_semantic_grounding=True,
            )
            return twin_engine_pb2.TurnVerificationResponse(
                is_accepted=ok,
                missing_ep_ids=missing,
                rejection_reason=reason,
            )
        except Exception as e:
            logger.error(f"VerifyTurn error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.TurnVerificationResponse(
                is_accepted=False,
                rejection_reason=f"INTERNAL_ERROR: {e}",
            )

    def ReduceState(self, request, context):
        try:
            pid = request.character_slug or "default"
            prop = {
                "mood": request.proposal.mood or "neutral",
                "energy_delta": request.proposal.energy_delta,
                "add_concern": request.proposal.add_concern,
                "resolve_concern": request.proposal.resolve_concern,
                "add_thread": request.proposal.add_thread,
                "confidence": request.proposal.confidence or 0.8,
            }
            res = self.reducer.reduce_proposal(
                persona_id=pid,
                user_id=request.user_id,
                proposal=prop,
            )
            return twin_engine_pb2.DynamicStateSnapshot(
                mood=res.get("mood", "neutral"),
                energy=float(res.get("energy", 0.7)),
                conversation_appetite=res.get("conversation_appetite", "medium"),
                current_mode=res.get("current_mode", "casual"),
                active_concerns=[c.get("topic", str(c)) if isinstance(c, dict) else str(c) for c in res.get("active_concerns", [])],
                active_threads=res.get("active_threads", []),
            )
        except Exception as e:
            logger.error(f"ReduceState error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.DynamicStateSnapshot()

    def PlanTurn(self, request, context):
        try:
            pid = request.character_slug or "default"
            plan = self.planner.plan_turn(
                persona_id=pid,
                user_id=request.user_id,
                user_message=request.user_message,
            )
            raw_eps = plan.get("delivery", {}).get("delivered_eps", []) or plan.get("delivery", {}).get("extract_points", [])
            proto_eps = []
            for ep in raw_eps:
                proto_eps.append(
                    twin_engine_pb2.ExtractPoint(
                        id=ep.get("id", ""),
                        meta_id=ep.get("meta_id", ""),
                        group=ep.get("grp", ep.get("group", "")),
                        vector=ep.get("vector", ""),
                        text=ep.get("text", ""),
                        confidence_score=float(ep.get("confidence", 0.0)),
                    )
                )

            st = plan.get("current_state", {})
            concerns = [
                c.get("topic", str(c)) if isinstance(c, dict) else str(c)
                for c in st.get("active_concerns", [])
            ]
            threads = [
                t.get("thread", str(t)) if isinstance(t, dict) else str(t)
                for t in st.get("active_threads", [])
            ]
            st_proto = twin_engine_pb2.DynamicStateSnapshot(
                mood=st.get("mood", "neutral"),
                energy=float(st.get("energy", 0.7)),
                conversation_appetite=st.get("conversation_appetite", "medium"),
                current_mode=st.get("current_mode", "casual"),
                active_concerns=concerns,
                active_threads=threads,
            )

            deliv_slice = twin_engine_pb2.DeliverySlice(
                run_id=plan.get("run_id", ""),
                extract_points=proto_eps,
                chosen_social_move=twin_engine_pb2.SocialMove.SOCIAL_MOVE_ANSWER,
                state_summary=json.dumps(st),
            )

            return twin_engine_pb2.PlanTurnResponse(
                run_id=plan.get("run_id", ""),
                social_move=plan.get("social_move", "answer"),
                bubble_count=plan.get("bubble_count", 1),
                delivery=deliv_slice,
                current_state=st_proto,
            )
        except Exception as e:
            logger.error(f"PlanTurn error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.PlanTurnResponse()

    def IngestBiometrics(self, request, context):
        try:
            pid = request.character_slug or "default"
            rr_list = list(request.rr_intervals_ms)
            res = self.reducer.reduce_biometric_telemetry(
                persona_id=pid,
                user_id=request.user_id,
                rr_intervals_ms=rr_list,
                sleep_hours=7.5,
            )
            bio = res.get("biometrics", {})
            return twin_engine_pb2.BiometricTelemetryResponse(
                rmssd=float(bio.get("rmssd_ms", 0.0)),
                stress_index=float(bio.get("stress_index", 0.0)),
                energy=float(res.get("energy", 0.7)),
                conversation_appetite=res.get("conversation_appetite", "medium"),
                mood=res.get("mood", "neutral"),
            )
        except Exception as e:
            logger.error(f"IngestBiometrics error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.BiometricTelemetryResponse()

    def ExecuteTurn(self, request, context):
        try:
            pid = request.character_slug or "default"
            generator = CognitiveGenerator(self.contour, self.reducer, self.planner, provider=self.provider)
            turn = generator.execute_turn(
                persona_id=pid,
                user_id=request.user_id,
                user_message=request.user_message,
            )
            st = turn.get("state", {})
            concerns = [
                c.get("topic", str(c)) if isinstance(c, dict) else str(c)
                for c in st.get("active_concerns", [])
            ]
            threads = [
                t.get("thread", str(t)) if isinstance(t, dict) else str(t)
                for t in st.get("active_threads", [])
            ]
            st_proto = twin_engine_pb2.DynamicStateSnapshot(
                mood=st.get("mood", "neutral"),
                energy=float(st.get("energy", 0.7)),
                conversation_appetite=st.get("conversation_appetite", "medium"),
                current_mode=st.get("current_mode", "casual"),
                active_concerns=concerns,
                active_threads=threads,
            )
            return twin_engine_pb2.ExecuteTurnResponse(
                run_id=turn.get("run_id", ""),
                is_verified=bool(turn.get("verified", False)),
                rejection_reason=turn.get("rejection_reason", ""),
                answer=turn.get("answer", ""),
                cited_ep_ids=turn.get("cited_ids", []),
                social_move=turn.get("social_move", "answer"),
                current_state=st_proto,
                delivered_count=int(turn.get("delivered_count", 0)),
            )
        except Exception as e:
            logger.error(f"ExecuteTurn error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return twin_engine_pb2.ExecuteTurnResponse()


def serve(
    host: str = "127.0.0.1",
    port: int = 50051,
    db_path: str = "omnitwin.db",
    provider: Optional[BaseLLMProvider] = None,
    api_key: Optional[str] = None,
    tls_cert: Optional[str] = None,
    tls_key: Optional[str] = None,
    allow_insecure_remote: bool = False,
):
    """
    Starts the OmniTwin gRPC service.
    Security Invariant: Binds to localhost (127.0.0.1) by default.
    Binding to 0.0.0.0 requires TLS or explicit allow_insecure_remote flag.
    """
    if host in ("0.0.0.0", "::") and not (tls_cert and tls_key) and not allow_insecure_remote:
        raise ValueError(
            "Insecure remote binding: Binding unencrypted gRPC service to 0.0.0.0 is prohibited "
            "without TLS or explicit --allow-insecure-remote."
        )

    interceptors = []
    if api_key:
        interceptors.append(AuthInterceptor(api_key))

    server = grpc.server(
        concurrent.futures.ThreadPoolExecutor(max_workers=10),
        interceptors=interceptors if interceptors else None,
    )
    servicer = CognitiveEngineServiceServicer(db_path, provider=provider)
    twin_engine_pb2_grpc.add_CognitiveEngineServiceServicer_to_server(servicer, server)

    bind_addr = f"{host}:{port}"
    if tls_cert and tls_key and os.path.exists(tls_cert) and os.path.exists(tls_key):
        with open(tls_key, "rb") as f:
            private_key = f.read()
        with open(tls_cert, "rb") as f:
            certificate_chain = f.read()
        server_creds = grpc.ssl_server_credentials(((private_key, certificate_chain),))
        server.add_secure_port(bind_addr, server_creds)
        logger.info(f"OmniTwin gRPC server listening with TLS on {bind_addr}")
    else:
        server.add_insecure_port(bind_addr)
        logger.info(f"OmniTwin gRPC server listening on {bind_addr} (db={db_path}, provider={servicer.provider.name})")

    server.start()
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniTwin Cognitive Engine gRPC Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on (default: 50051)")
    parser.add_argument("--db", type=str, default="omnitwin.db", help="Path to sqlite store")
    parser.add_argument("--api-key", type=str, default=None, help="Optional API key for client authentication")
    parser.add_argument(
        "--provider",
        type=str,
        default="auto",
        choices=["auto", "pi-gateway", "openrouter", "vertex", "simulator"],
        help="LLM provider: auto, pi-gateway, openrouter, vertex, or simulator",
    )
    parser.add_argument("--tls-cert", type=str, default=None, help="Path to TLS certificate file")
    parser.add_argument("--tls-key", type=str, default=None, help="Path to TLS private key file")
    parser.add_argument("--allow-insecure-remote", action="store_true", help="Allow unencrypted remote binding")
    args = parser.parse_args()

    prov = None
    if args.provider == "pi-gateway":
        prov = PiGatewayProvider()
    elif args.provider == "openrouter":
        prov = OpenRouterProvider()
    elif args.provider == "vertex":
        prov = GoogleVertexGeminiProvider()
    elif args.provider == "simulator":
        prov = OfflineSimulatorProvider()

    srv = serve(
        host=args.host,
        port=args.port,
        db_path=args.db,
        provider=prov,
        api_key=args.api_key or os.environ.get("OMNITWIN_API_KEY"),
        tls_cert=args.tls_cert or os.environ.get("OMNITWIN_TLS_CERT"),
        tls_key=args.tls_key or os.environ.get("OMNITWIN_TLS_KEY"),
        allow_insecure_remote=args.allow_insecure_remote,
    )
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        logger.info("Stopping OmniTwin gRPC server...")
        srv.stop(0)
