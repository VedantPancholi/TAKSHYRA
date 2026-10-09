# Streaming reliability: Kafka, MQTT, Event Hubs and analytical sinks

## Streaming reference workflow
Synthetic connected-device messages → MQTT broker or Kafka/Redpanda → Python decoder/enricher → ClickHouse (later optional) / Parquet → dashboard. Alternative Event Hubs input adapter only in Azure sandbox.

## Required concepts
- `event_time`, `ingest_time`, `processing_time` and watermark are different.
- Broker ack/committed consumer offset is not evidence that transformed records reached sink.
- Event ordering is per partition/key, not globally guaranteed.
- At-least-once processing is expected; dedupe keys and idempotent sink writes are required.
- Offset replay is bounded by retention and authorization.
- Backpressure and lag can be caused by source bursts, poison messages, sink slowness, or partitions.

## Core metrics
`partition_lag_messages`, `lag_seconds` where event-time can be measured, `records_ingested`, `records_decoded`, `records_written`, `dlq_count`, `decode_error_rate`, `throughput_per_sec`, `watermark_age`, `checkpoint_age`, `source_sink_reconciliation_gap`, `duplicate_ratio`.

Do not expose raw IDs/high-cardinality values as metrics labels. Use trace/run IDs in logs/traces instead.

## Schema change example
Vehicle publishes schema v15 and decoder only supports v14. Some payloads are rejected. Monitoring sees decoder exceptions + DLQ growth + sink reconciliation gap. Diagnosis hypothesizes schema incompatibility and cites evidence; shadow lab replays captured v15 events against a sandbox decoder; authorized replay recovers only eligible bounded messages after new code is independently reviewed. **No agent rewrites the decoder program itself.**

## Failure fixtures
1. Consumer falls behind source.
2. Source duplicates messages after reconnect.
3. Events arrive late/out of order.
4. Poison message repeatedly fails, goes DLQ with reason.
5. Sink temporarily unavailable while offsets advance incorrectly; reconciling should catch.
6. Broker restarts and queue redelivers.
7. Checkpoint expired or retention window missing (replay DENY/INCONCLUSIVE).
8. Schema incompatible with target decoder.

## Local first
Provide deterministic 1-2 minute scenario scripts with Docker Compose optional `streaming` profile. Test simulated broker/consumer and fixtures before optional live Kafka broker. No requirement to process millions of events to pass R1–R4.
