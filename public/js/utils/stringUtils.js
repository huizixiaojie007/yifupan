/**
 * 去除字符串前后空格
 * @param {string} str - 输入字符串
 * @returns {string} 处理后的字符串
 */
export function trimStr(str) {
  return str ? str.trim() : '';
}

/**
 * 安全获取字符串（避免null/undefined）
 * @param {string} str - 输入字符串
 * @param {string} defaultValue - 默认值
 * @returns {string} 处理后的字符串
 */
export function safeStr(str, defaultValue = '') {
  return str ? String(str) : defaultValue;
}