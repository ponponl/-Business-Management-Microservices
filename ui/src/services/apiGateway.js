const gatewayBaseUrl = import.meta.env.MODE === 'kubernetes'
  ? 'http://localhost:8090'
  : ''

export function enableApiGatewayRouting() {
  if (!gatewayBaseUrl || typeof window === 'undefined') return

  const originalFetch = window.fetch.bind(window)
  window.fetch = (input, init) => {
    if (typeof input === 'string') {
      const requestUrl = new URL(input, window.location.origin)
      const isLocalApiRequest = requestUrl.hostname === 'localhost'
        && (requestUrl.port === '' || /^808[0-7]$/.test(requestUrl.port))
        && requestUrl.pathname.startsWith('/api/')
      if (isLocalApiRequest) {
        input = `${gatewayBaseUrl}${requestUrl.pathname}${requestUrl.search}`
      }
    }

    return originalFetch(input, init)
  }
}
