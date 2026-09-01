(() => {
  const panel = document.getElementById("fridayPanel");
  if (!panel) return;
  const launcher = document.getElementById("fridayLauncher");
  const close = document.getElementById("fridayClose");
  const backdrop = document.getElementById("fridayBackdrop");
  const messages = document.getElementById("fridayMessages");
  const form = document.getElementById("fridayForm");
  const input = document.getElementById("fridayQuestion");
  const status = document.getElementById("fridayStatus");
  let historyLoaded = false;
  const add = (text, role) => {
    const node = document.createElement("div"); node.className = `friday-message ${role}`;
    node.textContent = text; messages.appendChild(node); messages.scrollTop = messages.scrollHeight;
  };
  const loadHistory = async () => {
    if (historyLoaded) return; historyLoaded = true;
    try {
      const response = await fetch("/api/testing-bot/history"); const data = await response.json();
      if (data.messages?.length) { messages.replaceChildren(); data.messages.forEach(item => add(item.message, item.role)); }
    } catch (_) { status.textContent = "History unavailable; new questions still work."; }
  };
  const open = () => { panel.classList.add("open"); panel.setAttribute("aria-hidden", "false"); launcher.setAttribute("aria-expanded", "true"); backdrop.hidden = false; loadHistory(); setTimeout(() => input.focus(), 180); };
  const shut = () => { panel.classList.remove("open"); panel.setAttribute("aria-hidden", "true"); launcher.setAttribute("aria-expanded", "false"); backdrop.hidden = true; };
  launcher.addEventListener("click", open); close.addEventListener("click", shut); backdrop.addEventListener("click", shut);
  document.addEventListener("keydown", event => { if (event.key === "Escape") shut(); });
  document.getElementById("fridaySuggestions").addEventListener("click", event => { if (event.target.tagName === "BUTTON") { input.value = event.target.textContent; form.requestSubmit(); } });
  form.addEventListener("submit", async event => {
    event.preventDefault(); const question = input.value.trim(); if (!question) return;
    add(question, "user"); input.value = ""; input.disabled = true; status.classList.add("thinking"); status.textContent = "Friday is checking portal evidence…";
    try {
      const response = await fetch("/api/testing-bot/ask", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question})});
      const data = await response.json(); add(data.answer || data.error || "I could not produce a grounded answer.", "assistant");
      const evidenceCount = Array.isArray(data.evidence) ? data.evidence.length : (data.evidence && typeof data.evidence === "object" ? Object.keys(data.evidence).length : 0);
      status.textContent = evidenceCount ? `Grounded with ${evidenceCount} evidence reference${evidenceCount === 1 ? "" : "s"}.` : "No matching evidence was found.";
    } catch (_) { add("The portal assistant is temporarily unavailable.", "assistant"); status.textContent = "Connection failed."; }
    finally { input.disabled = false; status.classList.remove("thinking"); input.focus(); }
  });
})();
