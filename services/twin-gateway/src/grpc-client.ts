// Copyright 2026 Mamdouh Aboammar
// SPDX-License-Identifier: Apache-2.0

import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import path from "path";
import fs from "fs";

function resolveProtoPath(): string {
  if (process.env.OMNITWIN_PROTO_PATH && fs.existsSync(process.env.OMNITWIN_PROTO_PATH)) {
    return process.env.OMNITWIN_PROTO_PATH;
  }
  const candidate1 = path.resolve(import.meta.dir, "../../proto/twin_engine.proto");
  if (fs.existsSync(candidate1)) return candidate1;

  const candidate2 = path.resolve(import.meta.dir, "../../../proto/twin_engine.proto");
  if (fs.existsSync(candidate2)) return candidate2;

  const candidate3 = path.resolve(import.meta.dir, "../../src/omnitwin/proto/twin_engine.proto");
  if (fs.existsSync(candidate3)) return candidate3;

  return candidate1;
}

const PROTO_PATH = resolveProtoPath();

let twinProto: any = null;

try {
  const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
  const protoDescriptor = grpc.loadPackageDefinition(packageDefinition) as any;
  twinProto = protoDescriptor.twin.engine.v1;
} catch (e) {
  console.warn(`[CognitiveEngineGrpcClient] Warning: Could not load proto from ${PROTO_PATH}:`, e);
}

export interface PlanTurnResponse {
  run_id: string;
  social_move: string;
  bubble_count: number;
  delivery: {
    run_id: string;
    extract_points: Array<{
      id: string;
      meta_id: string;
      group: string;
      vector: string;
      text: string;
      confidence_score: number;
    }>;
    state_summary: string;
  };
  current_state: {
    mood: string;
    energy: number;
    conversation_appetite: string;
    current_mode: string;
    active_concerns: string[];
    active_threads: string[];
  };
}

export interface VerifyTurnResponse {
  is_accepted: boolean;
  missing_ep_ids: string[];
  rejection_reason: string;
}

export interface BiometricTelemetryResponse {
  rmssd: number;
  stress_index: number;
  energy: number;
  conversation_appetite: string;
  mood: string;
}

export interface ExecuteTurnResponse {
  run_id: string;
  is_verified: boolean;
  rejection_reason: string;
  answer: string;
  cited_ep_ids: string[];
  social_move: string;
  current_state: {
    mood: string;
    energy: number;
    conversation_appetite: string;
    current_mode: string;
    active_concerns: string[];
    active_threads: string[];
  };
  delivered_count: number;
}

export class CognitiveEngineGrpcClient {
  private client: any;

  constructor(address: string = "localhost:50051", authToken?: string) {
    if (!twinProto) {
      throw new Error(`CognitiveEngine gRPC proto not initialized. Check proto path.`);
    }

    let creds = grpc.credentials.createInsecure();
    if (authToken) {
      const callCreds = grpc.credentials.createFromMetadataGenerator((_params, callback) => {
        const meta = new grpc.Metadata();
        meta.add("authorization", `Bearer ${authToken}`);
        callback(null, meta);
      });
      creds = grpc.credentials.combineChannelCredentials(creds, callCreds);
    }

    this.client = new twinProto.CognitiveEngineService(address, creds);
  }

  public openIntent(
    characterSlug: string,
    userId: string,
    userMessage: string
  ): Promise<{ run_id: string; character_slug: string; created_at_unix: number }> {
    return new Promise((resolve, reject) => {
      this.client.OpenIntent(
        { character_slug: characterSlug, user_id: userId, user_message: userMessage },
        (err: any, response: any) => {
          if (err) return reject(err);
          resolve(response);
        }
      );
    });
  }

  public planTurn(
    characterSlug: string,
    userId: string,
    userMessage: string
  ): Promise<PlanTurnResponse> {
    return new Promise((resolve, reject) => {
      this.client.PlanTurn(
        { character_slug: characterSlug, user_id: userId, user_message: userMessage },
        (err: any, response: any) => {
          if (err) return reject(err);
          resolve(response);
        }
      );
    });
  }

  public verifyTurn(
    runId: string,
    citedEpIds: string[]
  ): Promise<VerifyTurnResponse> {
    return new Promise((resolve, reject) => {
      this.client.VerifyTurn(
        { run_id: runId, cited_ep_ids: citedEpIds },
        (err: any, response: any) => {
          if (err) return reject(err);
          resolve(response);
        }
      );
    });
  }

  public ingestBiometrics(
    characterSlug: string,
    userId: string,
    rrIntervalsMs: number[],
    meanHrBpm: number = 70.0
  ): Promise<BiometricTelemetryResponse> {
    return new Promise((resolve, reject) => {
      this.client.IngestBiometrics(
        {
          character_slug: characterSlug,
          user_id: userId,
          rr_intervals_ms: rrIntervalsMs,
          mean_hr_bpm: meanHrBpm,
        },
        (err: any, response: any) => {
          if (err) return reject(err);
          resolve(response);
        }
      );
    });
  }

  public executeTurn(
    characterSlug: string,
    userId: string,
    userMessage: string
  ): Promise<ExecuteTurnResponse> {
    return new Promise((resolve, reject) => {
      this.client.ExecuteTurn(
        { character_slug: characterSlug, user_id: userId, user_message: userMessage },
        (err: any, response: any) => {
          if (err) return reject(err);
          resolve(response);
        }
      );
    });
  }
}
