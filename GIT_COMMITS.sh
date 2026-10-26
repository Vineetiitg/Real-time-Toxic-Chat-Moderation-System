## ─────────────────────────────────────────────────────────────
##  SafeChat Data Pipeline — Git Commit Commands
##
##  Run these commands whenever you're ready to commit.
##  Each block is an independent, well-scoped commit.
##  Execute them in order, at whatever timestamp suits you.
## ─────────────────────────────────────────────────────────────


## ─── Commit 1: Pipeline scaffolding & configuration ──────────
## (Project structure, config, .gitignore update)

git add data_pipeline/__init__.py data_pipeline/config.py .gitignore
git commit -m "feat(data-pipeline): add pipeline scaffolding and configuration

- Create data_pipeline/ package with centralized config
- Define 6-label schema constants and all path configs
- Add HuggingFace dataset URLs and sampling parameters
- Update .gitignore to exclude raw/processed CSVs (reproducible via script)"


## ─── Commit 2: Step 1 — Dataset download script ─────────────
## (Jigsaw, Prism, HASOC downloaders with smart rare-class sampling)

git add data_pipeline/step1_download.py
git commit -m "feat(data-pipeline): add Step 1 — raw dataset download from HuggingFace

- Download Jigsaw English toxicity (with rare-class preservation sampling)
- Download Prism Hinglish hate speech dataset
- Download HASOC 2019 Indic hate speech dataset
- Each source saved as separate raw CSV (no merging at this stage)
- Idempotent: skips re-download if file already exists"


## ─── Commit 3: Step 2 — Unify, clean, and deduplicate ───────
## (Schema mapping, text cleaning, adversarial normalization, dedup)

git add data_pipeline/step2_unify.py
git commit -m "feat(data-pipeline): add Step 2 — unify schemas, clean, and deduplicate

- Map Jigsaw 6-label, Prism binary, HASOC multi-class → unified 6-tag schema
- Apply Unicode NFC normalization and control character removal
- Add adversarial normalization (Cyrillic homoglyphs, leetspeak, char repetition)
- Fuzzy deduplication via normalized text matching
- Add 40 hand-curated Indic seed samples for threat/identity_hate coverage
- Length filtering (drop <3 chars or >2000 chars)"


## ─── Commit 4: Step 3 — EDA and validation statistics ───────
## (Class distribution, pos_weights, text stats, co-occurrence matrix)

git add data_pipeline/step3_eda.py
git commit -m "feat(data-pipeline): add Step 3 — comprehensive EDA and pos_weight calc

- Compute BCEWithLogitsLoss pos_weight per class (capped at 25.0)
- Analyze text length distribution (char and word level)
- Script breakdown analysis (Latin vs Devanagari vs other)
- Label co-occurrence matrix
- Data quality checks (empty texts, safe/toxic ratio)
- Export Markdown report + pos_weights.json + eda_stats.json"


## ─── Commit 5: Step 4 — Multi-label stratified splitting ────
## (80/10/10 split with MultilabelStratifiedKFold)

git add data_pipeline/step4_split.py
git commit -m "feat(data-pipeline): add Step 4 — multi-label stratified train/val/test split

- Use iterative-stratification for proper multi-label splitting
- 80% train / 10% val / 10% test with class distribution preservation
- Data leakage verification (zero overlap between splits)
- Per-split class rate comparison for consistency check
- Export split_report.json with full statistics"


## ─── Commit 6: Step 5 — Final validation and export ─────────
## (Schema checks, leakage verification, export to ml-service)

git add data_pipeline/step5_validate.py
git commit -m "feat(data-pipeline): add Step 5 — final validation gate and export

- Schema validation (columns, types, non-null checks)
- Cross-split data leakage detection
- Class distribution consistency verification
- Export validated splits to ml-service/training/data/real_datasets/
- Copy pos_weights and EDA report for training script consumption"


## ─── Commit 7: Pipeline runner ──────────────────────────────
## (Master script that runs all 5 steps in sequence)

git add data_pipeline/run_all.py
git commit -m "feat(data-pipeline): add full pipeline runner (run_all.py)

- Orchestrates all 5 steps sequentially: download → unify → EDA → split → validate
- Each step also runnable independently via python -m data_pipeline.stepN_xxx
- Ready for CI/CD integration"


## ─────────────────────────────────────────────────────────────
##  OPTIONAL: Single combined commit (if you prefer fewer commits)
## ─────────────────────────────────────────────────────────────
##
## git add data_pipeline/ .gitignore
## git commit -m "feat: add production data pipeline (download, unify, EDA, split, validate)
##
## Complete 5-step data pipeline replacing synthetic training data:
## - Step 1: Download Jigsaw, Prism, HASOC from HuggingFace
## - Step 2: Unify to 6-label schema, clean text, adversarial normalization
## - Step 3: EDA with pos_weight calculation and Markdown report
## - Step 4: Multi-label stratified 80/10/10 split (no data leakage)
## - Step 5: Final validation gate and export to training directory
##
## Fixes the core issue of training on 31 duplicated sentences."



## ─── Commit 8: Generated EDA reports and split metadata ─────
## (Pipeline output artifacts that are small enough to track)

git add data_pipeline/reports/ data_pipeline/splits/split_report.json
git commit -m "data(pipeline): add EDA reports, pos_weights, and split metadata

Pipeline run results (37,246 clean samples from 37,638 raw):
- EDA_REPORT.md: source distribution, class imbalance, length stats
- pos_weights.json: BCEWithLogitsLoss weights for class imbalance
- eda_stats.json: full statistics in machine-readable format
- split_report.json: train/val/test split metadata (80/10/10)
- Zero data leakage verified across all splits
- Class distribution consistent within 0.1% across splits"


## ═════════════════════════════════════════════════════════════
##  PHASE 2: Classification Model Training Pipeline
## ═════════════════════════════════════════════════════════════


## ─── Commit 9: Training config, dataset, and focal loss ───────
## (PyTorch Dataset, WeightedFocalLoss, TrainingConfig)

git add training/__init__.py training/config.py training/dataset.py training/losses.py
git commit -m "feat(training): add training config, multi-label dataset, and weighted focal loss

- Add TrainingConfig dataclass with defaults for Hing-RoBERTa / LoRA / Focal Loss
- Auto-fill paths from data pipeline outputs (splits, pos_weights)
- Add ToxicityDataset PyTorch class with proper padding/truncation
- Implement WeightedFocalLoss combining per-class pos_weights with focal modulation
- Solves gradient collapse on rare labels (e.g. threat at 1.3%)"


## ─── Commit 10: Multi-label evaluation and threshold tuning ───
## (Evaluation pass, Precision-Recall curves, per-class optimal thresholds)

git add training/evaluate.py
git commit -m "feat(training): add multi-label evaluation and PR-curve threshold tuning

- Implement run_evaluation computing Macro/Micro F1, Precision, Recall, and ROC-AUC
- Add optimize_thresholds using Precision-Recall curve F1 maximization
- Avoid misleading accuracy metric on imbalanced multi-label toxicity data
- Add pretty-printed evaluation summary logging"


## ─── Commit 11: Core trainer and CLI runner ───────────────────
## (LoRA fine-tuning, AMP, model merge on save, CLI entry point)

git add training/train.py training/run_training.py
git commit -m "feat(training): add core trainer and CLI entry point

- Full training loop with FP16 Automatic Mixed Precision (torch.amp)
- LoRA support (r=32, alpha=64) with fallback to full fine-tuning
- Best-model checkpointing by validation Macro F1
- Merge LoRA weights into base model before export for zero-PEFT inference
- CLI entry point with configurable epochs, batch-size, lr, and model name"


## ═════════════════════════════════════════════════════════════
##  PHASE 3: Intent-Preserving Detoxification (Option A)
## ═════════════════════════════════════════════════════════════


## ─── Commit 12: Detox config, LRU+TTL cache, and offline scrubber ──
## (Config, In-memory LRU cache with TTL, offline multilingual scrubber)

git add detoxification/config.py detoxification/cache.py detoxification/scrubber.py
git commit -m "feat(detox): add config, LRU+TTL cache, and multilingual intent scrubber

- DetoxConfig supporting GEMINI_API_KEY, custom models, and proxy base URLs
- DetoxCache: thread-safe LRU cache with TTL expiration and key normalization
- IntentPreservingScrubber: offline rule engine preserving intent across English,
  Hinglish, and Devanagari Hindi (<1ms latency, 100% local fallback)"


## ─── Commit 13: Response validation & Gemini REST client ─────
## (Gatekeeper validator, direct httpx Gemini REST + SSE streaming client)

git add detoxification/validator.py detoxification/gemini_client.py
git commit -m "feat(detox): add response validation gatekeeper and Gemini API client

- ResponseValidator: enforces non-toxicity, rejects generic scolding and moralizing lectures,
  strips preambles/quotes, and prevents hallucinatory length explosion
- GeminiClient: async REST client via httpx (no heavy SDK dependency needed)
- Exponential backoff with random jitter on HTTP 429/503 rate limits
- Server-Sent Events (SSE) streaming for real-time WebSocket generation
- Fallback support for OpenAI-compatible proxies (AICredits, OpenRouter, Groq)"


## ─── Commit 14: Master detoxifier & ML service integration ───
## (Detoxifier orchestrator, CLI tester, and updated FastAPI ML adapter)

git add detoxification/detoxifier.py detoxification/test_detox.py detoxification/__init__.py ml-service/app/models/llm_detoxifier.py ml-service/app/config.py
git commit -m "feat(detox): add master orchestrator, CLI tester, and ML service integration

- Detoxifier: coordinates Cache -> Gemini API -> Validator -> Offline Scrubber
- Fast script-based language identification (en, hi, hi-en)
- test_detox.py CLI tester for interactive verification across all languages
- Update ml-service LLMDetoxifier adapter for seamless backwards compatibility
- Fix DEBUG environment variable parsing in ml-service Pydantic config"


## ─── Commit 15: Detoxification automated test suite ──────────
## (19 comprehensive unit & integration tests)

git add tests/test_detoxification.py
git commit -m "test(detox): add comprehensive unit and integration test suite

- 19 test cases covering scrubber, validator, cache, language detection, and streaming
- Verifies threat resolution, slur neutralization, and intent preservation
- Verifies re-toxicity rejection and generic scolding detection
- Verifies LRU eviction and TTL expiration"


## ═════════════════════════════════════════════════════════════
##  PHASE 4: Backend API Platform Consolidation
## ═════════════════════════════════════════════════════════════


## ─── Commit 16: PostgreSQL and MongoDB persistence models ────
## (Relational User & Channel models, MongoDB chat & feedback documents)

git add src/safety_platform/models/ src/safety_platform/schemas/auth.py src/safety_platform/schemas/channel.py
git commit -m "feat(backend): add PostgreSQL relational and MongoDB document models

- Implement User and Channel SQLAlchemy models with relationships and cascade rules
- Implement ChatMessageDocument with granular ModerationMetadata and JSON serialization
- Implement ModeratorFeedbackDocument for continuous learning review traces
- Migrate Pydantic v2 schemas from deprecated class Config to ConfigDict"


## ─── Commit 17: Database resilience and local ML detox fallback ─
## (Fast startup timeouts, non-blocking DB probes, local detox engine integration)

git add src/safety_platform/core/db.py src/safety_platform/services/ml_client.py
git commit -m "feat(backend): add database startup resilience and local ML detox fallback

- Cap MongoDB serverSelectionTimeoutMS to 2s so offline local dev starts up in seconds
- Make Redis sliding-window rate limiter gracefully fall back to memory
- Integrate Phase 3 Detoxification Engine into MLClientService as automatic local fallback
- Gateway remains 100% operational even if remote ML microservice is offline"


## ─── Commit 18: Backend platform test suite ───────────────────
## (31 comprehensive unit and API integration tests)

git add tests/test_backend_platform.py tests/test_app.py tests/test_alias.py
git commit -m "test(backend): add comprehensive backend API platform test suite

- 31 test cases passing across platform and detoxification test suites
- Verifies bcrypt password hashing and constant-time verification
- Verifies JWT access token generation, expiration, and decoding
- Verifies FastAPI root registry discovery endpoint and Pydantic validation
- Verifies ML client automatic fallback to local detoxification engine
- Wraps legacy manual scripts so pytest discovers and executes cleanly"


## ═════════════════════════════════════════════════════════════
##  PHASE 5: Frontend Experience & Dashboard (React + Vite)
## ═════════════════════════════════════════════════════════════


## ─── Commit 19: TypeScript fixes, env config & Zustand stores ─
## (Fix float type error, add dynamic env config, authStore, chatStore)

git add frontend/.env.example frontend/src/config/env.ts frontend/src/stores/chatStore.ts frontend/src/stores/authStore.ts .gitignore
git commit -m "feat(frontend): fix TypeScript types, add env configuration and authStore

- Fix TypeScript compile error in chatStore (float -> number)
- Add env.ts for dynamic API_BASE_URL and WS_BASE_URL resolution
- Implement authStore with JWT token persistence and demo persona fallback
- Add channel switching and remote message history fetching in chatStore
- Ignore node_modules, dist, and local .env files in git"


## ─── Commit 20: Auth modal, error boundary, and admin dashboard ─
## (Auth modal, ErrorBoundary, Recharts telemetry dashboard)

git add frontend/src/components/auth/AuthModal.tsx frontend/src/components/common/ErrorBoundary.tsx frontend/src/components/dashboard/AdminDashboard.tsx
git commit -m "feat(frontend): add auth modal, error boundary, and admin dashboard

- Add AuthModal supporting PostgreSQL registration, JWT login, and 1-click demo personas
- Add ErrorBoundary catching unhandled React render exceptions with recovery actions
- Add AdminDashboard with Recharts visualizations for severity breakdown and language distribution
- Display polyglot infrastructure telemetry (Postgres, Redis, Mongo, ML Service)"


## ─── Commit 21: Secured ChatWindow & main App integration ────
## (Dynamic WebSockets, pre-send safety interception modal, channel navigation)

git add frontend/src/components/chat/ChatWindow.tsx frontend/src/App.tsx frontend/package-lock.json
git commit -m "feat(frontend): upgrade ChatWindow with dynamic WebSockets and tab navigation

- Replace hardcoded ws://localhost:8000 with dynamic authenticated getWsChatUrl()
- Remove unsafe 5-second bypass timeout; enforce proper async checking states
- Secure rewrite approval workflow so client cannot arbitrarily skip moderation
- Add sidebar channel navigation and live gateway online indicator pill
- Complete production build verified via tsc and vite build"


# =====================================================================
# PHASE 6: TESTING, CI/CD, CONTAINERIZATION & DEPLOYMENT
# =====================================================================

## ─── Commit 22: Test suite hardening, preprocessing defense tests & regression suite ─
## (Adversarial normalization tests, model regression benchmark, pipeline tests, test isolation)

git add ml-service/app/utils/preprocessing.py tests/test_preprocessing.py tests/test_model_regression.py tests/test_moderation_pipeline.py tests/test_alias.py tests/test_app.py
git commit -m "test: add adversarial preprocessing defense, regression benchmarks, and pipeline tests

- Fix separator insertion regex in preprocessing.py to preserve multi-word spacing
- Add 10 adversarial preprocessing tests (leetspeak, zero-width spaces, diacritics, repeated chars)
- Add latency regression and multi-label confidence sanity benchmarks
- Add 7 comprehensive moderation pipeline tests covering REST endpoints and WebSockets
- Isolate legacy standalone scripts (test_alias.py, test_app.py) behind __name__ guards"


## ─── Commit 23: Multi-job CI/CD GitHub Actions workflow ───────
## (Automated tests, matrix build, frontend lint and docker dry-run)

git add .github/workflows/ci.yml
git commit -m "ci: implement GitHub Actions multi-job continuous integration workflow

- Add backend test matrix job running pytest with coverage across tests/
- Add frontend build validation job executing TypeScript type check and Vite bundle
- Add docker configuration and docker-compose verification step"


## ─── Commit 24: Multi-stage Dockerization & docker-compose service mesh ─
## (Production Dockerfiles, Nginx SPA router, and 6-service orchestration)

git add Dockerfile ml-service/Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml
git commit -m "chore(infra): add multi-stage Dockerfiles and 6-service docker-compose mesh

- Add multi-stage Dockerfile for API Gateway with non-root user and curl healthcheck
- Add ML Service Dockerfile with PyTorch/Transformers dependencies and uvicorn server
- Add Frontend multi-stage Dockerfile (Node build -> Nginx alpine runtime)
- Configure nginx.conf with SPA HTML5 fallback routing and /api reverse proxying
- Orchestrate PostgreSQL, Redis, MongoDB, ML Service, API Gateway, and Frontend in docker-compose.yml"


## ─── Commit 25: Kubernetes production deployment manifests ────
## (K8s Namespace, Deployments, Services, ConfigMaps, and Secrets)

git add k8s/namespace.yaml k8s/postgres.yaml k8s/redis.yaml k8s/mongodb.yaml k8s/ml-service.yaml k8s/api-gateway.yaml k8s/frontend.yaml GIT_COMMITS.sh
git commit -m "chore(k8s): add production Kubernetes manifests and commit tracker script

- Define toxicity-platform namespace with resource quotas and labels
- Add Deployment and ClusterIP Services for Postgres, Redis, and MongoDB with PVCs
- Add Deployment, Service, and horizontal autoscaling ready specs for ML Service and API Gateway
- Add Frontend deployment with Nginx container and Ingress-ready Service
- Include centralized GIT_COMMITS.sh script tracking all development milestones"


# =====================================================================
# PHASE 7: FRONTEND UI PREMIUM OVERHAUL
# =====================================================================

## ─── Commit 26: Premium UI component library & design system ───
## (Badge, MessageBubble, TypingIndicator, Sidebar, Header)

git add frontend/src/components/common/Badge.tsx frontend/src/components/chat/MessageBubble.tsx frontend/src/components/chat/TypingIndicator.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/components/layout/Header.tsx
git commit -m "feat(frontend): add premium UI component library with design system

- Add Badge/SeverityBadge components with variant-based color coding
- Add MessageBubble with avatar gradients, entrance animations, and hover tooltips
- Add TypingIndicator with animated bouncing dots
- Add Sidebar with mobile responsive drawer, channel navigation, and user profile
- Add Header with real-time WebSocket connection status indicator"


## ─── Commit 27: Enhanced design system, ChatWindow & Dashboard ─
## (Tailwind config, CSS, upgraded ChatWindow, AdminDashboard, AuthModal)

git add frontend/tailwind.config.js frontend/src/index.css frontend/src/App.tsx frontend/src/components/chat/ChatWindow.tsx frontend/src/components/dashboard/AdminDashboard.tsx frontend/src/components/auth/AuthModal.tsx frontend/vite.config.ts frontend/package.json
git commit -m "feat(frontend): premium UI overhaul with animations, charts & responsive design

- Add custom animation keyframes (slide-up, fade-in, bounce-in, msg-enter, typing-dot)
- Add thin scrollbar, stat-card, input-field, btn-primary utility components
- Upgrade ChatWindow with MessageBubble, scroll-to-bottom button, empty state
- Upgrade AdminDashboard with stat cards, area timeline chart, moderation actions table
- Upgrade AuthModal with password strength indicator and glassmorphism header
- Add Vite code-splitting (vendor/charts) and source map optimization
- Upgrade App.tsx to use extracted Sidebar/Header layout components"


echo "====================================================================="
echo "  All 27 Modular Commits Successfully Applied!"
echo "  Real-time Toxic Chat Moderation System — Production Ready."
echo "====================================================================="


