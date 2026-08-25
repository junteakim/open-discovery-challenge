(() => {
  const app = document.querySelector(".app");
  const feed = document.getElementById("feed");
  const statusText = document.getElementById("status-text");
  const lineCount = document.getElementById("line-count");
  const searchInput = document.getElementById("search");

  let partialEl = null;
  let allLines = [];
  let glossaryTerms = [];
  let currentStrategies = null;

  // Tabs
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
    });
  });

  // Strategy tabs (MeetU-style 3 replies)
  document.querySelectorAll(".strategy").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!currentStrategies) return;
      document.querySelectorAll(".strategy").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const s = currentStrategies[btn.dataset.strategy];
      if (s) {
        document.getElementById("suggestion-text").innerHTML = highlightTerms(s.reply);
        document.getElementById("suggestion-native").textContent = s.reply_native || "";
      }
    });
  });

  // Compose chips
  document.querySelectorAll("[data-compose]").forEach((chip) => {
    chip.addEventListener("click", async () => {
      chip.disabled = true;
      await fetch("/compose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: chip.dataset.compose }),
      });
      chip.disabled = false;
      document.querySelector('[data-tab="compose"]').click();
    });
  });

  // Copy buttons
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const el = document.getElementById(btn.dataset.copy);
      if (el) navigator.clipboard.writeText(el.textContent || "");
      btn.textContent = "✓";
      setTimeout(() => { btn.textContent = "⎘"; }, 1200);
    });
  });

  // Search
  searchInput?.addEventListener("input", () => {
    const q = searchInput.value.trim().toLowerCase();
    feed.querySelectorAll(".line:not(.partial)").forEach((line) => {
      const text = line.textContent.toLowerCase();
      line.classList.toggle("hidden-by-search", q && !text.includes(q));
    });
  });

  function highlightTerms(text) {
    if (!text || !glossaryTerms.length) return escapeHtml(text);
    let out = escapeHtml(text);
    const sorted = [...glossaryTerms].sort((a, b) => b.length - a.length);
    for (const term of sorted) {
      if (term.length < 2) continue;
      const re = new RegExp(`(${escapeRegex(term)})`, "gi");
      out = out.replace(re, "<mark>$1</mark>");
    }
    return out;
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function langBadge(lang) {
    const cls = lang === "ko" ? "lang-ko" : "lang-en";
    return `<span class="badge ${cls}">${lang || "?"}</span>`;
  }

  function addLine(text, translated, lang, targetLang, partial) {
    if (partial) {
      if (!partialEl) {
        partialEl = document.createElement("article");
        partialEl.className = "line partial";
        partialEl.innerHTML = `<div class="line-meta">${langBadge(lang)}<span class="badge">live</span></div><div class="src"></div><div class="tr"></div>`;
        feed.prepend(partialEl);
      }
      partialEl.querySelector(".src").textContent = text;
      partialEl.querySelector(".tr").innerHTML = highlightTerms(translated === "…" ? "…" : translated);
      return;
    }
    partialEl = null;
    const el = document.createElement("article");
    el.className = "line";
    el.dataset.text = (text + " " + translated).toLowerCase();
    el.innerHTML = `
      <div class="line-meta">${langBadge(lang)}<span class="badge">→ ${targetLang || ""}</span></div>
      <div class="src">${escapeHtml(text)}</div>
      <div class="tr">${highlightTerms(translated)}</div>`;
    feed.prepend(el);
    allLines.push({ text, translated });
    lineCount.textContent = `${allLines.length} lines`;
  }

  function showSuggestion(msg) {
    const card = document.getElementById("suggestion-card");
    const tabs = document.getElementById("strategy-tabs");
    card.classList.remove("hidden");
    currentStrategies = msg.strategies || null;
    if (currentStrategies) {
      tabs.classList.remove("hidden");
      document.querySelectorAll(".strategy").forEach((b) => {
        b.classList.toggle("active", b.dataset.strategy === "diplomatic");
      });
    } else {
      tabs.classList.add("hidden");
    }
    document.getElementById("suggestion-text").innerHTML = highlightTerms(msg.reply);
    document.getElementById("suggestion-native").textContent = msg.reply_native || "";
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function showMention(msg) {
    const banner = document.getElementById("mention-banner");
    const titles = { name: "이름 호출", question: "질문 감지", request: "요청 감지" };
    document.getElementById("mention-title").textContent = titles[msg.kind] || "알림";
    document.getElementById("mention-text").textContent = msg.text || "";
    banner.classList.remove("hidden");
    setTimeout(() => banner.classList.add("hidden"), 8000);
  }

  function renderGlossary(items) {
    const el = document.getElementById("glossary");
    if (!items?.length) {
      el.innerHTML = '<p class="empty" style="padding:8px">ontology.json에 용어를 추가하세요</p>';
      return;
    }
    el.innerHTML = items.map((t) =>
      `<div class="glossary-item"><strong>${escapeHtml(t.term)}</strong><br><span>${escapeHtml(t.definition || "")}</span></div>`
    ).join("");
    glossaryTerms = items.flatMap((t) => [t.term, ...(t.aliases || [])]).filter(Boolean);
  }

  // Load glossary
  fetch("/glossary").then((r) => r.json()).then(renderGlossary).catch(() => {});

  const es = new EventSource("/stream");
  es.onopen = () => {
    app.dataset.state = "live";
    statusText.textContent = "실시간";
  };
  es.onerror = () => {
    app.dataset.state = "connecting";
    statusText.textContent = "재연결…";
  };

  es.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "segment") {
      addLine(msg.text, msg.translated, msg.lang, msg.target_lang, msg.partial);
      return;
    }
    if (msg.type === "brief") {
      document.getElementById("brief-text").textContent = msg.brief || "";
      const hl = document.getElementById("highlights");
      hl.innerHTML = (msg.highlights || [])
        .map((h) => `<span class="highlight">${escapeHtml(h)}</span>`)
        .join("");
      return;
    }
    if (msg.type === "suggestion") {
      showSuggestion(msg);
      return;
    }
    if (msg.type === "mention") {
      showMention(msg);
      return;
    }
    if (msg.type === "compose") {
      document.getElementById("compose-text").innerHTML = highlightTerms(msg.reply);
      document.getElementById("compose-native").textContent = msg.reply_native || "";
    }
  };
})();
