const TOGGLE_KEYS = new Set(['AUTO_INVOICING', 'BATCH_TRACKING', 'REQUIRE_MFA', 'DARK_MODE', 'PUSH_NOTIFICATIONS'])
const OPTION_CONFIG = {
  NAV_STYLE: { options: ['grid', 'sidebar'] },
  DENSITY_LEVEL: { options: ['compact', 'standard', 'spacious'] },
  SYSTEM_LANGUAGE: { options: ['en-US', 'ar-EG'] },
  THEME: { options: ['light', 'dark'] },
  ACCENT_COLOR: { options: ['blue', 'purple', 'green', 'amber', 'red'] },
  FONT_FAMILY: { options: ['inter', 'roboto', 'open-sans', 'system'] },
  SIDEBAR_MODE: { options: ['expanded', 'overlay'] },
}
const GROUP_ICONS = {
  General: 'tune',
  Company: 'business',
  Regional: 'language',
  Purchasing: 'shopping_cart',
  Sales: 'point_of_sale',
  Finance: 'account_balance',
  Inventory: 'inventory',
  System: 'settings',
  'Company Profile': 'business',
  'Operational Controls': 'settings_applications',
  Security: 'security',
  'App Preferences': 'display_settings',
  Layout: 'grid_view',
}

export function useSettingsUI() {
  function isToggle(setting) {
    return TOGGLE_KEYS.has(setting.setting_key)
  }

  function isOption(setting) {
    return setting.setting_key in OPTION_CONFIG
  }

  function getOptions(setting) {
    return OPTION_CONFIG[setting.setting_key]?.options || []
  }

  function groupIcon(groupName) {
    return GROUP_ICONS[groupName] || 'settings'
  }

  return { isToggle, isOption, getOptions, groupIcon }
}
