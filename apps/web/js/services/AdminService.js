window.AdminService = class AdminService {
  constructor() {
    this.api = new ApiClient('T0021I')
    this._users = []
  }

  async load() {
    try {
      this._users = await this.api.list() || []
    } catch (e) {
      console.warn('Failed to load users from API', e)
      this._users = []
    }
  }

  getUsers() { return this._users }

  async create(username, password, role) {
    var user = await this.api.create({
      username: username,
      passwordHash: password,
      fullName: username,
      email: username + '@novaerp.local',
      role: role,
      status: 'Active'
    })
    this._users.push(user)
    return user
  }

  async remove(id) {
    await this.api.delete(id)
    this._users = this._users.filter(function(u) { return u.id !== id })
  }
}
