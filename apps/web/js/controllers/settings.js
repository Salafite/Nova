window.NovaModules = window.NovaModules || {}; window.NovaModules['settings'] = {
  render() {
    return renderHtml('screens/settings', {})
  },
  settingsData: {}, // To store full setting objects mapping key -> object
  async loadSettings() {
    try {
      const response = await fetch('/api/T0025I?limit=100');
      const data = await response.json();
      const settings = data.data || [];
      
      this.settingsData = {};
      settings.forEach(s => {
        this.settingsData[s.setting_key] = s;
        const el = document.getElementById(s.setting_key);
        if (el) {
          if (el.type === 'checkbox') {
            el.checked = (s.setting_value === 'true');
          } else {
            el.value = s.setting_value || '';
          }
        }
      });
      
      // Update UI for styles and density
      const navStyleSetting = this.settingsData['NAV_STYLE'];
      if (navStyleSetting && navStyleSetting.setting_value) {
        const btn = document.querySelector(`.nav-style-btn[onclick*="${navStyleSetting.setting_value}"]`);
        if (btn) this.setNavStyle(navStyleSetting.setting_value, btn, true);
      }
      
      const densitySetting = this.settingsData['DENSITY_LEVEL'];
      if (densitySetting && densitySetting.setting_value) {
        const btn = document.querySelector(`.density-btn[onclick*="${densitySetting.setting_value}"]`);
        if (btn) this.setDensity(densitySetting.setting_value, btn, true);
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  },
  async saveChanges() {
    const keysToSave = ['COMPANY_NAME', 'COMPANY_REG_NUM', 'AUTO_INVOICING', 'BATCH_TRACKING', 'REQUIRE_MFA', 'DARK_MODE', 'PUSH_NOTIFICATIONS'];
    try {
      for (let key of keysToSave) {
        const el = document.getElementById(key);
        if (!el || !this.settingsData[key]) continue;
        
        let newValue = el.type === 'checkbox' ? (el.checked ? 'true' : 'false') : el.value;
        const settingObj = this.settingsData[key];
        
        if (settingObj.setting_value !== newValue) {
          await fetch(`/api/T0025I/${settingObj.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ setting_value: newValue })
          });
          settingObj.setting_value = newValue;
        }
      }
      alert('Settings saved successfully!');
    } catch (e) {
      console.error('Failed to save settings:', e);
      alert('Failed to save settings.');
    }
  },
  handleDarkModeToggle(el) {
    // We only change the visual here, saving happens on "Save All Changes"
  },
  scrollTo(id, navElement) {
    if (navElement) {
      document.querySelectorAll('#settingsNav a').forEach(item => {
        item.classList.remove('bg-primary-container', 'text-white', 'shadow-lg', 'shadow-primary/10');
        item.classList.add('hover:bg-surface-container-high');
        
        let firstSpan = item.querySelector('span:first-child');
        let secondSpan = item.querySelector('span:nth-child(2)');
        
        if (firstSpan) {
            firstSpan.classList.add('text-on-surface-variant');
            firstSpan.classList.remove('text-white');
        }
        if (secondSpan) {
            secondSpan.classList.add('text-on-surface-variant');
            secondSpan.classList.remove('text-white', 'font-semibold');
        }
      });
      
      navElement.classList.add('bg-primary-container', 'text-white', 'shadow-lg', 'shadow-primary/10');
      navElement.classList.remove('hover:bg-surface-container-high');
      
      let firstSpan = navElement.querySelector('span:first-child');
      let secondSpan = navElement.querySelector('span:nth-child(2)');
      
      if (firstSpan) {
          firstSpan.classList.remove('text-on-surface-variant');
          firstSpan.classList.add('text-white');
      }
      if (secondSpan) {
          secondSpan.classList.remove('text-on-surface-variant');
          secondSpan.classList.add('text-white', 'font-semibold');
      }
    }
    
    var el = document.getElementById(id);
    if (el) {
      var contentArea = document.getElementById('settingsContent');
      if (contentArea) {
        contentArea.scrollTo({
          top: el.offsetTop - contentArea.offsetTop,
          behavior: 'smooth'
        });
      } else {
        el.scrollIntoView({ behavior: 'smooth' });
      }
    }
  },
  mount() {
    this.loadSettings();
    // Add scroll listener for active section highlighting
    var contentArea = document.getElementById('settingsContent');
    if (contentArea) {
      contentArea.addEventListener('scroll', () => {
          let current = "";
          const sections = document.querySelectorAll('#settingsContent section');
          
          sections.forEach(section => {
              const sectionTop = section.offsetTop - contentArea.offsetTop;
              if (contentArea.scrollTop >= sectionTop - 120) {
                  current = section.getAttribute('id');
              }
          });

          if (current) {
              const navItems = document.querySelectorAll('#settingsNav a[href^="#"]');
              navItems.forEach(item => {
                  if (item.getAttribute('href') === '#' + current) {
                      // Apply active styling manually
                      item.classList.add('bg-primary-container', 'text-white', 'shadow-lg', 'shadow-primary/10');
                      item.classList.remove('hover:bg-surface-container-high');
                      let fs = item.querySelector('span:first-child');
                      if (fs) { fs.classList.remove('text-on-surface-variant'); fs.classList.add('text-white'); }
                      let ss = item.querySelector('span:nth-child(2)');
                      if (ss) { ss.classList.remove('text-on-surface-variant'); ss.classList.add('text-white', 'font-semibold'); }
                  } else {
                      // Remove active styling manually
                      item.classList.remove('bg-primary-container', 'text-white', 'shadow-lg', 'shadow-primary/10');
                      item.classList.add('hover:bg-surface-container-high');
                      let fs = item.querySelector('span:first-child');
                      if (fs) { fs.classList.add('text-on-surface-variant'); fs.classList.remove('text-white'); }
                      let ss = item.querySelector('span:nth-child(2)');
                      if (ss) { ss.classList.add('text-on-surface-variant'); ss.classList.remove('text-white', 'font-semibold'); }
                  }
              });
          }
      });
    }
  },
  setNavStyle(style, btn, skipSave = false) {
    document.querySelectorAll('.nav-style-btn').forEach(el => {
      el.classList.remove('border-primary', 'bg-primary/5');
      el.classList.add('border-outline-variant');
      let icon = el.querySelector('.material-symbols-outlined');
      let text = el.querySelector('.font-label-md');
      if (icon) { icon.classList.remove('text-primary'); icon.classList.add('text-on-surface-variant'); }
      if (text) { text.classList.remove('text-primary', 'font-semibold'); text.classList.add('text-on-surface-variant'); }
    });
    btn.classList.remove('border-outline-variant');
    btn.classList.add('border-primary', 'bg-primary/5');
    let icon = btn.querySelector('.material-symbols-outlined');
    let text = btn.querySelector('.font-label-md');
    if (icon) { icon.classList.remove('text-on-surface-variant'); icon.classList.add('text-primary'); }
    if (text) { text.classList.remove('text-on-surface-variant'); text.classList.add('text-primary', 'font-semibold'); }
    
    if (!skipSave && this.settingsData && this.settingsData['NAV_STYLE']) {
      const settingObj = this.settingsData['NAV_STYLE'];
      fetch(`/api/T0025I/${settingObj.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setting_value: style })
      }).then(() => settingObj.setting_value = style);
    }
  },
  setDensity(density, btn, skipSave = false) {
    document.querySelectorAll('.density-btn').forEach(el => {
      el.classList.remove('border-primary', 'bg-primary/5', 'text-primary');
      el.classList.add('border-outline-variant', 'text-on-surface-variant');
      let text = el.querySelector('.font-label-md');
      if (text) { text.classList.remove('font-semibold'); }
    });
    btn.classList.remove('border-outline-variant', 'text-on-surface-variant');
    btn.classList.add('border-primary', 'bg-primary/5', 'text-primary');
    let text = btn.querySelector('.font-label-md');
    if (text) { text.classList.add('font-semibold'); }
    if (!skipSave && this.settingsData && this.settingsData['DENSITY_LEVEL']) {
      const settingObj = this.settingsData['DENSITY_LEVEL'];
      fetch(`/api/T0025I/${settingObj.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setting_value: density })
      }).then(() => settingObj.setting_value = density);
    }
  }
}
