window.NovaModules = window.NovaModules || {}; window.NovaModules['home'] = {
  render() {
    return renderHtml('screens/home', {})
  },
  mount() {
    document.getElementById('homeUserName').textContent = CurrentUser ? CurrentUser.username : 'Admin'
    // Calculate basic stats for the dashboard preview
    var lowStockCount = window.inventoryService ? window.inventoryService.getLowStockCount() : 0
    document.getElementById('homePendingAlerts').textContent = lowStockCount + ' Critical'
    
    var products = window.productService ? window.productService.getAll() : []
    document.getElementById('homeActiveStock').textContent = products.length + ' Items'

    // Render app grid
    const gridEl = document.getElementById('homeAppGrid');
    const isAr = document.documentElement.lang === 'ar' || document.documentElement.dir === 'rtl';

    // Translations for Home screen
    if (isAr) {
        document.getElementById('lblHomeWelcome').textContent = 'مرحباً، ';
        document.getElementById('lblHomeSubtitle').textContent = 'حدد تطبيقًا لبدء سير عملك.';
        document.getElementById('lblHomeCustomize').textContent = 'تخصيص الشبكة';
        document.getElementById('lblHomeCompanyPerf').textContent = 'أداء الشركة';
        document.getElementById('lblHomeRealtime').textContent = 'تحديث في الوقت الفعلي';
        document.getElementById('lblHomeInsights').textContent = 'رؤى سريعة';
        document.getElementById('lblHomeSalesTarget').textContent = 'هدف المبيعات';
        document.getElementById('lblHomeReached').textContent = 'تم الوصول 82%';
        document.getElementById('lblHomeActiveStock').textContent = 'المخزون النشط';
        document.getElementById('homeActiveStock').textContent = products.length + ' عنصر';
        document.getElementById('lblHomePendingAlerts').textContent = 'تنبيهات معلقة';
        document.getElementById('homePendingAlerts').textContent = lowStockCount + ' حرج';
        document.getElementById('lblHomeViewReports').textContent = 'عرض تقارير مفصلة';
    } else {
        document.getElementById('homeActiveStock').textContent = products.length + ' Items';
        document.getElementById('homePendingAlerts').textContent = lowStockCount + ' Critical';
    }

    if (gridEl && app.nav) {
      const colorMap = {
        'inventory': '#5C6BC0', 'sales': '#EF5350', 'customers': '#66BB6A',
        'finance': '#26A69A', 'manufacturing': '#AB47BC', 'planning': '#42A5F5',
        'quality': '#26C6DA', 'warehouse': '#78909C', 'pos': '#EC407A',
        'dashboard': '#8D6E63', 'settings': '#607D8B'
      };
      
      let html = '';
      
      let items = app.nav;
      try { items = Permission.filterNav(app.nav); } catch(e) {}
      
      items.forEach(item => {
        if (!item.module || item.module === 'home' || item.module === 'admin' || !colorMap[item.module]) return;
        const color = colorMap[item.module] || '#5C6BC0';
        const displayLabel = (isAr && item.label_ar) ? item.label_ar : item.label;
        
        html += `
<div class="app-card group flex flex-col items-center p-lg bg-surface border border-outline-variant rounded-xl cursor-pointer hover:shadow-lg transition-all" onclick="app.loadModule('${item.module}')">
<div class="app-icon w-16 h-16 rounded-2xl flex items-center justify-center text-white mb-md transition-transform group-hover:-translate-y-1" style="background-color: ${color}">
<span class="material-symbols-outlined text-[32px]" style="font-variation-settings: 'FILL' 1;">${item.icon}</span>
</div>
<span class="font-title-md text-on-surface group-hover:text-primary transition-colors text-center">${displayLabel}</span>
</div>`;
      });
      gridEl.innerHTML = html;
    }
  }
}
