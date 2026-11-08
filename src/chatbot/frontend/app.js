/* Assistente Cardiologico Conversacional - cliente do chat */
(function () {
  "use strict";

  const API = ""; // mesma origem do Flask
  const chatEl = document.getElementById("chat");
  const formEl = document.getElementById("composer");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const resetBtn = document.getElementById("resetBtn");
  const quickEl = document.getElementById("quickReplies");
  const engineBadge = document.getElementById("engineBadge");

  let conversationId = localStorage.getItem("cardio_cid");
  if (!conversationId) {
    conversationId =
      (crypto.randomUUID && crypto.randomUUID()) ||
      "cid-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    localStorage.setItem("cardio_cid", conversationId);
  }

  /* ---------- render ---------- */

  function scrollDown() {
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function addMessage(text, who) {
    const div = document.createElement("div");
    div.className = "msg msg--" + who;
    div.textContent = text;
    chatEl.appendChild(div);
    scrollDown();
    return div;
  }

  function addMeta(text) {
    const div = document.createElement("div");
    div.className = "meta";
    div.textContent = text;
    chatEl.appendChild(div);
    scrollDown();
  }

  function classifModifier(classificacao) {
    if (!classificacao) return "GERAL";
    if (classificacao.indexOf("EMERGENCIA") === 0) return "EMERGENCIA";
    if (classificacao.indexOf("PRIORIDADE") === 0) return "PRIORIDADE";
    if (classificacao.indexOf("AVALIACAO ELETIVA") === 0) return "ELETIVA";
    return "GERAL";
  }

  function addSummary(s) {
    if (!s) return;
    const card = document.createElement("div");
    card.className = "summary";

    const rows = [
      ["Paciente", [s.paciente && s.paciente.nome, s.paciente && s.paciente.idade ? s.paciente.idade + " anos" : null].filter(Boolean).join(", ") || "-"],
      ["Queixa principal", s.queixa_principal || "-"],
      ["Sintomas", (s.sintomas && s.sintomas.length ? s.sintomas.join(", ") : "-")],
      ["Intensidade", s.intensidade || "-"],
      ["Duracao", s.duracao || "-"],
      ["Irradiacao", (s.irradiacao && s.irradiacao.length ? s.irradiacao.join(", ") : "-")],
      ["Fatores de risco", (s.fatores_risco && s.fatores_risco.length ? s.fatores_risco.join(", ") : "-")],
      ["Sinais de alarme", (s.sinais_de_alarme && s.sinais_de_alarme.length ? s.sinais_de_alarme.join("; ") : "nenhum identificado")],
    ];

    let html = "<h3>Resumo clinico da triagem</h3><dl>";
    rows.forEach(function (r) {
      html += "<dt>" + r[0] + "</dt><dd>" + escapeHtml(r[1]) + "</dd>";
    });
    html += "</dl>";
    html +=
      '<div class="classif classif--' +
      classifModifier(s.classificacao) +
      '">' +
      escapeHtml(s.classificacao || "") +
      " &mdash; " +
      escapeHtml(s.conduta_sugerida || "") +
      "</div>";

    card.innerHTML = html;
    chatEl.appendChild(card);
    scrollDown();
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function renderQuickReplies(options) {
    quickEl.innerHTML = "";
    (options || []).forEach(function (opt) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = opt;
      b.addEventListener("click", function () {
        send(opt);
      });
      quickEl.appendChild(b);
    });
  }

  /* ---------- rede ---------- */

  function setBusy(busy) {
    sendBtn.disabled = busy;
    inputEl.disabled = busy;
  }

  async function send(text) {
    text = (text || "").trim();
    if (!text) return;

    addMessage(text, "user");
    inputEl.value = "";
    renderQuickReplies([]);
    setBusy(true);

    const typing = addMessage("digitando...", "bot");
    typing.classList.add("msg--typing");

    try {
      const res = await fetch(API + "/api/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, conversation_id: conversationId }),
      });
      const data = await res.json();
      typing.remove();

      if (!res.ok) {
        addMessage("Erro: " + (data.error || res.status), "bot");
        return;
      }

      addMessage(data.reply, "bot");
      if (data.intent) {
        const conf = data.confidence != null ? " (" + Math.round(data.confidence * 100) + "%)" : "";
        const ents =
          data.entities && data.entities.length
            ? " | entities: " + data.entities.map(function (e) { return e.entity + "=" + e.value; }).join(", ")
            : "";
        addMeta("intent: " + data.intent + conf + ents);
      }
      addSummary(data.summary);
      renderQuickReplies(data.options);
      if (data.engine) {
        engineBadge.textContent = "motor: " + data.engine;
      }
    } catch (err) {
      typing.remove();
      addMessage("Nao foi possivel falar com o servidor. O backend esta rodando?", "bot");
    } finally {
      setBusy(false);
      inputEl.focus();
    }
  }

  async function loadHealth() {
    try {
      const res = await fetch(API + "/api/health");
      const data = await res.json();
      engineBadge.textContent = "motor: " + data.engine;
    } catch (e) {
      engineBadge.textContent = "offline";
    }
  }

  async function reset() {
    try {
      await fetch(API + "/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: conversationId }),
      });
    } catch (e) {
      /* ignora */
    }
    chatEl.innerHTML = "";
    renderQuickReplies([]);
    greet();
  }

  function greet() {
    addMessage(
      "Ola! Sou o assistente de triagem inicial em cardiologia. " +
        "Descreva o que voce esta sentindo ou faca uma pergunta sobre sintomas, " +
        "exames, medicamentos ou fatores de risco do coracao.",
      "bot"
    );
    renderQuickReplies(["Estou com dor no peito", "Falta de ar", "Palpitacao", "Tenho uma duvida"]);
  }

  /* ---------- eventos ---------- */

  formEl.addEventListener("submit", function (e) {
    e.preventDefault();
    send(inputEl.value);
  });
  resetBtn.addEventListener("click", reset);

  loadHealth();
  greet();
  inputEl.focus();
})();
