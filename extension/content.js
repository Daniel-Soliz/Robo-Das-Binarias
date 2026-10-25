(() => {
  if (document.getElementById("ds-trader-panel")) {
    document.getElementById("ds-trader-panel").remove();
    return;
  }
  const host = document.createElement("div");
  host.id = "ds-trader-panel";
  host.style.cssText = "position:fixed;top:90px;right:18px;z-index:2147483647;width:245px;background:#0b1020;color:#f5f7ff;border:1px solid #2b3c5e;border-radius:14px;box-shadow:0 12px 40px #0008;font:14px/1.4 system-ui,Arial,sans-serif;padding:15px";
  host.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
      <strong style="font-size:16px;letter-spacing:1px">DS TRADER</strong>
      <button id="ds-close" aria-label="Fechar" style="background:transparent;color:#9eabc4;border:0;font-size:20px;cursor:pointer">×</button>
    </div>
    <div style="font-size:10px;color:#91b6ff;margin:8px 0 12px">ANÁLISE M5 · HORIZONTE 1 MIN</div>
    <div id="ds-state" style="border-radius:10px;background:#18243b;padding:17px 8px;text-align:center;font-weight:800;font-size:22px">AGUARDANDO</div>
    <p style="font-size:11px;color:#aab5cc;margin:12px 0 0">Protótipo de interface. Leitura do gráfico e probabilidades ainda não validadas; nenhum sinal real está sendo calculado.</p>
  `;
  document.documentElement.appendChild(host);
  host.querySelector("#ds-close").addEventListener("click", () => host.remove());
})();
