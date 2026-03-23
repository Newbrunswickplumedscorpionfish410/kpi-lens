# 📊 KPI-Lens

**LLM-powered supply chain KPI anomaly detection and auto-reporting**

[![CI](https://github.com/aliivaezii/kpi-lens/actions/workflows/ci.yml/badge.svg)](https://github.com/aliivaezii/kpi-lens/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

KPI-Lens monitors 8 operational supply chain KPIs in real time, detects statistical and ML-based anomalies, and uses **Claude (claude-sonnet-4-6) via MCP** to generate natural-language root cause analyses and executive PowerPoint reports — automatically.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         KPI-Lens                                │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────────────────────────┐ │
│  │  Streamlit   │────►│         Claude Agent                 │ │
│  │  Dashboard   │     │    (claude-sonnet-4-6 via API)       │ │
│  │  Port 8501   │     └──────────────┬───────────────────────┘ │
│  └──────────────┘                    │ MCP Tool Calls           │
│                                      ▼                          │
│  ┌──────────────┐     ┌─────────────────────────────────────┐  │
│  │  FastAPI     │◄───►│         MCP Server                  │  │
│  │  Port 8000   │     │  (read-only KPI & anomaly access)   │  │
│  └──────┬───────┘     └─────────────────────────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐     ┌─────────────────────────────────────┐  │
│  │   SQLite DB  │     │   Anomaly Detection Pipeline        │  │
│  │   kpi_lens   │     │  ThresholdDetector → Z-Score → IQR  │  │
│  │   .db        │     │  → CUSUM → IsolationForest          │  │
│  └──────────────┘     │  → EnsembleDetector (weighted vote) │  │
│                        └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## KPIs Monitored

| KPI | Unit | Target | Industry Benchmark |
|---|---|---|---|
| OTIF Delivery Rate | % | ≥ 95% | 95.5% |
| Order Fill Rate | % | ≥ 97% | 96.0% |
| Demand Forecast Accuracy | % | ≥ 85% | 80.0% |
| Inventory Turnover | turns/yr | ≥ 12 | 10.0 |
| Days Inventory Outstanding | days | ≤ 30 | 35.0 |
| Supplier DPPM | ppm | ≤ 500 | 800 |
| Lead Time Variance | days σ | ≤ 3 | 5.0 |
| PO Cycle Time | days | ≤ 14 | 18.0 |

## Key Features

- **Multi-method anomaly detection**: Z-score (spikes) + IQR (distribution shifts) + CUSUM (drift) + Isolation Forest (multivariate ML)
- **LLM root cause analysis**: Claude investigates anomalies via MCP tools and generates narrative + 3 actionable recommendations
- **Interactive dashboard**: Streamlit + Plotly with RAG health grid, trend charts, anomaly log, and live chat interface
- **Automated reports**: PowerPoint + PDF with KPI charts, anomaly deep-dives, and executive summaries
- **Power BI export**: Structured Excel workbooks with named tables for direct Power BI consumption
- **MCP server**: Gives Claude structured, read-only access to KPI data via 6 typed tools
- **Fully containerised**: Docker Compose for one-command deployment

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/aliivaezii/kpi-lens.git
cd kpi-lens
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Seed database with 2 years of synthetic data
python data/seeds/generate_kpis.py

# 4a. Run with Docker (recommended)
docker compose up

# 4b. Or run services individually
uvicorn kpi_lens.api.main:app --reload &
streamlit run kpi_lens/dashboard/app.py
```

Open http://localhost:8501 for the dashboard.

## Running with MCP (Claude Desktop)

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "kpi-lens": {
      "command": "python",
      "args": ["-m", "kpi_lens.mcp_server.server"],
      "cwd": "/path/to/kpi-lens",
      "env": {"ANTHROPIC_API_KEY": "sk-ant-..."}
    }
  }
}
```

Claude Desktop will then have live access to your supply chain KPIs.

## Development

```bash
# Run tests
pytest tests/unit/ -v

# Lint + format
ruff check kpi_lens/ && ruff format kpi_lens/

# Type check
mypy kpi_lens/

# Run anomaly scan
python scripts/run_anomaly_scan.py
```

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Claude claude-sonnet-4-6 (Anthropic API) |
| MCP | `mcp` (FastMCP) — Model Context Protocol |
| Anomaly Detection | Z-score, IQR, CUSUM, Isolation Forest (sklearn) |
| Dashboard | Streamlit + Plotly |
| API | FastAPI + Uvicorn |
| Database | SQLite via SQLAlchemy 2.0 |
| Reporting | python-pptx + LibreOffice (PDF) + openpyxl (Power BI) |
| Scheduling | APScheduler |
| CI/CD | GitHub Actions |
| Containerization | Docker + Docker Compose |

## Project Structure

```
kpi_lens/
├── config.py           # Pydantic settings (single .env reader)
├── db/                 # SQLAlchemy models + repository pattern
├── kpis/               # KPI definitions — 8 typed constants
├── anomaly/            # Detection pipeline: base ABC → detectors → ensemble
├── llm/                # Anthropic client, prompts, analyst orchestrator
├── mcp_server/         # FastMCP server with 6 typed tools
├── reporting/          # PPTX, PDF, Excel/Power BI export
├── dashboard/          # Streamlit app (5 pages)
└── api/                # FastAPI endpoints
```

---

*Built by [Ali Vaezi](https://alivaezi.vercel.app) · MSc Digital Skills, Politecnico di Torino*
*Part of a supply chain AI research portfolio — see also [SUPRA-PPO](https://github.com/aliivaezii/FBWM-FTOPSIS-PPO)*
