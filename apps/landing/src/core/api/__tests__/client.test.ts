/**
 * Regression tests for API error surfacing: the backend wraps errors in a
 * structured envelope ({ success, error: { code, message } }), so the client
 * must surface `error.message` instead of a generic "HTTP Error 4xx" string.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { apiClient, ApiError } from '../client';

function httpResponse(status: number, body: string, contentType = 'application/json'): Response {
  return new Response(body, {
    status,
    headers: { 'Content-Type': contentType },
  });
}

async function expectApiError(request: Promise<unknown>): Promise<ApiError> {
  try {
    await request;
  } catch (err) {
    expect(err).toBeInstanceOf(ApiError);
    return err as ApiError;
  }
  throw new Error('Expected the request to fail with an ApiError');
}

describe('apiClient error surfacing', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('surfaces the structured envelope error.message on HTTP 400', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        httpResponse(
          400,
          JSON.stringify({
            success: false,
            error: { code: 'HTTP_400', message: 'PayPal capture failed' },
            meta: { request_id: 'req-1', timestamp: '2026-08-21T00:00:00Z' },
          }),
        ),
      ),
    );

    const err = await expectApiError(
      apiClient.post('/api/v1/billing/capture/00000000-0000-4000-8000-000000000000'),
    );

    expect(err.status).toBe(400);
    expect(err.message).toBe('PayPal capture failed');
  });

  it('falls back to the generic HTTP message when the body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => httpResponse(400, '<html>Bad Request</html>', 'text/html')),
    );

    const err = await expectApiError(apiClient.get('/api/v1/billing/plans'));

    expect(err.status).toBe(400);
    expect(err.message).toBe('HTTP Error 400');
  });
});
