window.NotificationService = class NotificationService {
  constructor() {
    this.api = new ApiClient('T0098I')
    this._notifications = []
  }

  async load() {
    try {
      this._notifications = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load notifications', e)
      this._notifications = []
    }
  }

  getAll() { return this._notifications }

  async markRead(id) {
    await fetch(this.api.base + '/' + id + '/read', { method: 'PUT', headers: this.api._headers() })
    var n = this._notifications.find(function(x) { return x.id === id })
    if (n) n.isRead = true
  }

  async markAllRead(userId) {
    await fetch(this.api.base + '/read-all/' + userId, { method: 'PUT', headers: this.api._headers() })
    this._notifications.forEach(function(n) { n.isRead = true })
  }

  getUnreadCount() {
    return this._notifications.filter(function(n) { return !n.isRead }).length
  }
}
