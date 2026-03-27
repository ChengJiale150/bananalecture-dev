import { NextRequest } from 'next/server';

const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'content-length',
  'host',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

function getBackendBaseUrl() {
  const baseUrl = process.env.BANANA_LECTURE_API_BASE_URL;
  if (!baseUrl) {
    throw new Error('Missing BANANA_LECTURE_API_BASE_URL');
  }
  return baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
}

function buildUpstreamUrl(request: NextRequest, pathSegments: string[]) {
  const baseUrl = getBackendBaseUrl();
  const upstreamUrl = new URL(`${baseUrl}/api/v1/${pathSegments.join('/')}`);
  upstreamUrl.search = request.nextUrl.search;
  return upstreamUrl;
}

function forwardHeaders(request: NextRequest) {
  const headers = new Headers();

  request.headers.forEach((value, key) => {
    if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) return;
    headers.set(key, value);
  });

  return headers;
}

async function proxyRequest(request: NextRequest, pathSegments: string[]) {
  let upstreamUrl: URL;

  try {
    upstreamUrl = buildUpstreamUrl(request, pathSegments);
  } catch (error) {
    return Response.json(
      {
        code: 500,
        message: error instanceof Error ? error.message : 'Proxy configuration error',
        data: null,
      },
      { status: 500 },
    );
  }

  const body =
    request.method === 'GET' || request.method === 'HEAD'
      ? undefined
      : await request.arrayBuffer();

  let upstreamResponse: Response;

  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: forwardHeaders(request),
      body,
      redirect: 'manual',
    });
  } catch (error) {
    return Response.json(
      {
        code: 502,
        message: error instanceof Error ? error.message : 'Failed to reach upstream API',
        data: null,
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  upstreamResponse.headers.forEach((value, key) => {
    if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) return;
    responseHeaders.set(key, value);
  });

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: responseHeaders,
  });
}

type RouteContext = {
  params: Promise<{
    path: string[];
  }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRequest(request, path);
}
