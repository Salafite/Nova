export function getSessionHash() {
  const token = localStorage.getItem('nova_token')
  if (!token) return ''
  let hash = 0
  for (let i = 0; i < token.length; i++) {
    const ch = token.charCodeAt(i)
    hash = ((hash << 5) - hash) + ch
    hash |= 0
  }
  return Math.abs(hash).toString(36).substring(0, 8)
}
