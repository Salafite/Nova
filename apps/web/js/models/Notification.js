window.NotificationModel = class NotificationModel {
  constructor(data) {
    this.id = data.id
    this.userId = data.userId
    this.title = data.title
    this.message = data.message || ''
    this.notificationType = data.notificationType || 'Info'
    this.referenceType = data.referenceType || null
    this.referenceId = data.referenceId || null
    this.isRead = data.isRead || false
    this.createdAt = data.createdAt
  }
}
