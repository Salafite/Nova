(function() {
  app.toast = function(msg, type) {
    if (type === undefined) type = 'info'
    let container = document.getElementById('toastContainer')
    if (!container) {
      container = document.createElement('div')
      container.id = 'toastContainer'
      container.className = 'fixed bottom-lg right-lg z-50 flex flex-col gap-sm pointer-events-none'
      document.body.appendChild(container)
    }
    const toast = document.createElement('div')
    const bgClass = type === 'error' ? 'bg-error text-on-error' : (type === 'success' ? 'bg-secondary text-on-secondary' : 'bg-surface-container-highest text-on-surface')
    const icon = type === 'error' ? 'error' : (type === 'success' ? 'check_circle' : 'info')
    toast.className = 'flex items-center gap-md px-md py-sm rounded-lg shadow-md transition-all duration-300 transform translate-y-4 opacity-0 ' + bgClass
    toast.innerHTML = '<span class="material-symbols-outlined">' + icon + '</span><span class="font-label-md text-label-md">' + msg + '</span>'
    container.appendChild(toast)
    requestAnimationFrame(function() { toast.classList.remove('translate-y-4', 'opacity-0') })
    setTimeout(function() {
      toast.classList.add('opacity-0')
      setTimeout(function() { toast.remove() }, 300)
    }, 3000)
  }
})()
