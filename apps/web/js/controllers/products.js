window.NovaModules = window.NovaModules || {}; window.NovaModules['products'] = new DynamicScreen({
  module: 'products',
  title: 'Products',
  entityName: 'Product',
  table: 'T0003I',
  searchFields: ['name', 'sku'],

  columns: [
    { key: 'sku', label: 'SKU' },
    { key: 'name', label: 'Name' },
    { key: 'price', label: 'Price', align: 'right', render: function(v) { return '$' + (v || 0).toFixed(2) } },
    { key: 'stock', label: 'Stock', align: 'right' },
    { key: 'category', label: 'Category' },
    { key: 'stock', label: 'Status', render: function(v, r) { return Badge.stock(v, r.minStock) } }
  ],

  stats: [
    { label: 'Total Products', value: function(d) { return d.length } },
    { label: 'Low Stock', value: function(d) { return d.filter(function(p) { return (p.stock||0) > 0 && (p.stock||0) < (p.minStock||5) }).length } },
    { label: 'Out of Stock', value: function(d) { return d.filter(function(p) { return !(p.stock||0) }).length } },
    { label: 'Inventory Value', value: function(d) { return '$' + d.reduce(function(s, p) { return s + (p.price||0) * (p.stock||0) }, 0).toLocaleString() } }
  ],

  fields: [
    { key: 'name', label: 'Name', required: true },
    { key: 'sku', label: 'SKU' },
    { key: 'price', label: 'Price', type: 'number', step: '0.01' },
    { key: 'category', label: 'Category', options: ['General', 'Electronics', 'Clothing', 'Food', 'Office'] },
    { key: 'stock', label: 'Stock', type: 'number' },
    { key: 'minStock', label: 'Min Stock', type: 'number' }
  ]
})
