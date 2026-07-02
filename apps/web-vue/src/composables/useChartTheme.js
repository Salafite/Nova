import { useTheme } from './useTheme.js'

export function useChartTheme() {
  const { dark } = useTheme()

  function colors(d) {
    return {
      tooltipBg: d ? '#2a2a4a' : '#1a1a2e',
      tickColor: d ? '#888' : '#999',
      gridColor: d ? 'rgba(255,255,255,0.08)' : 'rgba(128,128,128,0.15)',
      legendColor: d ? '#aaa' : '#666',
      pointBorderColor: d ? '#2a2a4a' : '#fff',
      segmentBorder: d ? '#2a2a4a' : '#fff'
    }
  }

  function chartOptions(overrides = {}) {
    const c = colors(dark.value)
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
          position: 'bottom',
          labels: { color: c.legendColor, font: { size: 11 }, padding: 12, usePointStyle: true },
          ...(overrides.legend || {})
        },
        tooltip: {
          backgroundColor: c.tooltipBg,
          titleFont: { size: 12 },
          bodyFont: { size: 12 },
          ...(overrides.tooltip || {})
        }
      },
      scales: overrides.scales || {
        x: { grid: { display: false }, ticks: { color: c.tickColor, font: { size: 11 } } },
        y: { grid: { color: c.gridColor }, ticks: { color: c.tickColor, font: { size: 11 } } }
      },
      ...(overrides.extra || {})
    }
  }

  return { chartOptions, colors, dark }
}
