// Capture the real Ingress UI with installed Chrome; no browser package or mock page.
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
const url = process.argv[2] || 'http://rahbar.local:18085';
const target = path.resolve('docs/evidence/platform/P04/ui.png');
const profile = path.resolve('.venv/rahbar-browser-' + Date.now());
const executable = process.env.CHROME_BIN || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
fs.mkdirSync(profile, {recursive:true});
const chrome = spawn(executable, ['--headless=new','--no-first-run','--no-default-browser-check',
  '--no-proxy-server','--host-resolver-rules=MAP rahbar.local 127.0.0.1','--remote-debugging-port=0',
  '--user-data-dir='+profile,'about:blank'], {windowsHide:true,stdio:'ignore'});
let socket;
(async () => {
  let port;
  for (let i=0;i<100;i++) {
    const file = path.join(profile,'DevToolsActivePort');
    if (fs.existsSync(file)) { port = fs.readFileSync(file,'utf8').split('\n')[0]; break; }
    await wait(100);
  }
  assert(port, 'Chrome DevTools did not start');
  const response = await fetch(`http://127.0.0.1:${port}/json/new?${url}`,{method:'PUT'});
  const page = await response.json();
  socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve,reject) => {socket.onopen=resolve;socket.onerror=reject;});
  let sequence=0;
  const pending = new Map();
  socket.onmessage = event => {
    const message=JSON.parse(event.data);
    if (pending.has(message.id)) {pending.get(message.id)(message);pending.delete(message.id);}
  };
  const call = (method,params={}) => new Promise((resolve,reject) => {
    const id=++sequence;
    const timer=setTimeout(()=>reject(Error('CDP timeout: '+method)),30000);
    pending.set(id,message=>{clearTimeout(timer);message.error?reject(Error(JSON.stringify(message.error))):resolve(message.result);});
    socket.send(JSON.stringify({id,method,params}));
  });
  await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1000,deviceScaleFactor:1,mobile:false});
  await call('Page.enable');
  await call('Page.navigate',{url});
  for (let i=0;i<100;i++) {
    const ready=await call('Runtime.evaluate',{expression:'!!document.getElementById("question")',returnByValue:true});
    if (ready.result.value) break;
    await wait(100);
  }
  await call('Runtime.evaluate',{expression:'document.getElementById("question").value="What is the last date to withdraw from a course under the current academic rules?"; document.getElementById("ask").requestSubmit();'});
  let answer;
  for (let i=0;i<180;i++) {
    const result=await call('Runtime.evaluate',{expression:'document.querySelector(".a .text")?.textContent || ""',returnByValue:true});
    if (result.result.value) {answer=result.result.value;break;}
    await wait(1000);
  }
  assert(answer && answer.includes('academic-rules-handbook'), 'Screenshot needs an actual cited answer');
  const screenshot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,Buffer.from(screenshot.data,'base64'));
  fs.writeFileSync(target.replace('.png','.json'),JSON.stringify({url,answer,screenshot:target,source:'Actual headless Chrome page through Kubernetes Ingress'},null,2));
  console.log('Captured actual cited UI:',target);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{if(socket)socket.close();chrome.kill();});
