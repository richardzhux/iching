# NEW FEATURE:

Welcome to my I Ching Project! This repository is designed to offer an interactive experience with I Ching (The Book of Changes),
allowing users to perform traditional divination using methods such as the 50-yarrow stalk method, three-coin toss, or Meihua Yishu.
The repository also includes tools to calculate BaZi (八字) and the corresponding five elements (五行).

## Project Layout

```
├── src/iching
│   ├── cli/runner.py          # Console entry point
│   ├── core/                  # Domain logic (hexagrams, divination, BaZi, time utils)
│   ├── gui/app.py             # Gradio web interface
│   ├── integrations/          # AI + Najia adapters
│   └── services/session.py    # Session orchestration layer
├── data/                      # Textual resources (guaci, takashima, etc.)
├── legacy/                    # Archived pre-refactor scripts
├── tests/                     # Pytest-based smoke tests
└── iching5.py                 # CLI bootstrapper (uses the refactored package)
```

## Usage

```bash
# install dependencies
pip install -r requirements.txt

# run the interactive console
python iching5.py

# launch the Gradio UI
python gui.py

# run the FastAPI backend (development)
uvicorn iching.web.api.main:app --reload

# execute automated tests
pytest
```

## Web Architecture & Roadmap

The app is now split into three independent layers:

1. **Core domain (`src/iching`)** – divination, BaZi, Najia, and AI orchestration.
2. **FastAPI backend (`iching.web.api`)** – exposes `/api/config`, `/api/sessions`, and `/api/health`, handling validation, AI gating, and archiving.
3. **React frontend (planned)** – a Next.js + Tailwind + shadcn/ui app deployed on Vercel that consumes the FastAPI API. See `docs/frontend-roadmap.md` for scaffolding instructions.

`gui.py` (Streamlit) remains for debugging, but all non-visual logic now lives inside reusable services so upcoming clients can share the same engine over HTTP.

Deployment checklists for Render/Vercel live in `docs/deployment.md`.

# Next steps

a. ENTIRELY RESTRUCTURE FOR CLARITY, use more class and subclass ✅ 10.23  
b. 纠正山地剥的错误binary code ✅ 10.24  
c. 校对傅佩荣 ✅ 10.27  
d. meihua make 3 3digit nums ✅ 10.24  
e. count and classify jixiong in each yao, rate ✅ 10.30  
f. generate flow chart ✅ 11.2  
g. 加入自然意象 ✅ 11.3  
h. 加入psutil, tqdm ✅ 11.4
i. integrate with AI for analysis and explanation ✅ 8.14 (2025)
j. add UI with Gradio ✅ 9.4
k. 八卦纳甲 卦分八宫 旺相休囚和生旺墓绝 十二长生 世应 六亲 六神 用神等 ✅ 11.3
l. complete titled database for all 64 hexagrams ✅ 11.4
m. total restructure ✅ 11.4
n. changed UI to streamlit ✅ 11.5

# WARNING
THE MAKEFILE IN THIS REPOSITORY CONTAINS COMMANDS THAT MAY RESULT IN THE PERMANENT DELETION OF DATA OR SYSTEM DAMAGE. DO NOT RUN THIS MAKEFILE UNLESS YOU ARE PREPARED FOR PERMANENT DATA LOSS OR SYSTEM DAMAGE. USE ONLY IN A SECURE, ISOLATED ENVIRONMENT FOR TESTING PURPOSES.
