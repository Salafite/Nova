window.WarehouseService = class WarehouseService {
  constructor(inventoryService) {
    this.inventory = inventoryService
  }

  _computeZones() {
    var items = this.inventory.getAll()
    var map = {}
    items.forEach(function(i) {
      var loc = i.location || 'Main'
      if (!map[loc]) map[loc] = { count: 0, qty: 0 }
      map[loc].count++
      map[loc].qty += i.quantity || 0
    })
    var keys = Object.keys(map)
    if (keys.length === 0) {
      return []
    }
    return keys.map(function(name) {
      var info = map[name]
      var capacity = Math.max(Math.ceil(info.qty * 2 / 100) * 100, 1000)
      var used = info.qty
      return {
        name: name,
        code: name === 'Main' ? 'A-1' : name.substring(0, 3).toUpperCase(),
        capacity: capacity,
        used: used,
        utilization: Math.round(used / capacity * 100),
        description: name + ' storage zone'
      }
    })
  }

  getZones() { return this._computeZones().map(function(z) { return z.name }) }

  getZoneDetails() { return this._computeZones() }

  getZone(name) { return this._computeZones().find(function(z) { return z.name === name }) || null }

  getTotalCapacity() { return this._computeZones().reduce(function(s, z) { return s + z.capacity }, 0) }

  getTotalUsed() { return this._computeZones().reduce(function(s, z) { return s + z.used }, 0) }

  getOverallUtilization() {
    var total = this.getTotalCapacity()
    return total ? Math.round(this.getTotalUsed() / total * 100) : 0
  }
}
