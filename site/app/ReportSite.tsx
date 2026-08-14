"use client";

import { useMemo, useState } from "react";
import reportData from "../data/rc1_model_assessments.json";

type Language = "zh" | "en";
type Score = {
  mean: number;
  records: number;
  scored_records: number;
  coverage: number;
  completion_rate: number;
  completion_adjusted_mean: number | null;
  recovery_attempted: number;
  recovery_selected: number;
  strict_mean: number | null;
};
type Model = (typeof reportData.models)[number];

const TRACKS = [
  "core",
  "reasoning",
  "code",
  "translation",
  "tools",
  "vision",
  "ocr",
  "long_context",
  "embedding",
  "safety",
  "medical",
] as const;

const trackLabels: Record<string, { zh: string; en: string }> = {
  all: { zh: "全部赛道", en: "All tracks" },
  core: { zh: "核心", en: "Core" },
  reasoning: { zh: "推理", en: "Reasoning" },
  code: { zh: "代码", en: "Code" },
  translation: { zh: "翻译", en: "Translation" },
  tools: { zh: "工具", en: "Tools" },
  vision: { zh: "视觉", en: "Vision" },
  ocr: { zh: "OCR", en: "OCR" },
  long_context: { zh: "长上下文", en: "Long context" },
  embedding: { zh: "嵌入", en: "Embedding" },
  safety: { zh: "安全", en: "Safety" },
  medical: { zh: "医疗", en: "Medical" },
};

const copy = {
  zh: {
    nav: ["结论", "设计", "赛道", "模型", "方法"],
    eyebrow: "BENCHMARK 1.0 · RC1 PRACTICAL SNAPSHOT",
    titleA: "39 个本地模型，",
    titleB: "在同一台电脑上说话。",
    intro:
      "一份关于小模型真实本地可用性的可复现记录。严格基线保持不变，默认展示实用离线重评与被选中的定向恢复证据，并拒绝用一个万能总分掩盖不同生态位。",
    openReport: "阅读完整报告",
    github: "查看 GitHub",
    current: "当前发布快照",
    metrics: ["本地模型", "任务记录", "正式赛道", "未完成基础设施记录"],
    takeawayTitle: "先给结论，再看榜单",
    takeawayLead: "Qwen3-8B Q4 与 Qwen3-VL 8B 是当前最均衡的通用参考；真正的答案仍取决于任务。",
    takeaways: [
      ["通用与 Agent", "Qwen3-8B Q4 与 Qwen3-VL 都达到 Core 0.879、Tools 0.909；后者 Code 0.890。"],
      ["高质量文本", "Gemma4 E4B 与 Qwen3.5 9B 适合通用和长上下文，但代码侧表现不同。"],
      ["速度优先", "Granite4 7B-A1B、LFM2.5 与 MiniCPM5 很快，但不能把吞吐当成能力。"],
      ["专用工作", "Qwen3 Embedding、Granite Guardian 与 OCR 模型必须结合完成率在原生生态位内解释。"],
    ],
    designTitle: "为什么没有一张“万能总榜”",
    designLead: "Benchmark 的目标不是复刻厂商 leaderboard，而是回答：这些模型在这台普通本地电脑上，实际能做什么？",
    principles: [
      ["分赛道", "Core、推理、代码、工具、视觉、OCR、嵌入与安全分别比较，不惩罚不适用能力。"],
      ["证据分层", "不可变 raw、归一化解释、评分器输出与展示报告彼此分离，评分更新无需重新推理。"],
      ["实用边界", "超时、截断和没有 final answer 是本机可用性证据；网络或服务失败绝不算能力 0 分。"],
      ["身份稳定", "版本、manifest hash、模型 digest、profile 和 task ID 共同定义一条结果，修订版不会覆盖旧证据。"],
    ],
    leaderTitle: "各赛道分别看，才不会误导",
    leaderLead: "每个分数是实用评分的 0–1 赛道均值；排序同时考虑完成率。Coverage、完成率与样本数必须一起阅读。",
    explorerTitle: "39 个模型逐一查看",
    explorerLead: "筛选生态位或赛道，查看官方定位、本机实际得分、推荐用途和风险。Retention 仍为 UNASSESSED。",
    search: "搜索模型、定位或 capability…",
    roleAll: "全部模型定位",
    sort: "排序/筛选赛道",
    showing: "当前显示",
    modelUnit: "个模型",
    official: "官方来源",
    recommendation: "推荐用途",
    caution: "注意事项",
    noScore: "无适用分数",
    runtimeTitle: "稳定性是能力的一部分，但不是能力分本身",
    runtimeLead: "严格基线没有基础设施缺口。50 条定向恢复只替换可评分且更好的派生结果，原始证据始终保留。",
    runtimeNotes: [
      ["50", "定向恢复记录"],
      ["39", "被选用的恢复结果"],
      ["6", "仍无可评分 final 的能力任务"],
      ["0", "基础设施未完成"],
    ],
    methodTitle: "以后新增模型，不重跑原来的 39 个",
    methodLead: "拉取新模型后记录 digest，显式选择可比能力分配，只跑适用冻结赛道，再导出新的脱敏结果。",
    steps: ["检查真实 metadata 与 digest", "选择已有可比 assignment", "逐题保存 raw 与 checkpoint", "离线评分并验证", "追加脱敏公开结果"],
    boundary: "解释边界",
    boundaryText:
      "Vision、OCR 与 Medical 的题集仍较小；官方数据只用于定位背景，除非数据集、精度、prompt、runtime 与 scorer 全部一致，否则不作数值等价比较。医疗和安全结果不构成临床或部署安全证明。",
    footer: "公开网站只包含脱敏派生数据。私有题库、raw response 与运行状态不会进入 GitHub 或 Sites。",
  },
  en: {
    nav: ["Findings", "Design", "Tracks", "Models", "Method"],
    eyebrow: "BENCHMARK 1.0 · RC1 PRACTICAL SNAPSHOT",
    titleA: "39 local models,",
    titleB: "one practical laptop.",
    intro:
      "A reproducible account of real small-model usability. The strict baseline remains intact; practical offline regrading and selected targeted recovery are the default view, without a universal score.",
    openReport: "Read the full report",
    github: "View on GitHub",
    current: "Current release snapshot",
    metrics: ["local models", "task records", "formal tracks", "infrastructure-incomplete records"],
    takeawayTitle: "Conclusions before leaderboards",
    takeawayLead: "Qwen3-8B Q4 and Qwen3-VL 8B are the most balanced general references, but the right answer depends on the job.",
    takeaways: [
      ["General and agents", "Qwen3-8B Q4 and Qwen3-VL both reach Core 0.879 and Tools 0.909; Qwen3-VL adds Code 0.890."],
      ["Quality text work", "Gemma4 E4B and Qwen3.5 9B are strong for general and long-context work, with different code profiles."],
      ["Speed first", "Granite4 7B-A1B, LFM2.5, and MiniCPM5 are fast, but throughput is not capability."],
      ["Specialist work", "Qwen3 Embedding, Granite Guardian, and OCR models must be interpreted with completion in their native niches."],
    ],
    designTitle: "Why there is no universal leaderboard",
    designLead: "The benchmark does not recreate publisher leaderboards. It asks what these models can actually do on this ordinary local machine.",
    principles: [
      ["Separate tracks", "Core, reasoning, code, tools, vision, OCR, embedding, and safety are compared independently; non-applicable tracks never penalize specialists."],
      ["Layered evidence", "Immutable raw, normalization, scorer output, and reporting are separate, so scorer changes do not require new inference."],
      ["Practical boundaries", "Timeouts, truncation, and missing final answers are usability evidence; network or service failure is never capability zero."],
      ["Stable identity", "Version, manifest hash, model digest, profile, and task ID define a result, so a revision never overwrites old evidence."],
    ],
    leaderTitle: "Track-by-track is the honest comparison",
    leaderLead: "Scores are 0–1 practical means, ranked with completion in view. Coverage, completion, and record counts must be read together.",
    explorerTitle: "Explore all 39 models",
    explorerLead: "Filter by niche or track to inspect publisher positioning, local scores, recommended use, and cautions. Retention remains UNASSESSED.",
    search: "Search model, role, or capability…",
    roleAll: "All model roles",
    sort: "Sort/filter track",
    showing: "Showing",
    modelUnit: "models",
    official: "Official source",
    recommendation: "Recommended use",
    caution: "Caution",
    noScore: "No applicable score",
    runtimeTitle: "Stability is part of usability, not the score itself",
    runtimeLead: "The strict baseline has no infrastructure gap. Targeted recovery replaces only scoreable, better derived outcomes while preserving original evidence.",
    runtimeNotes: [
      ["50", "targeted recovery records"],
      ["39", "selected recovery results"],
      ["6", "capability items still lacking a scoreable final"],
      ["0", "infrastructure-incomplete"],
    ],
    methodTitle: "Add future models without rerunning the 39",
    methodLead: "Record the new digest, select an explicit comparable assignment, run only applicable frozen tracks, then export a new sanitized snapshot.",
    steps: ["Inspect real metadata and digest", "Select a comparable assignment", "Persist raw and checkpoint per task", "Score offline and validate", "Append a sanitized public result"],
    boundary: "Interpretation boundary",
    boundaryText:
      "Vision, OCR, and Medical still use small fixture sets. Publisher data is positioning context, not numerically equivalent unless dataset, precision, prompt, runtime, and scorer match. Medical and safety results are not clinical or deployment certification.",
    footer: "This public site contains sanitized derived data only. Private tasks, raw responses, and run state never enter GitHub or Sites.",
  },
};

function scoreFor(model: Model, track: string): Score | undefined {
  return (model.scores as Record<string, Score | undefined>)[track];
}

function formatScore(value: number | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "—";
}

function rankingScore(score: Score | undefined) {
  return score?.completion_adjusted_mean ?? score?.mean ?? -1;
}

export function ReportSite() {
  const [lang, setLang] = useState<Language>("zh");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");
  const [track, setTrack] = useState("core");
  const t = copy[lang];

  const roles = useMemo(
    () => Array.from(new Set(reportData.models.map((model) => model.role[lang]))).sort(),
    [lang],
  );

  const leaders = useMemo(
    () =>
      TRACKS.map((trackId) => {
        const ranked = reportData.models
          .map((model) => ({ model, score: scoreFor(model, trackId) }))
          .filter((row): row is { model: Model; score: Score } => Boolean(row.score))
          .sort((a, b) => rankingScore(b.score) - rankingScore(a.score));
        if (!ranked.length) return null;
        const top = rankingScore(ranked[0].score);
        return {
          track: trackId,
          top,
          records: ranked[0].score.records,
          completion: ranked[0].score.completion_rate,
          names: ranked.filter((row) => rankingScore(row.score) === top).map((row) => row.model.short_name),
        };
      }).filter(Boolean),
    [],
  );

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return reportData.models
      .filter((model) => role === "all" || model.role[lang] === role)
      .filter((model) => track === "all" || Boolean(scoreFor(model, track)))
      .filter((model) => {
        if (!needle) return true;
        return [model.model, model.short_name, model.role[lang], model.capabilities.join(" "), model.official_model]
          .join(" ")
          .toLowerCase()
          .includes(needle);
      })
      .sort((a, b) => {
        const sortTrack = track === "all" ? "core" : track;
        const delta = rankingScore(scoreFor(b, sortTrack)) - rankingScore(scoreFor(a, sortTrack));
        return delta || a.short_name.localeCompare(b.short_name);
      });
  }, [lang, query, role, track]);

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="SummerTestModel home">
          <span className="brand-mark">STM</span>
          <span>SummerTestModel</span>
        </a>
        <nav aria-label="Primary navigation">
          {["findings", "design", "tracks", "models", "method"].map((id, index) => (
            <a key={id} href={`#${id}`}>{t.nav[index]}</a>
          ))}
        </nav>
        <button className="language-toggle" onClick={() => setLang(lang === "zh" ? "en" : "zh")} aria-label="Switch language">
          {lang === "zh" ? "EN" : "中文"}
        </button>
      </header>

      <section className="hero section" id="top">
        <div className="hero-copy">
          <p className="eyebrow">{t.eyebrow}</p>
          <h1>{t.titleA}<br /><em>{t.titleB}</em></h1>
          <p className="hero-intro">{t.intro}</p>
          <div className="hero-actions">
            <a className="button primary" href={`https://github.com/summer521521/SummerTestModel/blob/main/docs/final_report.${lang === "zh" ? "zh-CN" : "en"}.md`} target="_blank" rel="noreferrer">{t.openReport} ↗</a>
            <a className="button secondary" href="https://github.com/summer521521/SummerTestModel" target="_blank" rel="noreferrer">{t.github} ↗</a>
          </div>
        </div>
        <aside className="snapshot" aria-label={t.current}>
          <div className="snapshot-head"><span>{t.current}</span><strong>2026.08.14</strong></div>
          <div className="snapshot-grid">
            {["39", "1,938", "12", "0"].map((value, index) => (
              <div key={value + index}><strong>{value}</strong><span>{t.metrics[index]}</span></div>
            ))}
          </div>
          <div className="machine-line"><span>RTX 4060 Laptop · 8 GiB</span><span>i5-13500HX · 31.8 GiB</span></div>
        </aside>
      </section>

      <section className="section findings" id="findings">
        <div className="section-heading"><span>01</span><div><h2>{t.takeawayTitle}</h2><p>{t.takeawayLead}</p></div></div>
        <div className="takeaway-list">
          {t.takeaways.map(([title, body], index) => (
            <article key={title}><span className="index">0{index + 1}</span><h3>{title}</h3><p>{body}</p></article>
          ))}
        </div>
      </section>

      <section className="section design" id="design">
        <div className="section-heading inverse"><span>02</span><div><h2>{t.designTitle}</h2><p>{t.designLead}</p></div></div>
        <div className="principles">
          {t.principles.map(([title, body]) => <article key={title}><h3>{title}</h3><p>{body}</p></article>)}
        </div>
      </section>

      <section className="section tracks" id="tracks">
        <div className="section-heading"><span>03</span><div><h2>{t.leaderTitle}</h2><p>{t.leaderLead}</p></div></div>
        <div className="leader-table" role="table" aria-label="Track leaders">
          {leaders.map((row) => row && (
            <div className="leader-row" role="row" key={row.track}>
              <span className="track-name" role="cell">{trackLabels[row.track][lang]}</span>
              <span className="leader-name" role="cell">{row.names.join(" · ")}</span>
              <span className="score" role="cell">{row.top.toFixed(3)}</span>
              <span className="bar" aria-hidden="true"><i style={{ width: `${row.top * 100}%` }} /></span>
              <small>{row.records} records · {Math.round(row.completion * 100)}% complete</small>
            </div>
          ))}
        </div>
      </section>

      <section className="section explorer" id="models">
        <div className="section-heading"><span>04</span><div><h2>{t.explorerTitle}</h2><p>{t.explorerLead}</p></div></div>
        <div className="filters">
          <label><span className="sr-only">Search</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t.search} /></label>
          <label><span className="sr-only">Role</span><select value={role} onChange={(event) => setRole(event.target.value)}><option value="all">{t.roleAll}</option>{roles.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
          <label><span className="sr-only">Track</span><select value={track} onChange={(event) => setTrack(event.target.value)}><option value="all">{trackLabels.all[lang]}</option>{TRACKS.map((item) => <option key={item} value={item}>{trackLabels[item][lang]}</option>)}</select></label>
          <p>{t.showing} <strong>{filtered.length}</strong> {t.modelUnit}</p>
        </div>
        <div className="model-grid">
          {filtered.map((model) => {
            const selectedScore = track === "all" ? scoreFor(model, "core") : scoreFor(model, track);
            return (
              <article className="model-card" key={model.digest}>
                <div className="model-head"><div><span className="role-tag">{model.role[lang]}</span><h3>{model.short_name}</h3><code>{model.parameter_size} · {model.quantization} · {model.disk_size_gib.toFixed(2)} GiB</code></div><strong className="model-score">{formatScore(selectedScore?.mean)}</strong></div>
                <div className="score-strip">{Object.entries(model.scores).map(([name, score]) => <span key={name}><i>{trackLabels[name]?.[lang] ?? name}</i><b>{score.mean.toFixed(3)}</b><small>{Math.round(score.completion_rate * 100)}% ✓{score.recovery_selected ? ` · R${score.recovery_selected}` : ""}</small></span>)}</div>
                <dl><div><dt>{t.recommendation}</dt><dd>{model.recommendation[lang]}</dd></div><div><dt>{t.caution}</dt><dd>{model.caution[lang]}</dd></div></dl>
                <div className="model-foot"><span>{model.capabilities.join(" · ") || t.noScore}</span>{model.official_source_url ? <a href={model.official_source_url} target="_blank" rel="noreferrer">{t.official} ↗</a> : <span>Source unresolved</span>}</div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="section runtime">
        <div className="runtime-copy"><p className="eyebrow">RUNTIME EVIDENCE</p><h2>{t.runtimeTitle}</h2><p>{t.runtimeLead}</p></div>
        <div className="runtime-stats">{t.runtimeNotes.map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}</div>
      </section>

      <section className="section method" id="method">
        <div className="section-heading"><span>05</span><div><h2>{t.methodTitle}</h2><p>{t.methodLead}</p></div></div>
        <ol className="workflow">{t.steps.map((step, index) => <li key={step}><span>{index + 1}</span><p>{step}</p></li>)}</ol>
        <aside className="boundary"><h3>{t.boundary}</h3><p>{t.boundaryText}</p></aside>
      </section>

      <footer><div><strong>SummerTestModel</strong><span>Benchmark 1.0-rc1 · practical-regrade-1</span></div><p>{t.footer}</p><a href="#top">↑ TOP</a></footer>
    </main>
  );
}
