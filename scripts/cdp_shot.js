/**
 * cdp_shot.js — 用 CDP 协议驱动 Edge 做真·移动设备模拟截图/测量
 * 用法: node cdp_shot.js <url> <width> <height> <dsf> <out.png> [--eval <js>]
 * 说明: Edge headless 的 --window-size 有 ~492px 最小视口限制，无法真正模拟手机；
 *       本脚本通过 Emulation.setDeviceMetricsOverride 设置真实视口（含 mobile=true，
 *       触发 viewport meta），再 Page.captureScreenshot，或 Runtime.evaluate 取布局数据。
 * 依赖: ws（装在 C:\Users\99432\.workbuddy\binaries\node\workspace\node_modules）
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const WebSocket = require('ws');

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const PORT = 9333;

const [url, w, h, dsf, out, ...rest] = process.argv.slice(2);
const width = parseInt(w || '375', 10);
const height = parseInt(h || '812', 10);
const scale = parseFloat(dsf || '2');
const evalIdx = rest.indexOf('--eval');
const evalJs = evalIdx >= 0 ? rest.slice(evalIdx + 1).join(' ') : null;

if (!url || !out) {
  console.error('usage: node cdp_shot.js <url> <width> <height> <dsf> <out.png> [--eval <js>]');
  process.exit(1);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const edge = spawn(EDGE, [
    '--headless=new', '--no-sandbox', '--disable-gpu',
    `--remote-debugging-port=${PORT}`,
    '--user-data-dir=' + path.join(require('os').tmpdir(), 'cdp-edge-profile'),
    'about:blank',
  ], { stdio: 'ignore', detached: true });

  let wsUrl = null;
  for (let i = 0; i < 40; i++) {
    await sleep(250);
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const targets = await res.json();
      const page = targets.find((t) => t.type === 'page');
      if (page) { wsUrl = page.webSocketDebuggerUrl; break; }
    } catch (e) { /* 还没起来 */ }
  }
  if (!wsUrl) { console.error('CDP endpoint not found'); process.exit(1); }

  const ws = new WebSocket(wsUrl, { perMessageDeflate: false });
  let msgId = 0;
  const pending = new Map();
  ws.on('message', (data) => {
    const m = JSON.parse(data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++msgId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });

  await new Promise((r) => ws.on('open', r));
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width, height, deviceScaleFactor: scale, mobile: true,
    screenWidth: width, screenHeight: height,
  });

  const loaded = new Promise((resolve) => {
    const onLoad = (data) => {
      const m = JSON.parse(data);
      if (m.method === 'Page.loadEventFired') { ws.off('message', onLoad); resolve(); }
    };
    ws.on('message', onLoad);
    setTimeout(resolve, 15000); // 兜底超时
  });
  await send('Page.navigate', { url });
  await loaded;
  await sleep(600); // 等字体/图片稳定

  if (evalJs) {
    const r = await send('Runtime.evaluate', { expression: evalJs, returnByValue: true });
    console.log(r.result.value);
  }

  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
  console.log('saved: ' + out + ' (' + width + 'x' + height + ' @' + scale + 'x)');

  ws.close();
  try { process.kill(edge.pid); } catch (e) { /* ignore */ }
}

main().catch((e) => { console.error('FAIL: ' + (e && e.stack || e)); process.exit(1); });
