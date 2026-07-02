class SupplierClient {
  constructor() {
    this.api = new ApiClient('T0011I')
    this._cache = []
  }

  async load() {
    this._cache = (await this.api.list()) || []
  }

  getAll() { return this._cache }

  getById(id) {
    return this._cache.find(s => String(s.id) === String(id))
  }

  async add(name, email, phone, paymentTerms) {
    const supplier = await this.api.create({ name: name, email: email || '', phone: phone || '', paymentTerms: paymentTerms || 'Net 30' })
    this._cache.push(supplier)
    return supplier
  }

  async update(id, name, email, phone, paymentTerms) {
    const s = this.getById(id)
    if (!s) return null
    if (name !== undefined) s.name = name
    if (email !== undefined) s.email = email
    if (phone !== undefined) s.phone = phone
    if (paymentTerms !== undefined) s.paymentTerms = paymentTerms
    const updated = await this.api.update(id, s)
    const idx = this._cache.findIndex(x => String(x.id) === String(id))
    if (idx >= 0) this._cache[idx] = updated
    return updated
  }

  async remove(id) {
    await this.api.delete(id)
    this._cache = this._cache.filter(s => String(s.id) !== String(id))
  }
}
