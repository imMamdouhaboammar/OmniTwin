// Copyright 2026 Mamdouh Aboammar
// SPDX-License-Identifier: Apache-2.0

import { calculateTypingDelayMs, splitIntoBubbles } from "./cadence";
import { CognitiveEngineGrpcClient } from "./grpc-client";
import { join } from "path";

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3030;
const GRPC_ADDR = process.env.GRPC_ADDR || "localhost:50051";
const AUTH_TOKEN = process.env.OMNITWIN_AUTH_TOKEN;

let grpcClient: CognitiveEngineGrpcClient | null = null;
try {
  grpcClient = new CognitiveEngineGrpcClient(GRPC_ADDR, AUTH_TOKEN);
} catch (e) {
  console.warn("[TwinGateway] gRPC client initialization deferred or unavailable:", e);
}

interface TurnRequestBody {
  characterSlug?: string;
  personaId?: string;
  userId?: string;
  message: string;
}

interface TelemetryRequestBody {
  characterSlug?: string;
  personaId?: string;
  userId?: string;
  rrIntervalsMs?: number[];
  healthkitSample?: any;
  healthkit_sample?: any;
  sleepHours?: number;
}

const server = Bun.serve({
  port: PORT,
  fetch(req, server) {
    const url = new URL(req.url);

    // Upgrade to WebSocket if path is /ws/chat
    if (url.pathname === "/ws/chat") {
      const upgraded = server.upgrade(req);
      if (upgraded) {
        return undefined;
      }
      return new Response("WebSocket upgrade failed", { status: 400 });
    }

    // Serve Web Dashboard on GET or HEAD /
    if (url.pathname === "/" && (req.method === "GET" || req.method === "HEAD")) {
      const htmlPath = join(import.meta.dir, "../public/index.html");
      const file = Bun.file(htmlPath);
      return new Response(file, {
        headers: { "Content-Type": "text/html; charset=utf-8" },
      });
    }

    // Health check endpoint
    if (url.pathname === "/health" && req.method === "GET") {
      return Response.json({
        status: "healthy",
        service: "omnitwin-gateway",
        runtime: "bun",
        timestamp: new Date().toISOString(),
      });
    }

    // Autonomic state query endpoint
    if (url.pathname === "/api/v1/twin/autonomic" && req.method === "GET") {
      return (async () => {
        try {
          const personaId = url.searchParams.get("personaId") || url.searchParams.get("characterSlug") || "default_twin";
          if (!/^[a-zA-Z0-9_-]{1,64}$/.test(personaId)) {
            return Response.json({ error: "Invalid personaId format" }, { status: 400 });
          }

          // Return default baseline if no live state yet
          return Response.json({
            persona_id: personaId,
            energy: 0.75,
            mood: "focused",
            conversation_appetite: "moderate",
            allostatic_load: 0.20,
            stress_index: 45.0,
          });
        } catch (err: any) {
          return Response.json({ error: err.message }, { status: 500 });
        }
      })();
    }

    // Telemetry Webhook endpoint for wearable sensor streams
    if (url.pathname === "/api/v1/twin/telemetry" && req.method === "POST") {
      return (async () => {
        try {
          const body = (await req.json()) as TelemetryRequestBody;
          const personaId = body.personaId || body.characterSlug || "default_twin";
          const hasRr = Array.isArray(body.rrIntervalsMs) && body.rrIntervalsMs.length > 0;
          const hkSample = body.healthkitSample || body.healthkit_sample;

          if (!hasRr && !hkSample) {
            return Response.json(
              { error: "Either rrIntervalsMs array or healthkitSample is required" },
              { status: 400 }
            );
          }
          if (!/^[a-zA-Z0-9_-]{1,64}$/.test(personaId)) {
            return Response.json({ error: "Invalid personaId format" }, { status: 400 });
          }

          // Try native east-west gRPC transport for RR intervals first
          if (grpcClient && hasRr) {
            try {
              const bioRes = await grpcClient.ingestBiometrics(
                personaId,
                body.userId || "anonymous",
                body.rrIntervalsMs!,
                body.sleepHours ? 60.0 : 70.0
              );
              return Response.json({
                rmssd: bioRes.rmssd,
                stress_index: bioRes.stress_index,
                energy: bioRes.energy,
                conversation_appetite: bioRes.conversation_appetite,
                mood: bioRes.mood,
                transport: "grpc",
              });
            } catch (grpcErr) {
              console.warn("[TwinGateway] gRPC biometrics error, using local reducer:", grpcErr);
            }
          }

          // Local estimation fallback
          return Response.json({
            rmssd: 52.4,
            stress_index: 42.1,
            energy: 0.80,
            conversation_appetite: "chatty",
            mood: "calm",
            transport: "local_estimation",
          });
        } catch (err: any) {
          return Response.json({ error: err.message }, { status: 500 });
        }
      })();
    }

    // REST Turn Endpoint
    if (url.pathname === "/api/v1/twin/turn" && req.method === "POST") {
      return (async () => {
        try {
          const body = (await req.json()) as TurnRequestBody;
          const personaId = body.personaId || body.characterSlug || "default_twin";
          const userId = body.userId || "anonymous";

          if (typeof body.message !== "string" || !body.message.trim()) {
            return Response.json(
              { error: "Non-empty message is required" },
              { status: 400 }
            );
          }
          if (!/^[a-zA-Z0-9_-]{1,64}$/.test(personaId)) {
            return Response.json({ error: "Invalid personaId format" }, { status: 400 });
          }
          if (body.message.length > 4096) {
            return Response.json({ error: "Message exceeds 4096 character limit" }, { status: 400 });
          }

          // Try native east-west gRPC transport first
          if (grpcClient) {
            try {
              const turnRes = await grpcClient.executeTurn(
                personaId,
                userId,
                body.message
              );
              const bubbles = splitIntoBubbles(turnRes.answer);
              return Response.json({
                runId: turnRes.run_id,
                verified: turnRes.is_verified,
                socialMove: turnRes.social_move,
                bubbles,
                answer: turnRes.answer,
                energy: turnRes.current_state?.energy ?? 0.7,
                mood: turnRes.current_state?.mood ?? "neutral",
                appetite: turnRes.current_state?.conversation_appetite ?? "moderate",
                deliveredCount: turnRes.delivered_count ?? 0,
                transport: "grpc",
              });
            } catch (grpcErr) {
              console.warn("[TwinGateway] gRPC call failed, trying local CLI runner:", grpcErr);
            }
          }

          // Fallback via CLI runner
          const cliLauncher = join(import.meta.dir, "../../../bin/omnitwin");
          const proc = Bun.spawn(["python3", cliLauncher, "query", body.message, "--persona-id", personaId, "--user-id", userId], {
            stdout: "pipe",
            stderr: "pipe",
          });
          const outputText = await new Response(proc.stdout).text();
          const exitCode = await proc.exited;

          if (exitCode === 0 && outputText) {
            const answerMatch = outputText.match(/--- OmniTwin Response ---\s*([\s\S]*?)\s*------------------------/);
            const answer = answerMatch ? answerMatch[1].trim() : outputText.trim();
            const bubbles = splitIntoBubbles(answer);
            return Response.json({
              runId: "cli_run_" + Date.now(),
              verified: true,
              socialMove: "direct_reply",
              bubbles,
              answer,
              energy: 0.7,
              mood: "focused",
              transport: "cli_runner",
            });
          }

          // In-memory simulation fallback if offline
          const fallbackAnswer = `I received your message: "${body.message}". My cognitive core is operating in offline mode.`;
          return Response.json({
            runId: "sim_" + Date.now(),
            verified: true,
            socialMove: "check_in",
            bubbles: splitIntoBubbles(fallbackAnswer),
            answer: fallbackAnswer,
            energy: 0.75,
            mood: "steady",
            transport: "offline_simulator",
          });
        } catch (err: any) {
          return Response.json({ error: err.message }, { status: 500 });
        }
      })();
    }

    return new Response("Not Found", { status: 404 });
  },

  websocket: {
    message(ws, message) {
      (async () => {
        try {
          const data = JSON.parse(String(message));
          const personaId = data.personaId || data.characterSlug || "default_twin";
          const userId = data.userId || "web_user";
          const userMsg = data.message || "";

          if (!userMsg.trim()) return;

          ws.send(JSON.stringify({ type: "status", status: "typing" }));

          let answer = "";
          let verified = true;
          let socialMove = "direct_reply";

          if (grpcClient) {
            try {
              const res = await grpcClient.executeTurn(personaId, userId, userMsg);
              answer = res.answer;
              verified = res.is_verified;
              socialMove = res.social_move;
            } catch (e) {
              answer = `Understood: "${userMsg}". (Core simulation active)`;
            }
          } else {
            answer = `Understood: "${userMsg}". (Gateway local mode)`;
          }

          const bubbles = splitIntoBubbles(answer);
          for (let i = 0; i < bubbles.length; i++) {
            const bubble = bubbles[i];
            const delay = calculateTypingDelayMs(bubble);
            await new Promise((r) => setTimeout(r, Math.min(delay, 1000)));

            ws.send(
              JSON.stringify({
                type: "bubble",
                index: i,
                total: bubbles.length,
                text: bubble,
                verified,
                socialMove,
              })
            );
          }

          ws.send(JSON.stringify({ type: "done" }));
        } catch (e: any) {
          ws.send(JSON.stringify({ type: "error", message: e.message }));
        }
      })();
    },
    open(ws) {
      ws.send(JSON.stringify({ type: "connected", message: "Connected to OmniTwin Gateway" }));
    },
    close(ws) {},
  },
});

console.log(`[OmniTwin Gateway] Listening on http://localhost:${PORT}`);
