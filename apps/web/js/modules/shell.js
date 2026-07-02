(function() {
  app.renderNav = function() {
    const nav = document.getElementById('nav')
    if (!nav) return
    var items = this.nav
    const isAr = document.documentElement.lang === 'ar' || document.documentElement.dir === 'rtl'
    try { items = Permission.filterNav(this.nav) } catch (e) { console.error('nav filter', e) }
    nav.innerHTML = items.map(function(item) {
      const displayLabel = (isAr && item.label_ar) ? item.label_ar : item.label;
      if (item.section) return '<div class="px-md mt-md mb-xs font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">' + item.section + '</div>'
      return '<a data-id="' + item.id + '" href="#" onclick="app.loadModule(\'' + item.module + '\'); return false;" class="nav-item flex items-center gap-md text-on-surface-variant px-md py-sm mx-sm rounded-xl transition-all hover:bg-surface-container-high">'
        + '<span class="material-symbols-outlined">' + item.icon + '</span>'
        + '<span class="font-body-md text-body-md">' + displayLabel + '</span></a>'
    }).join('')
  }

  app.loadNavData = async function() {
    try {
      const res = await fetch('NavigationData.json')
      if (res.ok) {
        const navData = await res.json()
        if (navData.nav && navData.nav.length) this.nav = navData.nav
      }
    } catch (e) { console.warn('Nav data fetch failed, using hardcoded nav', e) }
  }

  app.isSidebarCollapsed = false

  app.updateSidebarLayout = function() {
    const sidebar = document.getElementById('navigation-drawer')
    const mainContent = document.querySelector('main')
    const isRtl = document.documentElement.dir === 'rtl'
    if (!sidebar || !mainContent) return

    if (window.innerWidth >= 1024) {
      if (isRtl) {
        mainContent.style.marginRight = app.isSidebarCollapsed ? '0px' : '240px'
        mainContent.style.marginLeft = '0px'
      } else {
        mainContent.style.marginLeft = app.isSidebarCollapsed ? '0px' : '240px'
        mainContent.style.marginRight = '0px'
      }
      sidebar.style.transform = app.isSidebarCollapsed ? (isRtl ? 'translateX(240px)' : 'translateX(-240px)') : 'translateX(0)'
    } else {
      sidebar.style.transform = app.isSidebarMobileOpen ? 'translateX(0)' : (isRtl ? 'translateX(240px)' : 'translateX(-240px)')
    }
  }

  app.isSidebarMobileOpen = false

  app.toggleSidebar = function() {
    if (window.innerWidth >= 1024) {
      app.isSidebarCollapsed = !app.isSidebarCollapsed
    } else {
      app.isSidebarMobileOpen = !app.isSidebarMobileOpen
    }
    app.updateSidebarLayout()
  }

  app.toggleLang = function() {
    const h = document.documentElement
    const searchInput = document.getElementById('globalSearch')
    const logoutBtn = document.getElementById('lblLogoutBtn')
    const userRole = document.getElementById('userRole')
    
    if (h.lang === 'en') { 
        h.lang = 'ar'; h.dir = 'rtl' 
        if (searchInput) searchInput.placeholder = 'البحث في التطبيقات...'
        if (logoutBtn) logoutBtn.textContent = 'تسجيل الخروج'
        if (userRole && CurrentUser && CurrentUser.role === 'Admin') userRole.textContent = 'مدير'
    } else { 
        h.lang = 'en'; h.dir = 'ltr' 
        if (searchInput) searchInput.placeholder = 'Search modules...'
        if (logoutBtn) logoutBtn.textContent = 'Logout'
        if (userRole && CurrentUser) userRole.textContent = CurrentUser.role
    }
    app.updateSidebarLayout()
    app.renderNav()
    if (app.currentModule) {
      app.loadModule(app.currentModule)
    }
  }

  app.search = function(query) {
    const q = query.toLowerCase()
    document.querySelectorAll('#nav a').forEach(function(a) {
      a.style.display = a.textContent.toLowerCase().indexOf(q) > -1 ? '' : 'none'
    })
  }
})()
