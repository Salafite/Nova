window.SupplierService = class SupplierService {
  constructor(supplierRepo) {
    this.repo = supplierRepo
  }

  getAll() { return this.repo.getAll() }

  getById(id) {
    return this.repo.getAll().find(function(s) { return String(s.id) === String(id) })
  }

  async add(name, email, phone, paymentTerms) {
    return await this.repo.add(name, email, phone, paymentTerms)
  }

  async update(id, name, email, phone, paymentTerms) {
    return await this.repo.update(id, name, email, phone, paymentTerms)
  }

  async remove(id) {
    await this.repo.remove(id)
  }
}
