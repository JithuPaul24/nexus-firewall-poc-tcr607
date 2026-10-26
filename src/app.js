const http = require('node:http');
const { v4: uuid } = require('uuid');
const { version } = require('../package.json');

function createServer() {
  return http.createServer((request, response) => {
    response.setHeader('Content-Type', 'application/json');
    if (request.url === '/health') {
      response.end(JSON.stringify({ status: 'ok' }));
      return;
    }
    if (request.url === '/') {
      response.end(JSON.stringify({ application: 'nexus-lifecycle-sbom-poc', version, requestId: uuid() }));
      return;
    }
    response.statusCode = 404;
    response.end(JSON.stringify({ error: 'Not found' }));
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT || 8080);
  createServer().listen(port, '0.0.0.0', () => console.log(`Listening on port ${port}`));
}

module.exports = { createServer };