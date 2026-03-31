# piv-oac — Deployment Guide

Infrastructure setup for running PIV/OAC pipelines in production or staging environments.

---

## 1. Minimum Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | ≥ 3.11 | SDK runtime |
| pip | ≥ 23.0 | Package management |
| Anthropic API key | — | Required for all agents |
| Docker (optional) | ≥ 24.0 | OTel Collector, local dev |

---

## 2. Installation

### Production

```bash
pip install piv-oac
```

### With OpenAI provider support

```bash
pip install "piv-oac[openai]"
```

### Development (with tests + type checking)

```bash
git clone https://github.com/DavidCaastro/lab.git
cd lab/sdk
pip install -e ".[dev]"
```

---

## 3. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `OPENAI_API_KEY` | Only for OpenAI provider | — | OpenAI API key |
| `PIV_OAC_TELEMETRY_ENABLED` | No | `false` | Enable OTel tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | `http://localhost:4317` | OTLP gRPC endpoint |

Set them in your environment or `.env` file (never commit `.env`):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export PIV_OAC_TELEMETRY_ENABLED="true"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4317"
```

---

## 4. OpenTelemetry Collector (Docker)

For local observability testing with Docker Desktop:

```bash
# 1. Create a minimal collector config
cat > otel-collector-config.yaml << 'EOF'
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [debug]
EOF

# 2. Run the collector
docker run -d \
  --name otel-collector \
  -p 4317:4317 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  otel/opentelemetry-collector:latest \
  --config /etc/otel-collector-config.yaml
```

### Verify spans are arriving

```bash
docker logs -f otel-collector
# You should see span data after running an agent invoke()
```

### With Jaeger UI (optional)

```yaml
# docker-compose.yml
version: "3"
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"   # Jaeger UI
      - "4317:4317"     # OTLP gRPC
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  piv-oac-app:
    build: .
    environment:
      - PIV_OAC_TELEMETRY_ENABLED=true
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

```bash
docker-compose up -d
# Open http://localhost:16686 for Jaeger UI
```

---

## 5. Checkpoint Storage

By default, `CheckpointStore` writes to `.piv/active/` relative to the working directory.

```python
from piv_oac.checkpoint import CheckpointStore

# Default: writes to .piv/ in current directory
store = CheckpointStore()

# Custom location (e.g., shared volume in k8s)
store = CheckpointStore(base_dir="/mnt/shared/piv-checkpoints")
```

For containerized deployments, mount a persistent volume at the checkpoint path so sessions survive container restarts.

---

## 6. Engram Storage

`EngramStore` defaults to `engram/` in the current directory.

```python
from piv_oac.engram import EngramStore

# Default
store = EngramStore()

# Custom location
store = EngramStore(engram_dir="/mnt/shared/engram")
```

**Security note:** Only `AuditAgent` is authorized to write engram atoms. Any other writer raises `PIVOACError`. Do not grant write permissions on the engram directory to other processes.

---

## 7. Running Tests

```bash
cd sdk

# All tests with coverage report
python -m pytest --cov=piv_oac --cov-report=term-missing

# Fail if coverage drops below 80%
python -m pytest --cov=piv_oac --cov-fail-under=80

# Type checking
python -m mypy piv_oac/
```

---

## 8. Production Checklist

Before deploying to a production environment:

- [ ] `ANTHROPIC_API_KEY` set as a secret (not in code or logs)
- [ ] `PIV_OAC_TELEMETRY_ENABLED=true` with a real OTLP endpoint
- [ ] Checkpoint directory on a persistent volume
- [ ] Engram directory on a persistent volume with restricted write access
- [ ] `.piv/active/` excluded from version control (already in `.gitignore`)
- [ ] `security_vault.md` not readable by any automated process (Zero-Trust)
- [ ] Gate 3 confirmation flow has a human-accessible interface (webhook, Slack, etc.)
- [ ] `metrics/sessions.md` backed up periodically (append-only log)
