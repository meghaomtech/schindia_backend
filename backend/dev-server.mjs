// Local dev API server — runs the Lambda handler against the real AWS dev DynamoDB table.
// Uses AWS credentials from AWS_PROFILE (or ambient credentials).
//
// Start with:
//   AWS_PROFILE=shichida-setup npm run dev:api
//
// No Docker required. Data goes to ShichidaInvoices-dev in AWS, never production.

import http from 'http';

const PORT = 3001;

// Set env vars BEFORE importing the Lambda — static imports are hoisted
// and would evaluate TABLE_NAME before these assignments run.
process.env.TABLE_NAME = 'ShichidaInvoices-dev';
process.env.AWS_REGION = 'ap-south-1';

const { handler } = await import('./lambda/index.mjs');

async function buildLambdaEvent(req) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathParams = {};
  const match = url.pathname.match(/^\/invoices\/(.+)$/);
  if (match) pathParams.invoiceNumber = decodeURIComponent(match[1]);

  let body = '';
  for await (const chunk of req) body += chunk;

  return {
    requestContext: { http: { method: req.method, path: url.pathname } },
    rawPath: url.pathname,
    pathParameters: Object.keys(pathParams).length ? pathParams : null,
    body: body || null,
  };
}

const server = http.createServer(async (req, res) => {
  try {
    const event = await buildLambdaEvent(req);
    const result = await handler(event);
    Object.entries(result.headers || {}).forEach(([k, v]) => res.setHeader(k, v));
    res.writeHead(result.statusCode);
    res.end(result.body ?? '');
  } catch (e) {
    console.error('Dev server error:', e.message);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: e.message }));
  }
});

server.listen(PORT, () => {
  console.log(`\n  ✅  Local API → http://localhost:${PORT}`);
  console.log(`      DynamoDB table : ShichidaInvoices-dev (AWS ap-south-1)`);
  console.log(`      Profile        : ${process.env.AWS_PROFILE ?? 'default'}\n`);
});
