<div align="center">

# Jeffrey Emanuel

<img src="je_headshot.webp" alt="Jeffrey Emanuel" width="180" />

**New York** · Builder & engineer · Former long/short equity analyst

![Rust](https://img.shields.io/badge/-Rust-2b2b2b?style=flat-square&logo=rust&logoColor=dea584)
![TypeScript](https://img.shields.io/badge/-TypeScript-2b2b2b?style=flat-square&logo=typescript&logoColor=3178C6)
![Python](https://img.shields.io/badge/-Python-2b2b2b?style=flat-square&logo=python&logoColor=3776AB)
![Go](https://img.shields.io/badge/-Go-2b2b2b?style=flat-square&logo=go&logoColor=00ADD8)
![Next.js](https://img.shields.io/badge/-Next.js-2b2b2b?style=flat-square&logo=next.js&logoColor=white)
![React](https://img.shields.io/badge/-React-2b2b2b?style=flat-square&logo=react&logoColor=61DAFB)
![Three.js](https://img.shields.io/badge/-Three.js-2b2b2b?style=flat-square&logo=three.js&logoColor=white)
![Claude](https://img.shields.io/badge/-Claude-2b2b2b?style=flat-square&logo=anthropic&logoColor=d4a27f)
![Bash](https://img.shields.io/badge/-Bash-2b2b2b?style=flat-square&logo=gnu-bash&logoColor=4EAA25)
![SQLite](https://img.shields.io/badge/-SQLite-2b2b2b?style=flat-square&logo=sqlite&logoColor=63b4f4)

*Building the tooling that lets dozens of AI agents ship complex projects in days.*

![Stars](https://img.shields.io/badge/Stars-16.7k+-2b2b2b?style=flat-square&logo=github&logoColor=white)
![Repos](https://img.shields.io/badge/Projects-90+-2b2b2b?style=flat-square&logo=github&logoColor=white)
![Followers](https://img.shields.io/badge/Followers-1.7k+-2b2b2b?style=flat-square&logo=github&logoColor=white)
![X](https://img.shields.io/badge/𝕏_Followers-29k-2b2b2b?style=flat-square&logo=x&logoColor=white)

[![Website](https://img.shields.io/badge/jeffreyemanuel.com-2b2b2b?style=flat-square&logo=google-chrome&logoColor=white)](https://www.jeffreyemanuel.com)
[![Prompts](https://img.shields.io/badge/jeffreysprompts.com-2b2b2b?style=flat-square&logo=bookstack&logoColor=white)](https://jeffreysprompts.com)
[![Flywheel](https://img.shields.io/badge/agent--flywheel.com-2b2b2b?style=flat-square&logo=atom&logoColor=white)](https://agent-flywheel.com)
[![Brenner](https://img.shields.io/badge/brennerbot.org-2b2b2b?style=flat-square&logo=microscope&logoColor=white)](https://brennerbot.org)
[![FrankenTUI](https://img.shields.io/badge/frankentui.com-2b2b2b?style=flat-square&logo=terminal&logoColor=white)](https://frankentui.com)

`Multi-Agent Coordination` · `Agentic Coding` · `Rust CLI Tools` · `LLM Applications` · `Terminal UI`

</div>

<p align="center">
<a href="#the-agentic-coding-flywheel">Flywheel</a> · <a href="#what-im-building-now">Building Now</a> · <a href="#open-source-highlights">Open Source</a> · <a href="#the-nvidia-short-thesis">Nvidia Thesis</a> · <a href="#writing">Writing</a> · <a href="#products">Products</a> · <a href="#philosophy">Philosophy</a> · <a href="#connect">Connect</a>
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="stats-light.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="stats.svg" />
    <img src="stats.svg" width="49%" alt="GitHub Stats" />
  </picture>
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="languages-light.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="languages.svg" />
    <img src="languages.svg" width="49%" alt="Top Languages" />
  </picture>
</p>

---

## The Agentic Coding Flywheel

A self-reinforcing ecosystem of 14 tools for multi-agent software development. Agents coordinate via mail, track work via beads, search past sessions, guard against destructive mistakes, and orchestrate across tmux panes. Each tool amplifies the others. The whole thing started in October 2025 and the shipping cadence accelerates with every addition.

<p align="center">
  <img src="flywheel_diagram.webp" alt="The Agentic Coding Flywheel — 14 interconnected tools for multi-agent development" width="800" />
</p>

| Tool | Stars | Lang | Purpose |
|:-----|:-----:|:----:|:--------|
| [**MCP Agent Mail**](https://github.com/Dicklesworthstone/mcp_agent_mail) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/mcp_agent_mail?style=flat-square&label=⭐) | ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | Gmail for coding agents: messaging, file leases, audit trails |
| [**Beads Viewer**](https://github.com/Dicklesworthstone/beads_viewer) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/beads_viewer?style=flat-square&label=⭐) | ![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white) | PageRank-powered task prioritization in a keyboard-driven TUI |
| [**Flywheel Setup**](https://github.com/Dicklesworthstone/agentic_coding_flywheel_setup) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/agentic_coding_flywheel_setup?style=flat-square&label=⭐) | ![Bash](https://img.shields.io/badge/-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white) | Zero to fully-configured agentic VPS in 30 minutes |
| [**Beads Rust**](https://github.com/Dicklesworthstone/beads_rust) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/beads_rust?style=flat-square&label=⭐) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Local-first, non-invasive issue tracker for git repos |
| [**DCG**](https://github.com/Dicklesworthstone/destructive_command_guard) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/destructive_command_guard?style=flat-square&label=⭐) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | SIMD-accelerated guard that blocks `rm -rf` and `git reset --hard` |
| [**CASS**](https://github.com/Dicklesworthstone/coding_agent_session_search) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/coding_agent_session_search?style=flat-square&label=⭐) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Unified search across 11+ AI coding tool histories |
| [**CASS Memory**](https://github.com/Dicklesworthstone/cass_memory_system) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/cass_memory_system?style=flat-square&label=⭐) | ![TypeScript](https://img.shields.io/badge/-TS-3178C6?style=flat-square&logo=typescript&logoColor=white) | Three-layer cognitive memory: episodic, working, procedural |
| [**UBS**](https://github.com/Dicklesworthstone/ultimate_bug_scanner) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/ultimate_bug_scanner?style=flat-square&label=⭐) | ![Bash](https://img.shields.io/badge/-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white) | 1,000+ pattern-based bug scanner, runs before every commit |
| [**NTM**](https://github.com/Dicklesworthstone/ntm) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/ntm?style=flat-square&label=⭐) | ![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white) | Multi-agent tmux orchestration with animated dashboards |
| [**Meta Skill**](https://github.com/Dicklesworthstone/meta_skill) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/meta_skill?style=flat-square&label=⭐) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Skill management platform with CASS mining and MCP server |
| [**XF**](https://github.com/Dicklesworthstone/xf) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/xf?style=flat-square&label=⭐) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Sub-millisecond search over X/Twitter data archives |
| [**SLB**](https://github.com/Dicklesworthstone/slb) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/slb?style=flat-square&label=⭐) | ![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white) | Two-person rule: peer approval before dangerous commands |
| [**RU**](https://github.com/Dicklesworthstone/repo_updater) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/repo_updater?style=flat-square&label=⭐) | ![Bash](https://img.shields.io/badge/-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white) | Keep hundreds of Git repos in sync with one command |
| [**GIIL**](https://github.com/Dicklesworthstone/giil) | ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/giil?style=flat-square&label=⭐) | ![Bash](https://img.shields.io/badge/-Bash-4EAA25?style=flat-square&logo=gnu-bash&logoColor=white) | Download full-res images from iCloud/Dropbox share links |

### Quick Install

> [!TIP]
> **Full ecosystem** (Ubuntu VPS):
> ```bash
> curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/agentic_coding_flywheel_setup/main/install.sh" | bash -s -- --yes --mode vibe
> ```
> **Individual Rust tools** via Cargo:
> ```bash
> cargo install xf  # xf — X/Twitter archive search
> ```
> Other Flywheel tools (CASS, DCG, Beads Rust) install from source via the Flywheel Setup script or `cargo install --git`.

### Agent Mail in Action

<p align="center">
  <img src="https://raw.githubusercontent.com/Dicklesworthstone/mcp_agent_mail/main/screenshots/output/agent_mail_showcase.gif" alt="Agent Mail — agents coordinating via threaded messages, file leases, and audit trails" width="800" />
</p>

---

## What I'm Building Now

| Project | Lang | What it does |
|:--------|:----:|:-------------|
| [**FrankenSQLite**](https://github.com/Dicklesworthstone/frankensqlite) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Clean-room SQLite reimplementation with MVCC page-level versioning and RaptorQ erasure codes |
| [**FrankenTUI**](https://github.com/Dicklesworthstone/frankentui) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Minimal, deterministic terminal UI kernel — the rendering layer for CASS and other Rust TUI tools |
| [**FrankenTerm**](https://github.com/Dicklesworthstone/frankenterm) | ![Rust](https://img.shields.io/badge/-Rust-000000?style=flat-square&logo=rust&logoColor=white) | Terminal hypervisor for AI agent swarms: pattern detection, event automation, multiplexed I/O |
| [**Bio-Inspired Nanochat**](https://github.com/Dicklesworthstone/bio_inspired_nanochat) | ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | What if a Transformer had a metabolism? Living weights with synaptic fatigue and structural plasticity |

### Live Demos

<table>
<tr>
<td align="center" width="33%">
<a href="https://frankentui.com/web"><img src="https://frankentui.com/web/og.png" alt="FrankenTUI Web Demo" width="100%" /></a><br/>
<a href="https://frankentui.com/web"><strong>FrankenTUI — Web Demo</strong></a><br/>
<sub>Pure TypeScript terminal UI running in the browser</sub>
</td>
<td align="center" width="33%">
<a href="https://frankentui.com/web_react"><img src="https://frankentui.com/web_react/opengraph-image?5478ac34bb117957" alt="FrankenTUI React Demo" width="100%" /></a><br/>
<a href="https://frankentui.com/web_react"><strong>FrankenTUI — React Demo</strong></a><br/>
<sub>React component wrapper for FrankenTUI widgets</sub>
</td>
<td align="center" width="33%">
<a href="https://frankensqlite.com/"><img src="https://frankensqlite.com/og-image.png" alt="FrankenSQLite" width="100%" /></a><br/>
<a href="https://frankensqlite.com/"><strong>FrankenSQLite</strong></a><br/>
<sub>Interactive docs for the Rust SQLite reimplementation</sub>
</td>
</tr>
<tr>
<td align="center" width="33%">
<a href="https://agent-flywheel.com"><img src="https://agent-flywheel.com/opengraph-image?de905a94719d4144" alt="Agent Flywheel" width="100%" /></a><br/>
<a href="https://agent-flywheel.com"><strong>Agent Flywheel</strong></a><br/>
<sub>Interactive setup wizard for the complete Flywheel ecosystem</sub>
</td>
<td align="center" width="33%">
<a href="https://brennerbot.org"><img src="https://brennerbot.org/opengraph-image?a523997cd907b722" alt="Brenner Bot" width="100%" /></a><br/>
<a href="https://brennerbot.org"><strong>Brenner Bot</strong></a><br/>
<sub>Multi-agent research orchestration using Sydney Brenner's methods</sub>
</td>
<td align="center" width="33%">
<a href="https://jeffreyemanuel.com/tldr"><img src="https://jeffreyemanuel.com/tldr/opengraph-image?6394e3001be2769b" alt="Jeffrey Emanuel — TL;DR" width="100%" /></a><br/>
<a href="https://jeffreyemanuel.com/tldr"><strong>jeffreyemanuel.com/tldr</strong></a><br/>
<sub>The short version of everything I'm working on</sub>
</td>
</tr>
</table>

---

## Open Source Highlights

### AI & LLM Tools

| | Project | Description |
|:--|:--|:--|
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/llm_aided_ocr?style=flat-square&label=⭐&color=2b2b2b) | **[LLM-Aided OCR](https://github.com/Dicklesworthstone/llm_aided_ocr)** | Tesseract + language models = perfect PDFs. Corrects OCR errors that regex rules never catch. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/swiss_army_llama?style=flat-square&label=⭐&color=2b2b2b) | **[Swiss Army Llama](https://github.com/Dicklesworthstone/swiss_army_llama)** | High-performance FastAPI service for local LLM inference and semantic search. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/your-source-to-prompt.html?style=flat-square&label=⭐&color=2b2b2b) | **[Your Source to Prompt](https://github.com/Dicklesworthstone/your-source-to-prompt.html)** | Secure, browser-based tool that turns codebases into optimized LLM prompts. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/bulk_transcribe_youtube_videos_from_playlist?style=flat-square&label=⭐&color=2b2b2b) | **[Bulk YouTube Transcriber](https://github.com/Dicklesworthstone/bulk_transcribe_youtube_videos_from_playlist)** | Convert entire playlists into structured, searchable text with Whisper. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/claude_code_agent_farm?style=flat-square&label=⭐&color=2b2b2b) | **[Claude Code Agent Farm](https://github.com/Dicklesworthstone/claude_code_agent_farm)** | Orchestrate parallel Claude Code agents to autonomously improve codebases across 34 tech stacks. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/mindmap-generator?style=flat-square&label=⭐&color=2b2b2b) | **[Mindmap Generator](https://github.com/Dicklesworthstone/mindmap-generator)** | Distills documents into hierarchical, context-aware mindmaps using non-linear exploration. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/ultimate_mcp_client?style=flat-square&label=⭐&color=2b2b2b) | **[Ultimate MCP Client](https://github.com/Dicklesworthstone/ultimate_mcp_client)** | Universal bridge for AI models to interact with the real world via MCP. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/ultimate_mcp_server?style=flat-square&label=⭐&color=2b2b2b) | **[Ultimate MCP Server](https://github.com/Dicklesworthstone/ultimate_mcp_server)** | Unified MCP server exposing dozens of tools to frontier models. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/markdown_web_browser?style=flat-square&label=⭐&color=2b2b2b) | **[Markdown Web Browser](https://github.com/Dicklesworthstone/markdown_web_browser)** | Headless browser that renders modern JavaScript-heavy sites into clean Markdown for agents. |

### Systems & Rust

| | Project | Description |
|:--|:--|:--|
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/fast_vector_similarity?style=flat-square&label=⭐&color=2b2b2b) | **[Fast Vector Similarity](https://github.com/Dicklesworthstone/fast_vector_similarity)** | High-speed Rust library for complex vector similarity metrics with Python bindings. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/frankentui?style=flat-square&label=⭐&color=2b2b2b) | **[FrankenTUI](https://github.com/Dicklesworthstone/frankentui)** | Minimal, high-performance terminal UI kernel. The rendering substrate for CASS and other Rust TUI apps. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/frankensqlite?style=flat-square&label=⭐&color=2b2b2b) | **[FrankenSQLite](https://github.com/Dicklesworthstone/frankensqlite)** | Clean-room Rust reimplementation of SQLite with MVCC page-level versioning and RaptorQ erasure codes. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/frankenterm?style=flat-square&label=⭐&color=2b2b2b) | **[FrankenTerm](https://github.com/Dicklesworthstone/frankenterm)** | Terminal hypervisor for AI agent swarms with pattern detection and event-driven automation. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/fast_cmaes?style=flat-square&label=⭐&color=2b2b2b) | **[Fast CMA-ES](https://github.com/Dicklesworthstone/fast_cmaes)** | SIMD-accelerated, Rayon-parallelized evolution strategy optimizer in Rust. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/rust_scriptbots?style=flat-square&label=⭐&color=2b2b2b) | **[Rust ScriptBots](https://github.com/Dicklesworthstone/rust_scriptbots)** | Deterministic, GPU-accelerated artificial life simulator. Modern Rust reimplementation of Karpathy's ScriptBots. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/ultrasearch?style=flat-square&label=⭐&color=2b2b2b) | **[UltraSearch](https://github.com/Dicklesworthstone/ultrasearch)** | Instant file search engine for Windows using NTFS USN journals and Tantivy. A modern "Everything" in Rust. |

### Research & Science

| | Project | Description |
|:--|:--|:--|
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/bio_inspired_nanochat?style=flat-square&label=⭐&color=2b2b2b) | **[Bio-Inspired Nanochat](https://github.com/Dicklesworthstone/bio_inspired_nanochat)** | What if a Transformer had a metabolism? Living weights with synaptic fatigue and structural plasticity. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/model_guided_research?style=flat-square&label=⭐&color=2b2b2b) | **[Model-Guided Research](https://github.com/Dicklesworthstone/model_guided_research)** | 11 exotic math frameworks for AI (Lie group attention, p-adic spaces, tropical geometry). |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/acip?style=flat-square&label=⭐&color=2b2b2b) | **[ACIP](https://github.com/Dicklesworthstone/acip)** | AI Cognitive Inoculation Protocol: defense against prompt injection via external monitoring. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/brenner_bot?style=flat-square&label=⭐&color=2b2b2b) | **[Brenner Bot](https://github.com/Dicklesworthstone/brenner_bot)** | Multi-agent research system embodying Sydney Brenner's scientific methodology. |
| | **[LLM Introspective Compression](https://www.jeffreyemanuel.com/writing/llm_introspective_compression)** | Treating LLM context as a save state: reasoning backtracking and metacognitive control. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/phage_explorer?style=flat-square&label=⭐&color=2b2b2b) | **[Phage Explorer](https://github.com/Dicklesworthstone/phage_explorer)** | Interactive educational site exploring bacteriophages with 3D visualization. |

### Developer Tools

| | Project | Description |
|:--|:--|:--|
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/sqlalchemy_data_model_visualizer?style=flat-square&label=⭐&color=2b2b2b) | **[SQLAlchemy Visualizer](https://github.com/Dicklesworthstone/sqlalchemy_data_model_visualizer)** | Instantly turn SQLAlchemy ORM models into interactive SVG diagrams. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/automatic_log_collector_and_analyzer?style=flat-square&label=⭐&color=2b2b2b) | **[Automatic Log Collector](https://github.com/Dicklesworthstone/automatic_log_collector_and_analyzer)** | Open-source Splunk alternative for multi-server log aggregation and analysis. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/misc_coding_agent_tips_and_scripts?style=flat-square&label=⭐&color=2b2b2b) | **[Coding Agent Tips](https://github.com/Dicklesworthstone/misc_coding_agent_tips_and_scripts)** | Battle-tested solutions for AI coding agent workflows and terminal setup. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/coding_agent_account_manager?style=flat-square&label=⭐&color=2b2b2b) | **[Coding Agent Account Manager](https://github.com/Dicklesworthstone/coding_agent_account_manager)** | Sub-100ms auth switching across Claude Max, GPT Pro, and Gemini subscriptions. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/flywheel_connectors?style=flat-square&label=⭐&color=2b2b2b) | **[Flywheel Connectors](https://github.com/Dicklesworthstone/flywheel_connectors)** | Secure integration adapters for external services in the Flywheel ecosystem. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/pi_agent_rust?style=flat-square&label=⭐&color=2b2b2b) | **[Pi Agent Rust](https://github.com/Dicklesworthstone/pi_agent_rust)** | High-performance AI coding agent CLI with sub-100ms startup and native SSE streaming. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/cloud_benchmarker?style=flat-square&label=⭐&color=2b2b2b) | **[Cloud Benchmarker](https://github.com/Dicklesworthstone/cloud_benchmarker)** | Automated cloud instance benchmarking with charts and historical tracking. |

### Education & Visualization

| | Project | Description |
|:--|:--|:--|
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/visual_astar_python?style=flat-square&label=⭐&color=2b2b2b) | **[Visual A* Pathfinding](https://github.com/Dicklesworthstone/visual_astar_python)** | Cinematic, animated visualizations of pathfinding algorithms in action. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/introduction_to_temporal_logic?style=flat-square&label=⭐&color=2b2b2b) | **[Introduction to Temporal Logic](https://github.com/Dicklesworthstone/introduction_to_temporal_logic)** | How temporal logic can be used to analyze concurrency. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/hoeffdings_d_explainer?style=flat-square&label=⭐&color=2b2b2b) | **[Hoeffding's D Explainer](https://github.com/Dicklesworthstone/hoeffdings_d_explainer)** | The non-parametric dependency measure that catches what Pearson and Spearman miss. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/bakery_algorithm?style=flat-square&label=⭐&color=2b2b2b) | **[Lamport's Bakery Algorithm](https://github.com/Dicklesworthstone/bakery_algorithm)** | Visual Pythonic implementation of fair mutual exclusion without atomic hardware. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/cmaes_explainer?style=flat-square&label=⭐&color=2b2b2b) | **[CMA-ES Explainer](https://github.com/Dicklesworthstone/cmaes_explainer)** | Interactive deep dive into the evolution strategy that works where gradient descent fails. |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/kissinger_undergraduate_thesis?style=flat-square&label=⭐&color=2b2b2b) | **[Kissinger Thesis Reader](https://github.com/Dicklesworthstone/kissinger_undergraduate_thesis)** | A reader for Henry Kissinger's 400-page undergraduate thesis on the meaning of history. |

### More Projects

| | Project | Description |
|:--|:--|:--|
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/nextjs-github-markdown-blog?style=flat-square&label=⭐&color=2b2b2b) | **[Next.js GitHub Blog](https://github.com/Dicklesworthstone/nextjs-github-markdown-blog)** | Blogging platform that uses GitHub as a headless CMS |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/jeffreysprompts.com?style=flat-square&label=⭐&color=2b2b2b) | **[JeffreysPrompts.com](https://github.com/Dicklesworthstone/jeffreysprompts.com)** | Curated prompt library for agentic coding workflows |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/llm-docs?style=flat-square&label=⭐&color=2b2b2b) | **[LLM Docs](https://github.com/Dicklesworthstone/llm-docs)** | Documentation optimized for LLM consumption |
| | **[Grassmann Article](https://www.jeffreyemanuel.com/writing/hermann_grassmann_nature_of_abstractions)** | The story of the self-taught genius who invented linear algebra decades early |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/llm_multi_round_coding_tournament?style=flat-square&label=⭐&color=2b2b2b) | **[LLM Tournament](https://github.com/Dicklesworthstone/llm_multi_round_coding_tournament)** | Arena where LLMs compete and iterate on coding challenges via peer review |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/agent_flywheel_clawdbot_skills_and_integrations?style=flat-square&label=⭐&color=2b2b2b) | **[Clawdbot Skills](https://github.com/Dicklesworthstone/agent_flywheel_clawdbot_skills_and_integrations)** | Modular skill library teaching agents to use the Flywheel toolkit |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/automated_plan_reviser_pro?style=flat-square&label=⭐&color=2b2b2b) | **[Automated Plan Reviser](https://github.com/Dicklesworthstone/automated_plan_reviser_pro)** | Iterative specification refinement using extended reasoning models |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/the_lighthill_debate_on_ai?style=flat-square&label=⭐&color=2b2b2b) | **[The Lighthill Debate on AI](https://github.com/Dicklesworthstone/the_lighthill_debate_on_ai)** | Full transcript of the 1973 debate that nearly killed British AI research |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/youtube_transcript_cleaner?style=flat-square&label=⭐&color=2b2b2b) | **[YouTube Transcript Cleaner](https://github.com/Dicklesworthstone/youtube_transcript_cleaner)** | Clean up raw YouTube auto-captions into readable text |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/remote_compilation_helper?style=flat-square&label=⭐&color=2b2b2b) | **[Remote Compilation Helper](https://github.com/Dicklesworthstone/remote_compilation_helper)** | Transparent build offloading for AI agents via Claude Code hooks |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/system_resource_protection_script?style=flat-square&label=⭐&color=2b2b2b) | **[System Resource Protection](https://github.com/Dicklesworthstone/system_resource_protection_script)** | Intelligent resource guardrails that prevent dev tools from freezing your Linux desktop |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/asupersync?style=flat-square&label=⭐&color=2b2b2b) | **[ASupersync](https://github.com/Dicklesworthstone/asupersync)** | Spec-first, cancel-correct, capability-secure async runtime for Rust |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/anti_alzheimers_flasher?style=flat-square&label=⭐&color=2b2b2b) | **[Anti-Alzheimer's Flasher](https://github.com/Dicklesworthstone/anti_alzheimers_flasher)** | Web-based 40Hz neural stimulation tool |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/chat_shared_conversation_to_file?style=flat-square&label=⭐&color=2b2b2b) | **[Chat to File](https://github.com/Dicklesworthstone/chat_shared_conversation_to_file)** | Convert ChatGPT, Gemini, and Grok share links to clean Markdown |
| ![Stars](https://img.shields.io/github/stars/Dicklesworthstone/prepareprojectforllmprompt?style=flat-square&label=⭐&color=2b2b2b) | **[PrepareProjectForLLMPrompt](https://github.com/Dicklesworthstone/prepareprojectforllmprompt)** | Flatten a codebase into a single LLM-ready prompt |

---

## The Nvidia Short Thesis

In January 2025, I published a [12,000-word analysis](https://www.jeffreyemanuel.com/writing/the_short_case_for_nvda) arguing that DeepSeek and the economics of AI inference would collide with Nvidia's valuation narrative. Within days, roughly $600 billion in market cap evaporated.

<table>
<tr>
<td width="120" align="center">
<a href="https://x.com/naval"><img src="https://img.shields.io/badge/-Naval_Ravikant-000000?style=for-the-badge&logo=x&logoColor=white" alt="Naval Ravikant"/></a>
</td>
<td><em>"Come for the trade, stay for the dazzling 60-minute education on the state of AI."</em></td>
</tr>
<tr>
<td align="center">
<a href="https://www.bloomberg.com/opinion/authors/ARbTQlRLRjE/matthew-s-levine"><img src="https://img.shields.io/badge/-Matt_Levine-5C00A3?style=for-the-badge&logo=bloomberg&logoColor=white" alt="Matt Levine"/></a>
</td>
<td><em>"A candidate for the most impactful short research report ever written."</em></td>
</tr>
<tr>
<td align="center">
<a href="https://simonwillison.net/"><img src="https://img.shields.io/badge/-Simon_Willison-2D7D46?style=for-the-badge&logo=python&logoColor=white" alt="Simon Willison"/></a>
</td>
<td><em>"Long, excellent... Jeffrey has a rare combination of experience in both computer science and investment analysis."</em></td>
</tr>
</table>

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
  <a href="https://star-history.com/#Dicklesworthstone/mcp_agent_mail&Dicklesworthstone/llm_aided_ocr&Dicklesworthstone/beads_viewer&Dicklesworthstone/agentic_coding_flywheel_setup&Dicklesworthstone/your-source-to-prompt.html&Date">
    <img src="https://api.star-history.com/svg?repos=Dicklesworthstone/mcp_agent_mail,Dicklesworthstone/llm_aided_ocr,Dicklesworthstone/beads_viewer,Dicklesworthstone/agentic_coding_flywheel_setup,Dicklesworthstone/your-source-to-prompt.html&type=Date&theme=dark" alt="Star History Chart" width="800" />
  </a>
</p>

---

## Products

- 🌐 **[jeffreyemanuel.com](https://www.jeffreyemanuel.com)** — Personal site built with Next.js 16, React Three Fiber, and GSAP. 70 components, 3D WebGL hero, 21 essays, 90+ project showcase.
- 📝 **[JeffreysPrompts.com](https://jeffreysprompts.com)** — Battle-tested prompts for AI coding agents. Browse, copy, or install as Claude Code skills.
- ⚡ **[Agent-Flywheel.com](https://agent-flywheel.com)** — Interactive setup wizard for the complete Flywheel ecosystem
- 🔬 **[BrennerBot.org](https://brennerbot.org)** — Multi-agent research orchestration using Sydney Brenner's scientific methods
- 🖥️ **[FrankenTUI.com](https://frankentui.com)** — Minimal, deterministic terminal UI kernel for Rust TUI applications

---

## Philosophy

> [!IMPORTANT]
> The bottleneck in software isn't writing code — it's coordination. Build the right tooling and you can run a dozen frontier-model agents on the same repo at the same time, delivering in days what used to take months. That's the Flywheel thesis: every tool you add makes every agent more productive, and the compounding never stops.

---

## Recognition

- **[Naval Ravikant](https://x.com/naval)** called the Nvidia short thesis a "dazzling 60-minute education on the state of AI"
- **[Matt Levine](https://www.bloomberg.com/opinion/authors/ARbTQlRLRjE/matthew-s-levine)** (Bloomberg) called it "a candidate for the most impactful short research report ever written"
- **[Simon Willison](https://simonwillison.net/)** (creator of Datasette) praised the "rare combination of experience in both computer science and investment analysis"
- Front page of **Hacker News** (multiple times)
- Featured on **Slashdot**, the **Bankless podcast**, and picked up by analysts and fund managers worldwide
- 16,700+ GitHub stars, 1,700+ followers, 60,000+ contributions

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
