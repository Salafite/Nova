window.ScheduledTaskModel = class ScheduledTaskModel {
  constructor(data) {
    this.id = data.id
    this.taskName = data.taskName
    this.taskType = data.taskType
    this.cronExpression = data.cronExpression
    this.description = data.description || ''
    this.config = data.config || {}
    this.isActive = data.isActive !== false
    this.lastRunAt = data.lastRunAt || null
    this.nextRunAt = data.nextRunAt || null
    this.status = data.status || 'Idle'
    this.createdAt = data.createdAt
    this.createdBy = data.createdBy
    this.updatedAt = data.updatedAt
    this.updatedBy = data.updatedBy
    this.updateNumber = data.updateNumber || 1
  }
}
