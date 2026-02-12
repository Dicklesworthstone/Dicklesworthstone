# Jeffrey Emanuel

**New York** · Builder & engineer · Former long/short equity analyst

![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white)
![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white)
![Next.js](https://img.shields.io/badge/-Next.js-000000?style=flat-square&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/-React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Three.js](https://img.shields.io/badge/-Three.js-000000?style=flat-square&logo=three.js&logoColor=white)
![Claude](https://img.shields.io/badge/-Claude-191919?style=flat-square&logo=anthropic&logoColor=white)
![Bash](https://img.shields.io/badge/-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white)
![SQLite](https://img.shields.io/badge/-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)

> Building the tools that sit between markets and frontier AI.

**16,700+ GitHub stars** across **90+ open-source projects** · **1,700+ followers** · **29K on X** · **152 public repos**

🌐 [jeffreyemanuel.com](https://www.jeffreyemanuel.com) · 📝 [jeffreysprompts.com](https://jeffreysprompts.com) · ⚡ [agent-flywheel.com](https://agent-flywheel.com) · 🔬 [brennerbot.org](https://brennerbot.org)

<p align="center">
  <img src="https://github-profile-trophy.vercel.app/?username=Dicklesworthstone&theme=darkhub&no-frame=true&row=1&column=7" alt="GitHub Trophies" />
</p>

<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=Dicklesworthstone&show_icons=true&theme=tokyonight&hide_border=true&bg_color=0d1117&count_private=false" width="49%" alt="GitHub Stats" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=Dicklesworthstone&layout=compact&theme=tokyonight&hide_border=true&bg_color=0d1117&langs_count=10" width="49%" alt="Top Languages" />
</p>

---

## The Agentic Coding Flywheel

A self-reinforcing ecosystem of 14 tools for multi-agent software development. Agents coordinate via mail, track work via beads, search past sessions, guard against destructive mistakes, and orchestrate across tmux panes. Each tool amplifies the others. The whole thing started in October 2025 and the shipping cadence accelerates with every addition.

```mermaid
graph TD
    subgraph orchestration["Orchestration"]
        NTM["NTM<br/>Tmux Orchestrator"]
        ACFS["Flywheel Setup<br/>Zero-to-VPS"]
    end

    subgraph coordination["Coordination"]
        MAIL["Agent Mail<br/>1,677★"]
        SLB["SLB<br/>Two-Person Rule"]
    end

    subgraph knowledge["Knowledge"]
        CASS["CASS<br/>Session Search"]
        CM["CASS Memory<br/>3-Layer Memory"]
        MS["Meta Skill<br/>Skill Platform"]
        XF["XF<br/>X Archive Search"]
    end

    subgraph tasks["Task Management"]
        BV["Beads Viewer<br/>1,242★"]
        BR["Beads Rust<br/>Issue Tracker"]
    end

    subgraph safety["Safety"]
        DCG["DCG<br/>Command Guard"]
        UBS["UBS<br/>Bug Scanner"]
    end

    subgraph utility["Utility"]
        RU["RU<br/>Repo Updater"]
        GIIL["GIIL<br/>Image Downloader"]
    end

    MAIL <--> NTM
    MAIL <--> BV
    MAIL <--> CASS
    MAIL <--> CM
    MAIL <--> SLB

    NTM <--> CASS
    NTM <--> BV
    NTM <--> DCG
    NTM <--> RU

    CASS <--> CM
    CASS <--> MS
    CASS <--> XF

    BV <--> UBS
    BV <--> MS
    BR <--> BV

    DCG <--> SLB
    UBS <--> SLB

    ACFS -.->|installs| NTM
    ACFS -.->|installs| MAIL
    ACFS -.->|installs| DCG
```

| Tool | Stars | Lang | Purpose |
|:-----|------:|:-----|:--------|
| [**MCP Agent Mail**](https://github.com/Dicklesworthstone/mcp_agent_mail) | 1,677 | Python | Gmail for coding agents: messaging, file leases, audit trails |
| [**Beads Viewer**](https://github.com/Dicklesworthstone/beads_viewer) | 1,242 | Go | PageRank-powered task prioritization in a keyboard-driven TUI |
| [**Flywheel Setup**](https://github.com/Dicklesworthstone/agentic_coding_flywheel_setup) | 1,042 | Bash | Zero to fully-configured agentic VPS in 30 minutes |
| [**Beads Rust**](https://github.com/Dicklesworthstone/beads_rust) | 515 | Rust | Local-first, non-invasive issue tracker for git repos |
| [**DCG**](https://github.com/Dicklesworthstone/destructive_command_guard) | 507 | Rust | SIMD-accelerated guard that blocks `rm -rf` and `git reset --hard` |
| [**CASS**](https://github.com/Dicklesworthstone/coding_agent_session_search) | 454 | Rust | Unified search across 11+ AI coding tool histories |
| [**CASS Memory**](https://github.com/Dicklesworthstone/cass_memory_system) | 216 | TS | Three-layer cognitive memory: episodic, working, procedural |
| [**UBS**](https://github.com/Dicklesworthstone/ultimate_bug_scanner) | 158 | Bash | 1,000+ pattern-based bug scanner, runs before every commit |
| [**NTM**](https://github.com/Dicklesworthstone/ntm) | 139 | Go | Multi-agent tmux orchestration with animated dashboards |
| [**Meta Skill**](https://github.com/Dicklesworthstone/meta_skill) | 108 | Rust | Skill management platform with CASS mining and MCP server |
| [**XF**](https://github.com/Dicklesworthstone/xf) | 69 | Rust | Sub-millisecond search over X/Twitter data archives |
| [**SLB**](https://github.com/Dicklesworthstone/slb) | 56 | Go | Two-person rule: peer approval before dangerous commands |
| [**RU**](https://github.com/Dicklesworthstone/repo_updater) | 51 | Bash | Keep hundreds of Git repos in sync with one command |
| [**GIIL**](https://github.com/Dicklesworthstone/giil) | 28 | Bash | Download full-res images from iCloud/Dropbox share links |

### Quick Install

**Full ecosystem** (Ubuntu VPS, 30 minutes):

```bash
curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/agentic_coding_flywheel_setup/main/install.sh" | bash -s -- --yes --mode vibe
```

**Individual Rust tools** via Cargo:

```bash
cargo install coding-agent-search      # cass — unified session search
cargo install destructive_command_guard # dcg  — command safety guard
cargo install beads_rust               # br   — issue tracker
cargo install xf                       # xf   — X/Twitter archive search
```

### Agent Mail in Action

<p align="center">
  <img src="https://raw.githubusercontent.com/Dicklesworthstone/mcp_agent_mail/main/screenshots/output/agent_mail_showcase.gif" alt="Agent Mail — agents coordinating via threaded messages, file leases, and audit trails" width="800" />
</p>

---

## What I'm Building Now

| Project | Lang | What it does |
|:--------|:-----|:-------------|
| [**FrankenSQLite**](https://github.com/Dicklesworthstone/frankensqlite) | Rust | Clean-room SQLite reimplementation with MVCC page-level versioning and RaptorQ erasure codes |
| [**FrankenTUI**](https://github.com/Dicklesworthstone/frankentui) | Rust | Minimal, deterministic terminal UI kernel — the rendering layer for CASS, Beads Viewer, and NTM |
| [**FrankenTerm**](https://github.com/Dicklesworthstone/frankenterm) | Rust | Terminal hypervisor for AI agent swarms: pattern detection, event automation, multiplexed I/O |
| [**Bio-Inspired Nanochat**](https://github.com/Dicklesworthstone/bio_inspired_nanochat) | Python | What if a Transformer had a metabolism? Living weights with synaptic fatigue and structural plasticity |
| [**SmartEdgar**](https://github.com/Dicklesworthstone/smartedgar) | Python | SEC filing ingestion, entity resolution, and research stack with an MCP server at its core |

---

## Open Source Highlights

### AI & LLM Tools

- 📄 **[LLM-Aided OCR](https://github.com/Dicklesworthstone/llm_aided_ocr)** `2,862★` — Tesseract + language models = perfect PDFs. Corrects OCR errors that regex rules never catch.
- 🦙 **[Swiss Army Llama](https://github.com/Dicklesworthstone/swiss_army_llama)** `1,044★` — High-performance FastAPI service for local LLM inference and semantic search.
- 📋 **[Your Source to Prompt](https://github.com/Dicklesworthstone/your-source-to-prompt.html)** `738★` — Secure, browser-based tool that turns codebases into optimized LLM prompts.
- 🎥 **[Bulk YouTube Transcriber](https://github.com/Dicklesworthstone/bulk_transcribe_youtube_videos_from_playlist)** `648★` — Convert entire playlists into structured, searchable text with Whisper.
- 🤖 **[Claude Code Agent Farm](https://github.com/Dicklesworthstone/claude_code_agent_farm)** `647★` — Orchestrate parallel Claude Code agents to autonomously improve codebases across 34 tech stacks.
- 🧠 **[Mindmap Generator](https://github.com/Dicklesworthstone/mindmap-generator)** `198★` — Distills documents into hierarchical, context-aware mindmaps using non-linear exploration.
- 🔗 **[Ultimate MCP Client](https://github.com/Dicklesworthstone/ultimate_mcp_client)** `146★` — Universal bridge for AI models to interact with the real world via MCP.
- 🔌 **[Ultimate MCP Server](https://github.com/Dicklesworthstone/ultimate_mcp_server)** `138★` — Unified MCP server exposing dozens of tools to frontier models.
- 🌐 **[Markdown Web Browser](https://github.com/Dicklesworthstone/markdown_web_browser)** `120★` — Headless browser that renders modern JavaScript-heavy sites into clean Markdown for agents.

### Systems & Rust

- ⚡ **[Fast Vector Similarity](https://github.com/Dicklesworthstone/fast_vector_similarity)** `426★` — High-speed Rust library for complex vector similarity metrics with Python bindings.
- 🔬 **[FrankenTUI](https://github.com/Dicklesworthstone/frankentui)** `134★` — Minimal, high-performance terminal UI kernel. The rendering substrate for CASS, Beads Viewer, and NTM.
- 🗄️ **[FrankenSQLite](https://github.com/Dicklesworthstone/frankensqlite)** `32★` — Clean-room Rust reimplementation of SQLite with MVCC page-level versioning and RaptorQ erasure codes.
- 🖥️ **[FrankenTerm](https://github.com/Dicklesworthstone/frankenterm)** `32★` — Terminal hypervisor for AI agent swarms with pattern detection and event-driven automation.
- 🦀 **[Fast CMA-ES](https://github.com/Dicklesworthstone/fast_cmaes)** — SIMD-accelerated, Rayon-parallelized evolution strategy optimizer in Rust.
- 🦎 **[Rust ScriptBots](https://github.com/Dicklesworthstone/rust_scriptbots)** — Deterministic, GPU-accelerated artificial life simulator. Modern Rust reimplementation of Karpathy's ScriptBots.
- 🔍 **[UltraSearch](https://github.com/Dicklesworthstone/ultrasearch)** — Instant file search engine for Windows using NTFS USN journals and Tantivy. A modern "Everything" in Rust.

### Research & Science

- 🧬 **[Bio-Inspired Nanochat](https://github.com/Dicklesworthstone/bio_inspired_nanochat)** — What if a Transformer had a metabolism? Living weights with synaptic fatigue and structural plasticity.
- 🔢 **[Model-Guided Research](https://github.com/Dicklesworthstone/model_guided_research)** `94★` — 11 exotic math frameworks for AI (Lie group attention, p-adic spaces, tropical geometry), designed by GPT-5.
- 🛡️ **[ACIP](https://github.com/Dicklesworthstone/acip)** `247★` — AI Cognitive Inoculation Protocol: defense against prompt injection via external monitoring.
- 🔬 **[Brenner Bot](https://github.com/Dicklesworthstone/brenner_bot)** `51★` — Multi-agent research system embodying Sydney Brenner's scientific methodology.
- 🧮 **[LLM Introspective Compression](https://www.jeffreyemanuel.com/writing/llm_introspective_compression)** `30★` — Treating LLM context as a save state: reasoning backtracking and metacognitive control.
- 🦠 **[Phage Explorer](https://github.com/Dicklesworthstone/phage_explorer)** `22★` — Interactive educational site exploring bacteriophages with 3D visualization.

### Developer Tools

- 📊 **[SQLAlchemy Visualizer](https://github.com/Dicklesworthstone/sqlalchemy_data_model_visualizer)** `285★` — Instantly turn SQLAlchemy ORM models into interactive SVG diagrams.
- 📝 **[Automatic Log Collector](https://github.com/Dicklesworthstone/automatic_log_collector_and_analyzer)** `423★` — Open-source Splunk alternative for multi-server log aggregation and analysis.
- 💡 **[Coding Agent Tips](https://github.com/Dicklesworthstone/misc_coding_agent_tips_and_scripts)** `196★` — Battle-tested solutions for AI coding agent workflows and terminal setup.
- 📦 **[Coding Agent Account Manager](https://github.com/Dicklesworthstone/coding_agent_account_manager)** `51★` — Sub-100ms auth switching across Claude Max, GPT Pro, and Gemini subscriptions.
- 🔄 **[Flywheel Connectors](https://github.com/Dicklesworthstone/flywheel_connectors)** `29★` — Secure integration adapters for external services in the Flywheel ecosystem.
- 🏗️ **[Pi Agent Rust](https://github.com/Dicklesworthstone/pi_agent_rust)** `40★` — High-performance AI coding agent CLI with sub-100ms startup and native SSE streaming.
- ☁️ **[Cloud Benchmarker](https://github.com/Dicklesworthstone/cloud_benchmarker)** `37★` — Automated cloud instance benchmarking with charts and historical tracking.

### Education & Visualization

- 🌀 **[Visual A* Pathfinding](https://github.com/Dicklesworthstone/visual_astar_python)** `176★` — Cinematic, animated visualizations of pathfinding algorithms in action.
- ⏱️ **[Introduction to Temporal Logic](https://www.jeffreyemanuel.com/writing/introduction_to_temporal_logic)** `108★` — How temporal logic can be used to analyze concurrency.
- 📐 **[Hoeffding's D Explainer](https://www.jeffreyemanuel.com/writing/hoeffdings_d_explainer)** `100★` — The non-parametric dependency measure that catches what Pearson and Spearman miss.
- 🍞 **[Lamport's Bakery Algorithm](https://www.jeffreyemanuel.com/writing/bakery_algorithm)** `95★` — Visual Pythonic implementation of fair mutual exclusion without atomic hardware.
- 🧮 **[CMA-ES Explainer](https://www.jeffreyemanuel.com/writing/cmaes_explainer)** — Interactive deep dive into the evolution strategy that works where gradient descent fails.
- 🏰 **[Kissinger Thesis Reader](https://github.com/Dicklesworthstone/kissinger_undergraduate_thesis)** `47★` — A reader for Henry Kissinger's 400-page undergraduate thesis on the meaning of history.

### More Projects

- 📰 **[Next.js GitHub Blog](https://github.com/Dicklesworthstone/nextjs-github-markdown-blog)** `89★` — Blogging platform that uses GitHub as a headless CMS
- 📝 **[JeffreysPrompts.com](https://github.com/Dicklesworthstone/jeffreysprompts.com)** `69★` — Curated prompt library for agentic coding workflows
- 📚 **[LLM Docs](https://github.com/Dicklesworthstone/llm-docs)** `64★` — Documentation optimized for LLM consumption
- 📐 **[Grassmann Article](https://www.jeffreyemanuel.com/writing/hermann_grassmann_nature_of_abstractions)** `54★` — The story of the self-taught genius who invented linear algebra decades early
- 🏆 **[LLM Tournament](https://www.jeffreyemanuel.com/writing/llm_multi_round_coding_tournament)** `47★` — Arena where LLMs compete and iterate on coding challenges via peer review
- 🧩 **[Clawdbot Skills](https://github.com/Dicklesworthstone/agent_flywheel_clawdbot_skills_and_integrations)** `43★` — Modular skill library teaching agents to use the Flywheel toolkit
- 🔁 **[Automated Plan Reviser](https://github.com/Dicklesworthstone/automated_plan_reviser_pro)** `42★` — Iterative specification refinement using extended reasoning models
- 🗣️ **[The Lighthill Debate on AI](https://www.jeffreyemanuel.com/writing/the_lighthill_debate_on_ai)** `34★` — Full transcript of the 1973 debate that nearly killed British AI research
- 🎬 **[YouTube Transcript Cleaner](https://github.com/Dicklesworthstone/youtube_transcript_cleaner)** `27★` — Clean up raw YouTube auto-captions into readable text
- 📡 **[Remote Compilation Helper](https://github.com/Dicklesworthstone/remote_compilation_helper)** `27★` — Transparent build offloading for AI agents via Claude Code hooks
- 🛡️ **[System Resource Protection](https://github.com/Dicklesworthstone/system_resource_protection_script)** `25★` — Intelligent resource guardrails that prevent dev tools from freezing your Linux desktop
- 🔄 **[ASupersync](https://github.com/Dicklesworthstone/asupersync)** `23★` — Spec-first, cancel-correct, capability-secure async runtime for Rust
- 💡 **[Anti-Alzheimer's Flasher](https://github.com/Dicklesworthstone/anti_alzheimers_flasher)** `23★` — Web-based 40Hz neural stimulation tool
- 💬 **[Chat to File](https://github.com/Dicklesworthstone/chat_shared_conversation_to_file)** `22★` — Convert ChatGPT, Gemini, and Grok share links to clean Markdown
- 🦠 **[Phage Explorer](https://github.com/Dicklesworthstone/phage_explorer)** `22★` — Interactive bacteriophage education with 3D visualization
- 📦 **[PrepareProjectForLLMPrompt](https://github.com/Dicklesworthstone/prepareprojectforllmprompt)** `22★` — Flatten a codebase into a single LLM-ready prompt

---

## The Nvidia Short Thesis

In January 2025, I published a [12,000-word analysis](https://www.jeffreyemanuel.com/writing/the_short_case_for_nvda) arguing that DeepSeek and the economics of AI inference would collide with Nvidia's valuation narrative. Within days, roughly $600 billion in market cap evaporated.

> "Come for the trade, stay for the dazzling 60-minute education on the state of AI."
> — **Naval Ravikant**, founder of AngelList

> "A candidate for the most impactful short research report ever written."
> — **Matt Levine**, Bloomberg Opinion

> "Long, excellent... Jeffrey has a rare combination of experience in both computer science and investment analysis."
> — **Simon Willison**, creator of Datasette

Featured on Slashdot, Hacker News front page, and the Bankless podcast. Picked up by analysts and fund managers worldwide.

---

## Writing

Selected essays from [jeffreyemanuel.com/writing](https://www.jeffreyemanuel.com/writing):

- **[RaptorQ: The Black Magic of Liquid Data](https://www.jeffreyemanuel.com/writing/raptorq)** — Deep dive into the fountain code that turns any file into an infinite stream of interchangeable packets
- **[The Short Case for Nvidia Stock](https://www.jeffreyemanuel.com/writing/the_short_case_for_nvda)** — How AI economics, DeepSeek, and GPU supply collide with valuation narratives
- **[The Most Impressive Prediction of All Time](https://www.jeffreyemanuel.com/writing/the_most_impressive_prediction_of_all_time)** — Pyotr Durnovo's 1914 memo that predicted WWI, its alliances, and the Russian Revolution
- **[The Lessons of Hermann Grassmann](https://www.jeffreyemanuel.com/writing/hermann_grassmann_nature_of_abstractions)** — The self-taught genius who invented linear algebra decades before it was understood
- **[Factor Risk Models and the Hedge Fund Business](https://www.jeffreyemanuel.com/writing/barra_factor_model_article)** — How "smart" risk models distort incentives and create hidden systemic risk
- **[PPP Loan Fraud: A Data Science Detective Story](https://www.jeffreyemanuel.com/writing/ppp_loan_fraud_analysis)** — Network analysis that could have caught billions in theft
- **[Making Complex Code Changes with Claude Code](https://www.jeffreyemanuel.com/writing/making_complex_code_changes_with_cc)** — Separating cognition: use agents for plans first, code second
- **[Some Thoughts on AI Alignment](https://www.jeffreyemanuel.com/writing/some_thoughts_on_ai_alignment)** — Why internal alignment fails and AI needs an external criminal justice system

---

## GitHub Activity

![GitHub Contribution Graph](https://ghchart.rshah.org/Dicklesworthstone)

<p align="center">
  <a href="https://star-history.com/#Dicklesworthstone/mcp_agent_mail&Dicklesworthstone/llm_aided_ocr&Dicklesworthstone/beads_viewer&Dicklesworthstone/agentic_coding_flywheel_setup&Dicklesworthstone/swiss_army_llama&Date">
    <img src="https://api.star-history.com/svg?repos=Dicklesworthstone/mcp_agent_mail,Dicklesworthstone/llm_aided_ocr,Dicklesworthstone/beads_viewer,Dicklesworthstone/agentic_coding_flywheel_setup,Dicklesworthstone/swiss_army_llama&type=Date&theme=dark" alt="Star History Chart" width="800" />
  </a>
</p>

---

## Products

- 📈 **[SmartEdgar](https://github.com/Dicklesworthstone/smartedgar)** — Modern SEC filing ingestion and research stack with an MCP server at its core
- 🌐 **[jeffreyemanuel.com](https://www.jeffreyemanuel.com)** — Personal site built with Next.js 16, React Three Fiber, and GSAP. 70 components, 3D WebGL hero, 21 essays, 90+ project showcase.
- 📝 **[JeffreysPrompts.com](https://jeffreysprompts.com)** — Battle-tested prompts for AI coding agents. Browse, copy, or install as Claude Code skills.
- ⚡ **[Agent-Flywheel.com](https://agent-flywheel.com)** — Interactive setup wizard for the complete Flywheel ecosystem
- 🔬 **[BrennerBot.org](https://brennerbot.org)** — Multi-agent research orchestration using Sydney Brenner's scientific methods

---

## Connect

[![X](https://img.shields.io/badge/-@doodlestein-000000?style=flat-square&logo=x&logoColor=white)](https://x.com/doodlestein)
[![GitHub](https://img.shields.io/badge/-Follow-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/Dicklesworthstone)
[![LinkedIn](https://img.shields.io/badge/-Jeffrey_Emanuel-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/jeffreyemanuel)
[![Website](https://img.shields.io/badge/-jeffreyemanuel.com-FF5722?style=flat-square&logo=google-chrome&logoColor=white)](https://www.jeffreyemanuel.com)
[![Email](https://img.shields.io/badge/-jeffreyemanuel@gmail.com-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:jeffreyemanuel@gmail.com)

---

## Background

- Spent a decade as a long/short equity analyst at hedge funds in New York
- Building with deep learning since 2010, multi-agent systems since 2023
- Consult to PE firms and hedge funds on AI automation strategy
- The Flywheel ecosystem started in October 2025 and each tool accelerates the creation of the next
