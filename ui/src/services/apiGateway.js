const configuredGatewayUrl = import.meta.env.VITE_API_BASE_URL?.trim()
const defaultGatewayUrl = import.meta.env.DEV || import.meta.env.MODE === 'kubernetes'
  ? 'http://localhost:8090'
  : ''
const gatewayBaseUrl = (configuredGatewayUrl || defaultGatewayUrl)
  .replace(/\/$/, '')
  .replace(/^http:\/\/localhost$/, 'http://localhost:8090')

export function enableApiGatewayRouting() {
  if (!gatewayBaseUrl || typeof window === 'undefined') return

  const originalFetch = window.fetch.bind(window)
  window.fetch = (input, init) => {
    const requestUrl = typeof input === 'string'
      ? new URL(input, window.location.origin)
      : input instanceof URL
        ? input
        : null
    const isLocalApiRequest = requestUrl?.hostname === 'localhost'
      && (requestUrl.port === '' || /^808[0-7]$/.test(requestUrl.port))
      && requestUrl.pathname.startsWith('/api/')
    if (isLocalApiRequest) {
      input = `${gatewayBaseUrl}${requestUrl.pathname}${requestUrl.search}`
    }

    return originalFetch(input, init)
  }
}
