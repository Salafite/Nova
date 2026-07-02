(function() {
  app.renderAuth = function(page) {
    document.querySelector('.app-shell').style.display = 'none'
    const overlay = document.getElementById('authOverlay')
    overlay.classList.add('active')
    overlay.innerHTML = this.getAuthHtml(page)
  }

  app.getAuthHtml = function(page) {
    if (page === 'login') {
      return [
        '<main class="flex-grow flex items-center justify-center px-margin-mobile md:px-0 py-xl w-full h-full">',
          '<div class="w-full max-w-[440px]">',
            '<div class="tonal-layer-1 p-xl rounded shadow-none bg-surface-container-lowest border border-outline-variant">',
              '<div class="mb-lg text-center">',
                '<div class="flex justify-center mb-md">',
                  '<span class="material-symbols-outlined text-primary text-[48px]" style="font-variation-settings: \'FILL\' 1;">bolt</span>',
                '</div>',
                '<h1 class="font-headline-lg text-headline-lg text-on-surface mb-xs">Sign In</h1>',
                '<p class="text-on-surface-variant font-body-md text-body-md">Enter your credentials to access your ERP workspace.</p>',
              '</div>',
              '<div id="authAlert" class="p-sm mb-md rounded text-center font-bold" style="display:none"></div>',
              '<form class="space-y-lg" onsubmit="event.preventDefault();">',
                '<div class="space-y-xs">',
                  '<label class="block font-label-md text-label-md text-on-surface-variant uppercase tracking-wider" for="authUsername">Username</label>',
                  '<div class="relative">',
                    '<span class="absolute left-md top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant text-[20px]">person</span>',
                    '<input class="w-full pl-11 pr-md py-sm bg-surface-container-low border border-outline-variant rounded focus:border-2 focus:border-primary focus:ring-0 transition-all outline-none text-body-md" id="authUsername" type="text"/>',
                  '</div>',
                '</div>',
                '<div class="space-y-xs">',
                  '<div class="flex justify-between items-center">',
                    '<label class="block font-label-md text-label-md text-on-surface-variant uppercase tracking-wider" for="authPassword">Password</label>',
                    '<a class="font-label-md text-label-md text-primary hover:underline transition-colors" href="#" onclick="app.showReset();return false">Forgot password?</a>',
                  '</div>',
                  '<div class="relative">',
                    '<span class="absolute left-md top-1/2 -translate-y-1/2 material-symbols-outlined text-on-surface-variant text-[20px]">lock</span>',
                    '<input class="w-full pl-11 pr-11 py-sm bg-surface-container-low border border-outline-variant rounded focus:border-2 focus:border-primary focus:ring-0 transition-all outline-none text-body-md" id="authPassword" type="password"/>',
                  '</div>',
                '</div>',
                '<div class="pt-base">',
                  '<button class="w-full bg-primary text-on-primary font-title-md text-title-md py-sm px-lg rounded flex items-center justify-center gap-sm press-effect hover:bg-primary-container transition-all" onclick="app.handleLogin()">',
                    '<span>Sign In</span>',
                    '<span class="material-symbols-outlined">arrow_forward</span>',
                  '</button>',
                '</div>',
              '</form>',
              '<div class="mt-md text-center text-on-surface-variant font-label-md">Enter your credentials to continue</div>',
            '</div>',
          '</div>',
        '</main>'
      ].join('\n')
    }
    if (page === 'reset') {
      return [
        '<main class="flex-grow flex items-center justify-center px-margin-mobile md:px-0 py-xl w-full h-full">',
          '<div class="w-full max-w-[440px]">',
            '<div class="tonal-layer-1 p-xl rounded shadow-none bg-surface-container-lowest border border-outline-variant">',
              '<div class="mb-lg text-center">',
                '<h1 class="font-headline-lg text-headline-lg text-on-surface mb-xs">Reset Password</h1>',
              '</div>',
              '<div id="resetAlert" class="p-sm mb-md rounded text-center font-bold" style="display:none"></div>',
              '<div class="space-y-lg">',
                '<div class="space-y-xs">',
                  '<input class="w-full px-md py-sm bg-surface-container-low border border-outline-variant rounded focus:border-2 focus:border-primary transition-all outline-none" id="resetUsername" placeholder="Username" type="text"/>',
                '</div>',
                '<button class="w-full bg-primary text-on-primary font-title-md py-sm px-lg rounded press-effect hover:bg-primary-container transition-all" onclick="app.handleReset()">Reset Password</button>',
                '<p class="text-center mt-md"><a href="#" class="text-primary hover:underline" onclick="app.showLogin();return false">Back to sign in</a></p>',
              '</div>',
            '</div>',
          '</div>',
        '</main>'
      ].join('\n')
    }
  }

  app.handleLogin = async function() {
    const username = document.getElementById('authUsername').value.trim()
    const password = document.getElementById('authPassword').value
    const alert = document.getElementById('authAlert')
    if (!username || !password) {
      alert.className = 'bg-error-container text-error p-sm rounded text-center font-bold mb-md'
      alert.textContent = 'Please enter username and password'
      alert.style.display = 'block'
      return
    }
    const ok = await Auth.login(username, password)
    if (ok) {
      this._started = false
      this.init()
    } else {
      alert.className = 'bg-error-container text-error p-sm rounded text-center font-bold mb-md'
      alert.textContent = 'Invalid username or password'
      alert.style.display = 'block'
    }
  }

  app.handleReset = function() {
    throw new Error('Unimplemented: Password reset API not available')
  }

  app.showReset = function() { this.renderAuth('reset') }
  app.showLogin = function() { this.renderAuth('login') }
})()
