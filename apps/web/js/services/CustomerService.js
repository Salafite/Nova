window.CustomerService = class CustomerService {
  constructor(customerRepo) {
    this.repo = customerRepo
  }

  getAll() { return this.repo.getAll() }

  async add(name, group, phone, creditLimit) {
    return await this.repo.add({ name, group, phone, creditLimit })
  }

  getByName(name) { return this.repo.getByName(name) }

  getOutstandingBalance() {
    return this.repo.getAll().reduce((s, c) => s + c.balance, 0)
  }

  getTotalCreditLimit() {
    return this.repo.getAll().reduce((s, c) => s + c.creditLimit, 0)
  }
}
