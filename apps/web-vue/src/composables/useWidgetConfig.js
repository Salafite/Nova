export function parseWidgetConfig(widget) {
  try {
    return typeof widget.config === 'string' ? JSON.parse(widget.config) : (widget.config || {})
  } catch {
    return {}
  }
}

export function widgetChartProps(widget) {
  const cfg = parseWidgetConfig(widget)
  if (widget.widget_type === 'Metric') {
    return { type: 'stat', statLabel: cfg.statLabel || widget.title, statValue: cfg.statValue || 0, statPrefix: cfg.statPrefix || '', statSuffix: cfg.statSuffix || '', statIcon: cfg.statIcon || '', trend: cfg.trend || '', trendDir: cfg.trendDir || 'up', height: 180 }
  }
  if (widget.widget_type === 'KPI') {
    return { type: 'progress', progressLabel: cfg.progressLabel || widget.title, progressValue: cfg.progressValue || 75, progressSubtext: cfg.progressSubtext || '', color: cfg.color || '#5d3fd3', height: 120 }
  }
  if (widget.widget_type === 'Chart') {
    return { type: cfg.chart_subtype || 'bar', labels: cfg.labels || [], values: cfg.values || [], label: cfg.label || '', color: cfg.color || '#5d3fd3', height: 220 }
  }
  return { type: 'stat', statLabel: widget.title || 'Widget', statValue: 0, height: 100 }
}

export function widgetTo(widget) {
  const cfg = parseWidgetConfig(widget)
  return cfg.to || ''
}

export function navigateToWidget(router, widget) {
  const routeName = widgetTo(widget)
  if (routeName) router.push({ name: routeName })
}
