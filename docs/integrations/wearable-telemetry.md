# Wearable Telemetry & Physiological Pacing Integration

OmniTwin allows conversational agents to pace their conversational energy, appetite, and tone based on wearable physiological telemetry.

---

> [!CAUTION]
> **CRITICAL NON-CLINICAL DISCLAIMER**
> OmniTwin's biometric telemetry processing is **strictly an informational conversational pacing mechanism**.
> It is **NOT** a medical diagnostic device, clinical decision-support tool, or healthcare monitoring system.
> Estimates such as RMSSD or Baevsky Stress Index must **NEVER** be used to evaluate health, diagnose disease, prescribe medication, or guide clinical treatment.

---

## 1. Supported Telemetry Feeds

OmniTwin accepts two primary telemetry formats:
1. **R-R Interval Streams**: Millisecond intervals between successive heartbeats (from ECG or optical PPG sensors such as Polar H10, Apple Watch workout mode, or Oura ring).
2. **Aggregated Metrics**: Heart rate in BPM and prior night's sleep duration in hours.

---

## 2. Ingesting Telemetry via HTTP REST

Submit telemetry to the Twin Gateway:

```bash
curl -X POST http://localhost:3030/api/v1/twin/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "personaId": "alex",
    "rrIntervalsMs": [812, 804, 796, 815, 820, 808, 792, 805, 810, 818],
    "sleepHours": 7.5
  }'
```

**Response:**
```json
{
  "rmssd": 48.6,
  "stress_index": 38.2,
  "energy": 0.82,
  "conversation_appetite": "chatty",
  "mood": "calm",
  "transport": "grpc"
}
```

---

## 3. How Pacing Affects Agent Behavior

When physiological energy is low (e.g. \(E_{\text{phys}} < 0.35\)) or allostatic load is elevated:
- **Social Move Adaptation**: The turn planner shifts from expansive discourse (`give_opinion`, `practical_help`) to low-overhead presence (`minimal_presence` or concise `acknowledge`).
- **Cadence Modulation**: The cadence engine reduces maximum bubbles to 1 and limits message lengths, emulating a human partner who is fatigued or resting.
- **Relational Boundary Awareness**: Exhausted twins do not initiate emotionally demanding or vulnerable threads until energy recovers.
