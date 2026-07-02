window.JournalEntryModel = class JournalEntry {
  constructor(fields) {
    this.id = fields.id || 0
    this.entryDate = fields.entryDate || new Date().toISOString().split('T')[0]
    this.reference = fields.reference || ''
    this.description = fields.description || ''
    this.status = fields.status || 'Draft'
    this.lines = fields.lines || []
  }
}
