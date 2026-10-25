document.getElementById("open").addEventListener("click", async () => {
  const status = document.getElementById("status");
  try {
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab?.id || !/^https?:/.test(tab.url || "")) {
      status.textContent = "Abra uma página web compatível e tente novamente.";
      return;
    }
    await chrome.scripting.executeScript({target:{tabId:tab.id},files:["content.js"]});
    status.textContent = "Painel solicitado. Confira a aba do gráfico.";
    window.close();
  } catch (e) {
    status.textContent = "Não foi possível abrir o painel nesta página. Atualize a aba e tente novamente.";
  }
});
