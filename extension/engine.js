/*
 * DS Trader — motor técnico experimental.
 * Recebe candles OHLC já fechados; não coleta dados do site nem executa ordens.
 * Não converte score em probabilidade: isso exige validação histórica fora da amostra.
 */
(() => {
  const finite = n => Number.isFinite(Number(n));
  function validCandles(candles, min=30) {
    if (!Array.isArray(candles) || candles.length < min) return false;
    return candles.every(c => c && ["open","high","low","close"].every(k=>finite(c[k])) &&
      Number(c.high) >= Math.max(Number(c.open),Number(c.close),Number(c.low)) &&
      Number(c.low) <= Math.min(Number(c.open),Number(c.close),Number(c.high)));
  }
  function sma(values, period) {
    if(values.length < period) return null;
    const s=values.slice(-period);
    return s.reduce((a,b)=>a+b,0)/period;
  }
  function rsi(closes, period=14) {
    if(closes.length < period+1) return null;
    let gains=0, losses=0;
    for(let i=closes.length-period;i<closes.length;i++){
      const d=closes[i]-closes[i-1]; if(d>0) gains+=d; else losses-=d;
    }
    if(losses===0) return gains===0 ? 50 : 100;
    return 100-(100/(1+gains/losses));
  }
  function analyze(candles) {
    if(!validCandles(candles)) return {state:"AGUARDANDO",reason:"Dados OHLC insuficientes ou inválidos.",score:null,probability:null};
    const closes=candles.map(c=>Number(c.close));
    const last=candles[candles.length-1], prev=candles[candles.length-2];
    const fast=sma(closes,9), slow=sma(closes,21), r=rsi(closes,14);
    if(fast===null||slow===null||r===null) return {state:"AGUARDANDO",reason:"Histórico insuficiente para indicadores.",score:null,probability:null};
    let score=0;
    if(fast>slow) score+=1; else if(fast<slow) score-=1;
    if(last.close>last.open) score+=0.5; else if(last.close<last.open) score-=0.5;
    if(last.close>prev.close) score+=0.5; else if(last.close<prev.close) score-=0.5;
    if(r<35) score+=0.5; else if(r>65) score-=0.5;
    const state=score>=1.5?"CALL":score<=-1.5?"PUT":"ANALISANDO";
    return {state,reason:"Score técnico experimental; não é probabilidade nem garantia.",score,probability:null,
      indicators:{sma9:fast,sma21:slow,rsi14:r},lastClosedCandle:{open:Number(last.open),high:Number(last.high),low:Number(last.low),close:Number(last.close)}};
  }
  globalThis.DSTraderEngine={validCandles, sma, rsi, analyze};
})();
