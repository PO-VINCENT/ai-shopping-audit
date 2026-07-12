"use strict";

/* Dashboard translations. The default language follows the browser
   (navigator.language); the header selector overrides it and persists in
   localStorage. Findings and recommendations come from the audit engine
   and are not translated here. Add a language by adding one entry. */

const I18N = {
  en: {
    tagline: "Is your product page readable by AI shopping agents?",
    badges: "Offline · deterministic · no API key · no storefront writes",
    inputTitle: "Product page",
    urlLabel: "URL",
    fetch: "Fetch",
    fetchTitle: "The local server fetches this one page (a single request)",
    htmlLabel: "Page HTML",
    htmlPlaceholder:
      "Left empty? Audit fetches the page for you (one request via the local server). Or paste the rendered HTML to stay fully offline.",
    demoGood: "Load good demo (97/100)",
    demoBad: "Load bad demo (16/100)",
    providerSummary: "Model provider (optional)",
    providerLabel: "Provider",
    providerOffline: "Offline / deterministic",
    modelLabel: "Model ID",
    modelPlaceholder: "Server default",
    providerNote:
      "Keys stay in the local server environment. This page never asks for or stores them.",
    audit: "Audit page",
    emptyTitle: "Your audit appears here",
    emptyBody:
      "Load a demo or enter a product URL, then press Audit page. You get a 0–100 readiness score, findings with rule IDs, the questions only the merchant can answer, and evidence-backed fixes.",
    scoreNote:
      "Six pillars sum to 100; blocking defects cap the total. Status is ready only at 80+ with no cap. Click a pillar to see exactly what it checks.",
    tabFindings: "Findings",
    tabQuestions: "Merchant questions",
    tabFixes: "Fixes",
    tabEvidence: "Evidence",
    questionsNote: "CatalogReady never invents these facts. Supply verified values and re-run.",
    resume: "Re-run with answers",
    fixesNote:
      "Draft mode builds reversible changes from verified evidence only and validates them against an isolated in-memory preview. Nothing is written to a storefront.",
    draft: "Draft evidence-backed fixes",
    jsonldTitle: "Recommended Product JSON-LD",
    copy: "Copy",
    copied: "Copied",
    evId: "ID",
    evField: "Field",
    evValue: "Value",
    evSource: "Source",
    chatTitle: "Ask the agent",
    chatPlaceholder: "e.g. why is structured data low? · what should I fix first?",
    ask: "Ask",
    chatNote:
      "Answers come from the audit result only. Select a model provider above for open-ended questions; otherwise answers are deterministic.",
    downloadReport: "Download HTML report",
    downloadJson: "Download JSON",
    footerLeft: "CatalogReady · evidence-grounded product audits",
    footerRight: "A readiness score is never a ranking or citation guarantee.",
    serverInfo: (version, started) => `Server v${version} · started ${started}`,
    serverStale: (version, started) =>
      `Server v${version} (started ${started}) is running OLD code — restart: uv run catalogready dashboard`,
    serverUnreachable: "Local server unreachable — start it with: uv run catalogready dashboard",
    // dynamic strings
    statusNeedUrl: "Provide a product URL (or load a demo).",
    statusEnterUrl: "Enter a product URL to fetch.",
    statusFetching: "Fetching the page (one request via the local server)…",
    statusFetched: (kb) => `Fetched ${kb} KB. Ready to audit.`,
    statusBotWall:
      "The site served a bot-protection page instead of the product. Paste the page HTML from your browser (view-source) or use the extension.",
    statusAuditing: "Auditing locally…",
    statusDrafting: "Drafting evidence-backed fixes…",
    demoGoodLoaded: "Good demo loaded. Press Audit page.",
    demoBadLoaded: "Bad demo loaded. Press Audit page.",
    scoreLine: (score, status) => `${score}/100, ${status}`,
    verdictReady:
      "This page is ready for AI shopping agents — its product data is machine-readable and evidence-backed.",
    verdictPartial:
      "This page is partially readable by AI shopping agents; the gaps below limit how confidently they can use it.",
    verdictPoor:
      "This page is largely invisible or untrustworthy to AI shopping agents in its current state.",
    summaryCapped: (cap, reasons) => `The score is hard-capped at ${cap}: ${reasons}`,
    summaryFindings: (high, medium) =>
      `${high} critical and ${medium} recommended findings need attention — see the Findings tab.`,
    summaryBlocking: (n) =>
      `${n} blocking fact${n > 1 ? "s" : ""} only the merchant can supply — see Merchant questions.`,
    summaryStart: (action) => `Start here: ${action}`,
    summaryAutofix: (n, before, after) =>
      `Auto-drafted ${n} reversible fix(es): validated preview ${before} → ${after} — see the Fixes tab.`,
    capBanner: (cap) => `Score capped at ${cap}.`,
    noFindings: "No findings. Everything checked is machine-readable.",
    noQuestions: "No open merchant questions.",
    blocking: "blocking",
    answerPlaceholder: (field) => `Verified ${field}`,
    proposedChanges: (n) => `Proposed ${n} reversible change(s):`,
    reversible: "reversible",
    validationLine: (before, after, delta, status) =>
      `Isolated preview validation: ${before} → ${after} (${delta}), status ${status}. Nothing was written to any storefront.`,
    noChanges: "No evidence-backed page changes were justified yet.",
    chatNeedsAudit: "Run an audit first, then ask me about the result.",
    answeredBy: (mode) => `answered by ${mode}`,
    error: (message) => `Error: ${message}`,
    keyHint:
      "To use a model provider, add its key to the server's .env (e.g. OPENAI_API_KEY=… and OPENAI_MODEL=…) and restart the server. See docs/BYO-KEYS.md. The audit itself needs no key.",
    groupBy: "Group by",
    groupSeverity: "Severity",
    groupMetric: "Metric",
    summaryWeakest: (metric, high, total) =>
      `Weakest area: ${metric} (${high} critical of ${total} findings).`,
    metricAll: "All findings",
    metrics: {
      machine_readability: { name: "Readability", question: "Can a parser extract the product at all?" },
      validity: { name: "Validity", question: "Is the data well-formed against its standard?" },
      completeness: { name: "Completeness", question: "Are the fields agents require present?" },
      consistency: { name: "Consistency", question: "Does the markup match the visible page?" },
      trust: { name: "Trust", question: "Can the claims be believed?" },
      accessibility: { name: "Accessibility", question: "Can AI crawlers reach and cite it?" },
      transactability: { name: "Transactability", question: "Could an agent complete a purchase?" },
      freshness: { name: "Freshness", question: "Is the data current?" },
    },
    pillars: {
      product_identity: "Product identity",
      offer_completeness: "Offer completeness",
      structured_data: "Structured data",
      decision_evidence: "Decision evidence",
      media_variants: "Media & variants",
      claim_grounding: "Claim grounding",
    },
    pillarExplain: {
      product_identity:
        "Can an AI agent tell exactly which product this is? Checks the title, brand, category, a stable identifier (SKU, GTIN, or MPN), and a canonical URL.",
      offer_completeness:
        "Can an agent quote this offer? Price, currency, and availability must exist as evidence and be machine-readable together in the Offer markup.",
      structured_data:
        "Is there valid Product JSON-LD that matches the visible page? This is the primary surface shopping agents parse; missing Product data caps the total at 74.",
      decision_evidence:
        "Is there enough verified substance to answer buyer questions: a description, specifications, substantive visible text, and on-page shipping/returns/care facts?",
      media_variants:
        "Can an agent show and distinguish the product: a primary image, multiple images, variant attributes (color/size), and a variant-level identifier.",
      claim_grounding:
        "Do marketing claims in the title and description have supporting evidence on the page? Unsupported superlative, proof, warranty, or performance claims deduct points, and a high-risk one caps the total at 49.",
    },
    checks: {
      stable_identifier: "stable identifier (SKU / GTIN / MPN)",
      complete_offer_markup: "price + currency + availability together in Offer markup",
      product_node: "Product JSON-LD node present",
      valid_json_ld: "all JSON-LD blocks parse",
      substantive_page: "at least 120 words of visible text",
      evidence_topics: "3+ evidence topics (shipping, returns, care…)",
      review_evidence: "aggregate rating with review count",
      variant_attribute: "variant attribute (color / size / pattern)",
      variant_identity: "variant-level identifier",
      no_high_risk_claims: "no unsupported high-risk claims",
      no_unsupported_claims: "no unsupported claims at all",
      title: "title",
      brand: "brand",
      category: "category",
      canonical_url: "canonical URL",
      price: "price",
      currency: "currency",
      availability: "availability",
      canonical: "canonical link",
      product_identity: "product name in markup",
      offer: "complete Offer markup",
      description: "description",
      specifications: "specifications",
      primary_image: "primary image",
      multiple_images: "multiple images",
    },
  },

  zh: {
    tagline: "你的商品页面能被 AI 购物助手读懂吗？",
    badges: "离线运行 · 确定性规则 · 无需 API 密钥 · 不写入店铺",
    inputTitle: "商品页面",
    urlLabel: "网址",
    fetch: "抓取",
    fetchTitle: "由本地服务器抓取该页面（仅一次请求）",
    htmlLabel: "页面 HTML",
    htmlPlaceholder:
      "留空则审计时自动抓取页面（经本地服务器发起一次请求）；也可粘贴渲染后的 HTML，完全离线运行。",
    demoGood: "加载优秀示例（97/100）",
    demoBad: "加载问题示例（16/100）",
    providerSummary: "模型提供方（可选）",
    providerLabel: "提供方",
    providerOffline: "离线 / 确定性",
    modelLabel: "模型 ID",
    modelPlaceholder: "使用服务器默认值",
    providerNote: "密钥只保存在本地服务器环境变量中，本页面绝不询问或存储密钥。",
    audit: "审计页面",
    emptyTitle: "审计结果将显示在这里",
    emptyBody:
      "加载示例或输入商品网址，然后点击「审计页面」。你将得到 0–100 的就绪评分、带规则编号的问题清单、只有商家能回答的问题，以及有依据支撑的修复建议。",
    scoreNote:
      "六大支柱合计 100 分；阻断性缺陷会封顶总分。仅当 80 分以上且无封顶时状态才为「就绪」。点击任一支柱可查看具体检查项。",
    tabFindings: "问题清单",
    tabQuestions: "商家问题",
    tabFixes: "修复建议",
    tabEvidence: "证据",
    questionsNote: "CatalogReady 绝不编造这些信息。请填写已核实的值后重新运行。",
    resume: "带答案重新运行",
    fixesNote:
      "草稿模式仅基于已核实的证据生成可回滚的修改，并在隔离的内存预览中验证效果。不会写入任何店铺。",
    draft: "生成有据可依的修复草稿",
    jsonldTitle: "推荐的 Product JSON-LD",
    copy: "复制",
    copied: "已复制",
    evId: "编号",
    evField: "字段",
    evValue: "值",
    evSource: "来源",
    chatTitle: "向智能体提问",
    chatPlaceholder: "例如：结构化数据为什么分低？· 应该先修什么？",
    ask: "提问",
    chatNote: "回答仅基于审计结果。在上方选择模型提供方可回答开放式问题；否则为确定性回答。",
    downloadReport: "下载 HTML 报告",
    downloadJson: "下载 JSON",
    footerLeft: "CatalogReady · 有据可依的商品审计",
    footerRight: "就绪评分不构成任何排名或引用保证。",
    serverInfo: (version, started) => `服务器 v${version} · 启动于 ${started}`,
    serverStale: (version, started) =>
      `服务器 v${version}（启动于 ${started}）运行的是旧代码——请重启：uv run catalogready dashboard`,
    serverUnreachable: "本地服务器不可达——请启动：uv run catalogready dashboard",
    statusNeedUrl: "请输入商品网址（或加载示例）。",
    statusEnterUrl: "请先输入要抓取的商品网址。",
    statusFetching: "正在抓取页面（经本地服务器发起一次请求）…",
    statusFetched: (kb) => `已抓取 ${kb} KB，可以开始审计。`,
    statusBotWall:
      "该网站返回了反爬验证页而不是商品页。请从浏览器中复制页面 HTML（查看源代码）粘贴到此处，或使用浏览器扩展。",
    statusAuditing: "正在本地审计…",
    statusDrafting: "正在生成有据可依的修复草稿…",
    demoGoodLoaded: "已加载优秀示例，点击「审计页面」。",
    demoBadLoaded: "已加载问题示例，点击「审计页面」。",
    scoreLine: (score, status) => `${score}/100，${status === "ready" ? "就绪" : "待改进"}`,
    verdictReady: "该页面已为 AI 购物助手就绪——商品数据机器可读且有证据支撑。",
    verdictPartial: "该页面对 AI 购物助手只部分可读；下列缺口会降低其可信引用程度。",
    verdictPoor: "当前状态下，该页面对 AI 购物助手基本不可见或不可信。",
    summaryCapped: (cap, reasons) => `评分被硬性封顶为 ${cap}：${reasons}`,
    summaryFindings: (high, medium) =>
      `${high} 个严重问题和 ${medium} 个建议修复项需要处理——见「问题清单」。`,
    summaryBlocking: (n) => `${n} 项关键信息只有商家能提供——见「商家问题」。`,
    summaryStart: (action) => `建议从这里开始：${action}`,
    summaryAutofix: (n, before, after) =>
      `已自动生成 ${n} 项可回滚修复：隔离预览验证 ${before} → ${after}——见「修复建议」。`,
    capBanner: (cap) => `评分封顶为 ${cap}。`,
    noFindings: "没有发现问题，所有检查项均机器可读。",
    noQuestions: "没有待回答的商家问题。",
    blocking: "必填",
    answerPlaceholder: (field) => `已核实的 ${field}`,
    proposedChanges: (n) => `已生成 ${n} 项可回滚修改：`,
    reversible: "可回滚",
    validationLine: (before, after, delta, status) =>
      `隔离预览验证：${before} → ${after}（${delta}），状态 ${status}。未写入任何店铺。`,
    noChanges: "暂无由证据支撑的页面修改。",
    chatNeedsAudit: "请先运行一次审计，再向我提问。",
    answeredBy: (mode) => `由 ${mode} 回答`,
    error: (message) => `错误：${message}`,
    keyHint:
      "使用模型提供方需在服务器的 .env 中配置密钥（如 OPENAI_API_KEY=… 和 OPENAI_MODEL=…）并重启服务器，详见 docs/BYO-KEYS.md。审计本身无需任何密钥。",
    groupBy: "分组方式",
    groupSeverity: "按严重程度",
    groupMetric: "按度量维度",
    summaryWeakest: (metric, high, total) =>
      `最薄弱维度：${metric}（${total} 项问题中 ${high} 项严重）。`,
    metricAll: "全部问题",
    metrics: {
      machine_readability: { name: "机器可读性", question: "解析器能否提取出商品信息？" },
      validity: { name: "数据有效性", question: "数据是否符合相应标准格式？" },
      completeness: { name: "完整性", question: "AI 助手所需字段是否齐全？" },
      consistency: { name: "一致性", question: "标记数据与页面显示是否一致？" },
      trust: { name: "可信度", question: "页面宣称是否可信有据？" },
      accessibility: { name: "可达性", question: "AI 爬虫能否访问并引用该页？" },
      transactability: { name: "可交易性", question: "AI 助手能否据此完成购买？" },
      freshness: { name: "时效性", question: "数据是否保持最新？" },
    },
    pillars: {
      product_identity: "商品身份",
      offer_completeness: "报价完整性",
      structured_data: "结构化数据",
      decision_evidence: "决策证据",
      media_variants: "图片与变体",
      claim_grounding: "宣称核实",
    },
    pillarExplain: {
      product_identity:
        "AI 助手能否确切识别这是哪个商品？检查标题、品牌、类目、稳定标识符（SKU、GTIN 或 MPN）及规范网址。",
      offer_completeness:
        "AI 助手能否准确报价？价格、币种、库存状态必须作为证据存在，并在 Offer 标记中同时机器可读。",
      structured_data:
        "是否存在与可见页面一致的有效 Product JSON-LD？这是购物助手解析的主要入口；缺失 Product 数据会将总分封顶为 74。",
      decision_evidence:
        "是否有足够的已核实内容回答买家问题：描述、规格参数、足量可见文本，以及页面上的物流/退换/保养信息？",
      media_variants:
        "AI 助手能否展示并区分该商品：主图、多图、变体属性（颜色/尺码）及变体级标识符。",
      claim_grounding:
        "标题与描述中的营销宣称是否有页面证据支撑？无依据的最高级、功效、保修或性能宣称会扣分，高风险宣称会将总分封顶为 49。",
    },
    checks: {
      stable_identifier: "稳定标识符（SKU / GTIN / MPN）",
      complete_offer_markup: "Offer 标记中同时包含价格 + 币种 + 库存",
      product_node: "存在 Product JSON-LD 节点",
      valid_json_ld: "所有 JSON-LD 均可解析",
      substantive_page: "可见文本不少于 120 词",
      evidence_topics: "3 类以上证据主题（物流、退换、保养…）",
      review_evidence: "评分及评论数",
      variant_attribute: "变体属性（颜色 / 尺码 / 花色）",
      variant_identity: "变体级标识符",
      no_high_risk_claims: "无未证实的高风险宣称",
      no_unsupported_claims: "无任何未证实宣称",
      title: "标题",
      brand: "品牌",
      category: "类目",
      canonical_url: "规范网址",
      price: "价格",
      currency: "币种",
      availability: "库存状态",
      canonical: "规范链接",
      product_identity: "标记中的商品名称",
      offer: "完整的 Offer 标记",
      description: "描述",
      specifications: "规格参数",
      primary_image: "主图",
      multiple_images: "多张图片",
    },
  },
};

const i18n = {
  lang: "en",

  detect() {
    const saved = localStorage.getItem("catalogready-lang");
    if (saved && I18N[saved]) return saved;
    const browser = (navigator.language || "en").toLowerCase();
    return browser.startsWith("zh") ? "zh" : "en";
  },

  set(lang) {
    if (!I18N[lang]) lang = "en";
    this.lang = lang;
    localStorage.setItem("catalogready-lang", lang);
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    this.applyStatic();
  },

  t(key, ...args) {
    const table = I18N[this.lang] || I18N.en;
    const value = table[key] ?? I18N.en[key] ?? key;
    return typeof value === "function" ? value(...args) : value;
  },

  pillars() {
    return (I18N[this.lang] || I18N.en).pillars;
  },

  pillarExplain() {
    return (I18N[this.lang] || I18N.en).pillarExplain;
  },

  metricInfo(key) {
    const table = I18N[this.lang] || I18N.en;
    return table.metrics[key] || I18N.en.metrics[key] || { name: key, question: "" };
  },

  checkLabel(key) {
    const table = I18N[this.lang] || I18N.en;
    return table.checks[key] || I18N.en.checks[key] || key.replace(/_/g, " ");
  },

  applyStatic() {
    document.querySelectorAll("[data-i18n]").forEach((element) => {
      element.textContent = this.t(element.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
      element.placeholder = this.t(element.dataset.i18nPlaceholder);
    });
    document.querySelectorAll("[data-i18n-title]").forEach((element) => {
      element.title = this.t(element.dataset.i18nTitle);
    });
  },
};
