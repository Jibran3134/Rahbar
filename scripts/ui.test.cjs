// Native node tests: no UI build step or third-party browser dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Node {
  constructor() { this.children = []; this.disabled = false; this.listeners = {}; }
  setAttribute() {}
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren() { this.children = []; }
  addEventListener(event, fn) { this.listeners[event] = fn; }
  remove() {}
  scrollIntoView() {}
  focus() {}
  set innerHTML(_) { throw Error('Untrusted markup must never execute'); }
}
const elements = Object.fromEntries(['thread','ask','question','send','new-chat','query-mode','mode-help'].map(id => [id,new Node()]));
elements['query-mode'].value = 'independent';
const calls = [];
const context = vm.createContext({
  URLSearchParams, location: {search:'',origin:'http://test'}, window: {},
  document: {getElementById: id => elements[id],createElement: () => new Node()},
  fetch: async (_, options) => {
    calls.push(JSON.parse(options.body));
    return {ok:true,json:async () => ({session_id:'server_session_1',answer:'<script>unsafe</script>',citations:[]}),
      headers:{get:()=>'BYPASS'}};
  }
});
const html = fs.readFileSync('ui/index.html','utf8');
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async () => {
  await vm.runInContext('ask("First question")',context);
  await vm.runInContext('ask("First question")',context);
  assert.equal(calls[0].session_id,undefined);
  assert.equal(calls[1].session_id,undefined, 'Independent repeats must be eligible for cache without resetting the thread');
  elements['query-mode'].value = 'conversation';
  elements['query-mode'].listeners.change();
  assert.match(elements['mode-help'].textContent,/bypass cache/);
  await vm.runInContext('ask("And the old policy?")',context);
  assert.equal(calls[2].session_id,'server_session_1');
  elements['new-chat'].listeners.click();
  await vm.runInContext('ask("New independent question")',context);
  assert.equal(calls[3].session_id,undefined);
  assert.equal(elements['query-mode'].disabled,false);
  assert.match(JSON.stringify(elements.thread.children),/No verified answer/);
  const timeoutCard=vm.runInContext('renderAnswer({answered_from_context:false,answer:"Could not verify"},"MISS","generation_timeout")',context);
  assert.match(JSON.stringify(timeoutCard),/model reached its time limit/);
  console.log('PASS: independent repeats omit history, conversation reuses server session, reset works, output stays text');
})().catch(error => { console.error(error); process.exitCode=1; });
