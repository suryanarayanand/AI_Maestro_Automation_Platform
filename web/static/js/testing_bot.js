(() => {
  const form = document.getElementById("testingBotForm"); if (!form) return;
  const input = document.getElementById("testingBotQuestion"), messages = document.getElementById("botMessages"), clear = document.getElementById("clearTestingBot");
  const add = (text, role) => { const node = document.createElement("div"); node.className = `bot-message ${role}`; node.textContent = text; messages.appendChild(node); messages.scrollTop = messages.scrollHeight; };
  form.addEventListener("submit", async (event) => { event.preventDefault(); const question = input.value.trim(); if (!question) return; add(question, "user"); input.value = ""; const response = await fetch("/api/testing-bot/ask", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({question})}); const data = await response.json(); add(data.answer || data.error || "The bot could not answer.", "assistant"); });
  clear.addEventListener("click", async () => { if (!window.confirm("Clear this conversation? Testing knowledge will be preserved.")) return; const response = await fetch("/api/testing-bot/clear", {method: "POST"}); if (!response.ok) return; messages.replaceChildren(); add("Chat cleared. App Memory, locators, YAML knowledge, and run history were preserved.", "assistant"); });
})();
