const assert = require('node:assert/strict');
const { test } = require('node:test');
const { once } = require('node:events');
const { createServer } = require('../src/app');

test('API responds with health, version, request identity and missing-route status', async () => {
  const server = createServer();
  try {
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const origin = `http://127.0.0.1:${server.address().port}`;
    const health = await fetch(`${origin}/health`);
    assert.equal(health.status, 200);
    assert.deepEqual(await health.json(), { status: 'ok' });
    const response = await fetch(origin);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.version, '1.0.0');
    assert.match(body.requestId, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    assert.equal((await fetch(`${origin}/missing`)).status, 404);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});