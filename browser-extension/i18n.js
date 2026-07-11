"use strict";

/* Popup translations. Default follows the browser language; the header
   selector overrides it (persisted in the popup's localStorage). Findings
   and recommendations come from the local audit engine and are not
   translated here. Add a language by adding one entry. */

const I18N = {
  en: {
    tagline: "AI readiness score",
    settings: "Settings",
    serverLabel: "Local server",
    providerLabel: "Provider",
    providerOffline: "Offline / deterministic",
    modelLabel: "Model ID",
    modelPlaceholder: "Server default",
    settingsNote:
      "Keys stay in the local server environment — this extension never asks for or stores them. Start the server with:",
    analyze: "Score this product page",
    findings: "Findings",
    questions: "Merchant questions",
    fixes: "Fix suggestions",
    questionsNote: "CatalogReady never invents these facts. Fill in what you know and re-run.",
    resume: "Re-run with answers",
    jsonldTitle: "Recommended Product JSON-LD",
    copy: "Copy",
    copied: "Copied",
    askPlaceholder: "Ask the agent, e.g. what should I fix first?",
    ask: "Ask",
    downloadReport: "HTML report",
    copyJson: "Copy JSON",
    footer: "Read-only · no storefront writes · runs on your machine",
    statusReading: "Reading this page…",
    statusAuditing: "Auditing locally…",
    statusRerunning: "Re-running with your answers…",
    statusJsonCopied: "Full JSON result copied.",
    errServer: (server) => `Cannot reach ${server}. Start it with: uv run catalogready dashboard --no-open`,
    errNoPage: "Open a public product page, then click the extension.",
    errNoHtml: "The page HTML could not be read.",
    verdictReady: "Ready for AI shopping agents.",
    verdictPartial: "Partially readable by AI shopping agents.",
    verdictPoor: "Largely invisible or untrustworthy to AI shopping agents.",
    summaryCapped: (cap, reasons) => `Capped at ${cap}: ${reasons}`,
    summaryCritical: (n) => `${n} critical finding${n > 1 ? "s" : ""}.`,
    summaryBlocking: (n) => `${n} blocking merchant question${n > 1 ? "s" : ""}.`,
    summaryAutofix: (n, before, after) =>
      `${n} auto-drafted fix(es): ${before} → ${after} validated.`,
    capBanner: (cap) => `Score capped at ${cap}.`,
    noFindings: "No findings. Everything checked is machine-readable.",
    blocking: "blocking",
    answerPlaceholder: (field) => `Verified ${field}`,
    fixesPending: "Fix suggestions are drafted automatically after the audit.",
    reversible: "reversible",
    validationLine: (before, after) =>
      `Validated preview: ${before} → ${after}. Nothing was written to your store.`,
    error: (message) => `Error: ${message}`,
    helpNeed: "Questions or fix help:",
    keyHint:
      "To use a model provider, add its key to the local server's .env (e.g. OPENAI_API_KEY=…) and restart the server. See docs/BYO-KEYS.md. The audit itself needs no key.",
    pillars: {
      product_identity: "Product identity",
      offer_completeness: "Offer completeness",
      structured_data: "Structured data",
      decision_evidence: "Decision evidence",
      media_variants: "Media & variants",
      claim_grounding: "Claim grounding",
    },
    checks: {
      stable_identifier: "stable identifier (SKU / GTIN / MPN)",
      complete_offer_markup: "complete Offer markup",
      product_node: "Product JSON-LD present",
      valid_json_ld: "JSON-LD parses",
      substantive_page: "120+ words visible",
      evidence_topics: "3+ evidence topics",
      review_evidence: "rating + review count",
      variant_attribute: "variant attribute",
      variant_identity: "variant identifier",
      no_high_risk_claims: "no high-risk claims",
      no_unsupported_claims: "no unsupported claims",
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
    tagline: "AI 就绪评分",
    settings: "设置",
    serverLabel: "本地服务器",
    providerLabel: "提供方",
    providerOffline: "离线 / 确定性",
    modelLabel: "模型 ID",
    modelPlaceholder: "使用服务器默认值",
    settingsNote: "密钥只保存在本地服务器环境变量中，本扩展绝不询问或存储密钥。启动服务器：",
    analyze: "为此商品页面评分",
    findings: "问题清单",
    questions: "商家问题",
    fixes: "修复建议",
    questionsNote: "CatalogReady 绝不编造这些信息。请填写已知的值后重新运行。",
    resume: "带答案重新运行",
    jsonldTitle: "推荐的 Product JSON-LD",
    copy: "复制",
    copied: "已复制",
    askPlaceholder: "向智能体提问，例如：应该先修什么？",
    ask: "提问",
    downloadReport: "HTML 报告",
    copyJson: "复制 JSON",
    footer: "只读 · 不写入店铺 · 在本机运行",
    statusReading: "正在读取当前页面…",
    statusAuditing: "正在本地审计…",
    statusRerunning: "正在带答案重新运行…",
    statusJsonCopied: "完整 JSON 结果已复制。",
    errServer: (server) => `无法连接 ${server}。请先启动：uv run catalogready dashboard --no-open`,
    errNoPage: "请先打开一个公开商品页面，再点击扩展。",
    errNoHtml: "无法读取页面 HTML。",
    verdictReady: "已为 AI 购物助手就绪。",
    verdictPartial: "对 AI 购物助手只部分可读。",
    verdictPoor: "对 AI 购物助手基本不可见或不可信。",
    summaryCapped: (cap, reasons) => `封顶为 ${cap}：${reasons}`,
    summaryCritical: (n) => `${n} 个严重问题。`,
    summaryBlocking: (n) => `${n} 个必答商家问题。`,
    summaryAutofix: (n, before, after) => `已自动生成 ${n} 项修复：验证 ${before} → ${after}。`,
    capBanner: (cap) => `评分封顶为 ${cap}。`,
    noFindings: "没有发现问题，所有检查项均机器可读。",
    blocking: "必填",
    answerPlaceholder: (field) => `已核实的 ${field}`,
    fixesPending: "审计完成后会自动生成修复建议。",
    reversible: "可回滚",
    validationLine: (before, after) => `隔离预览验证：${before} → ${after}。未写入店铺。`,
    error: (message) => `错误：${message}`,
    helpNeed: "问题反馈或修复求助：",
    keyHint:
      "使用模型提供方需在本地服务器的 .env 中配置密钥（如 OPENAI_API_KEY=…）并重启服务器，详见 docs/BYO-KEYS.md。审计本身无需任何密钥。",
    pillars: {
      product_identity: "商品身份",
      offer_completeness: "报价完整性",
      structured_data: "结构化数据",
      decision_evidence: "决策证据",
      media_variants: "图片与变体",
      claim_grounding: "宣称核实",
    },
    checks: {
      stable_identifier: "稳定标识符（SKU / GTIN / MPN）",
      complete_offer_markup: "完整的 Offer 标记",
      product_node: "存在 Product JSON-LD",
      valid_json_ld: "JSON-LD 可解析",
      substantive_page: "可见文本 120 词以上",
      evidence_topics: "3 类以上证据主题",
      review_evidence: "评分及评论数",
      variant_attribute: "变体属性",
      variant_identity: "变体级标识符",
      no_high_risk_claims: "无高风险宣称",
      no_unsupported_claims: "无未证实宣称",
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
    let saved = null;
    try {
      saved = localStorage.getItem("catalogready-lang");
    } catch (error) {
      /* storage unavailable */
    }
    if (saved && I18N[saved]) return saved;
    const browser = (navigator.language || "en").toLowerCase();
    return browser.startsWith("zh") ? "zh" : "en";
  },

  set(lang) {
    if (!I18N[lang]) lang = "en";
    this.lang = lang;
    try {
      localStorage.setItem("catalogready-lang", lang);
    } catch (error) {
      /* storage unavailable */
    }
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    this.applyStatic();
  },

  t(key, ...args) {
    const table = I18N[this.lang] || I18N.en;
    const value = table[key] ?? I18N.en[key] ?? key;
    return typeof value === "function" ? value(...args) : value;
  },

  pillarLabel(key) {
    const table = I18N[this.lang] || I18N.en;
    return table.pillars[key] || I18N.en.pillars[key] || key;
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
  },
};
