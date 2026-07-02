window.NovaModules = window.NovaModules || {}; window.NovaModules['warehouse'] = {
  render() {
    var zonesDetails = window.warehouseService ? window.warehouseService.getZoneDetails() : []
    var inventory = window.inventoryService.getAll()
    var products = window.productService ? window.productService.getAll() : []
    
    const zoneConfigs = [
      { color: 'primary', icon: 'download', name: 'Receiving', desc: 'Inbound logistics processing', m1: 'Incoming', m2: 'Processed', v1: '14', v2: '42' },
      { color: 'secondary', icon: 'inventory_2', name: 'Main Storage', desc: 'Standard ambient goods', m1: 'Active SKUs', m2: 'Turnover', v1: '2,481', v2: '4.2x' },
      { color: 'error', icon: 'ac_unit', name: 'Cold Storage', desc: 'Perishables & Temp Control', m1: 'Temperature', m2: 'Alerts', v1: '-18°C', v2: '<span class="text-error">0</span>' }
    ];

    var zoneRows = zonesDetails.map(function(z, idx) {
      var pct = z.utilization || Math.floor(Math.random() * 50 + 40)
      var conf = zoneConfigs[idx % zoneConfigs.length]
      
      return `
<div class="col-span-12 lg:col-span-4 bg-surface-container-lowest p-lg border border-outline-variant rounded-xl group hover:border-${conf.color} transition-all">
<div class="flex justify-between items-start mb-lg">
<div class="p-3 rounded-lg bg-${conf.color === 'secondary' ? conf.color : conf.color + '-container'}/10 text-${conf.color}">
<span class="material-symbols-outlined">${conf.icon}</span>
</div>
<span class="font-data-mono text-data-mono text-on-surface-variant">Zone ${z.code || (idx+1)}</span>
</div>
<h4 class="font-title-md text-title-md mb-xs">${escapeHtml(z.name || conf.name)}</h4>
<p class="text-on-surface-variant text-body-md mb-lg">${conf.desc}</p>
<div class="space-y-md">
<div class="flex justify-between text-label-md font-label-md">
<span class="text-on-surface-variant">Capacity</span>
<span class="text-on-background">${pct}%</span>
</div>
<div class="w-full h-2 bg-surface-container-high rounded-full overflow-hidden">
<div class="h-full bg-${conf.color} transition-all duration-1000" style="width: ${pct}%"></div>
</div>
<div class="flex justify-between pt-sm">
<div class="text-center">
<p class="text-on-surface-variant text-[10px] uppercase font-bold">${conf.m1}</p>
<p class="font-data-mono text-title-md">${conf.v1}</p>
</div>
<div class="text-center">
<p class="text-on-surface-variant text-[10px] uppercase font-bold">${conf.m2}</p>
<p class="font-data-mono text-title-md">${conf.v2}</p>
</div>
</div>
</div>
</div>`
    }).join('')

    var stockRows = inventory.slice(0, 10).map(function(i) {
      var prod = products.find(p => p.id === i.productId) || {}
      var sku = prod.sku || ('WRH-' + (1000 + i.productId) + '-X')
      var qty = i.quantity || 0
      
      var isLow = qty < 20
      var statusColor = isLow ? 'amber' : 'green'
      var statusText = isLow ? 'Low Stock' : 'In Stock'
      var lastUpdate = (qty % 15 + 2) + ' mins ago'
      
      return `
<tr class="hover:bg-primary/5 transition-colors border-b border-outline-variant group">
<td class="p-md font-data-mono text-data-mono text-primary">${escapeHtml(sku)}</td>
<td class="p-md font-body-md text-body-md">${escapeHtml(i.productName)}</td>
<td class="p-md">
<span class="px-2 py-1 bg-surface-variant/50 text-[11px] font-bold rounded">${escapeHtml(i.location || 'Main')}</span>
</td>
<td class="p-md">
<span class="inline-flex items-center gap-1 text-${statusColor}-600 bg-${statusColor}-50 px-2 py-1 rounded-full text-[11px] font-bold">
<span class="w-1.5 h-1.5 bg-${statusColor}-600 rounded-full"></span>
    ${statusText}
</span>
</td>
<td class="p-md font-data-mono text-right">${qty}</td>
<td class="p-md text-on-surface-variant text-sm">${lastUpdate}</td>
</tr>`
    }).join('')

    return renderHtml('screens/warehouse', { zoneRows: zoneRows, stockRows: stockRows })
  }
}
