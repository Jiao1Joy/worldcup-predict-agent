import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const viteCli = fileURLToPath(new URL('../node_modules/vite/bin/vite.js', import.meta.url));
const playwrightCli = require.resolve('@playwright/test/cli');
const isWindows = process.platform === 'win32';

const server = spawn(
  process.execPath,
  [viteCli, '--host', '127.0.0.1', '--port', '4173'],
  {
    stdio: 'ignore',
    windowsHide: true,
    detached: !isWindows,
  },
);

async function waitForServer() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch('http://127.0.0.1:4173');
      if (response.ok) return;
    } catch {
      // Vite is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('Vite did not start on port 4173 within 30 seconds');
}

async function stopServer() {
  if (!server.pid || server.exitCode !== null) return;
  if (isWindows) {
    server.kill();
    server.unref();
  } else {
    process.kill(-server.pid, 'SIGTERM');
  }
}

async function stopProcessTree(child) {
  if (!child.pid || child.exitCode !== null) return;
  if (isWindows) {
    child.kill();
    child.unref();
  } else {
    process.kill(-child.pid, 'SIGTERM');
  }
}

let exitCode = 1;
try {
  await waitForServer();
  const tests = spawn(process.execPath, [playwrightCli, 'test'], {
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
    detached: true,
  });
  let output = '';
  const summary = new Promise((resolve) => {
    const forward = (target) => (chunk) => {
      target.write(chunk);
      output = `${output}${chunk}`.slice(-8_000).replace(/\x1b\[[0-9;]*m/g, '');
      if (/\b\d+ failed\b/.test(output)) resolve(1);
      else if (/\b\d+ passed\b/.test(output)) resolve(0);
    };
    tests.stdout.on('data', forward(process.stdout));
    tests.stderr.on('data', forward(process.stderr));
  });
  const closed = new Promise((resolve) => tests.once('close', resolve));
  exitCode = await Promise.race([closed, summary]);
  await stopProcessTree(tests);
} finally {
  await stopServer();
}

process.exit(typeof exitCode === 'number' ? exitCode : 1);
