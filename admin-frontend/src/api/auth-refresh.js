export function shouldRefreshAuth(error) {
  const headers = error.config?.headers
  const authorization = typeof headers?.get === 'function'
    ? headers.get('Authorization')
    : headers?.Authorization || headers?.authorization

  return error.response?.status === 401 && Boolean(authorization) && !error.config?._retry
}
