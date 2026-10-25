// Execute com: node extension/engine.test.js
const assert = require("node:assert/strict");
require("./engine.js");
const {validCandles,sma,rsi,detectPatterns,analyze}=globalThis.DSTraderEngine;
assert.equal(sma([1,2,3,4],3),3);
assert.equal(rsi(Array.from({length:16},(_,i)=>i+1),14),100);
assert.equal(validCandles([]),false);
assert.equal(analyze([]).state,"AGUARDANDO");
const candles=[];
for(let i=0;i<40;i++){
 const close=100+i;
 candles.push({open:close-0.2,high:close+0.5,low:close-0.5,close});
}
const result=analyze(candles);
assert.equal(result.state,"CALL");
assert.equal(result.probability,null);

const engulfing=[
 {open:10,high:10.5,low:7.5,close:8},
 {open:7.8,high:10.5,low:7.5,close:10.2}
];
assert.ok(detectPatterns(engulfing).some(p=>p.name==="engolfo_de_alta" && p.direction==="CALL"));
const doji=[
 {open:10,high:11,low:9,close:10.5},
 {open:10.2,high:11,low:9,close:10.21}
];
assert.ok(detectPatterns(doji).some(p=>p.name==="doji" && p.direction==="NEUTRO"));
console.log("DS Trader engine: testes básicos e padrões passaram.");
