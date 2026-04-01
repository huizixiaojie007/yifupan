import { BUSINESS_CONFIG } from '../constants/configConstants.js';

/**
 * 根据字符串生成固定的哈希值
 * @param {string} str - 输入字符串
 * @returns {number} 哈希值
 */
export function stringToHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // 转换为32位整数
    hash = Math.abs(hash);
  }
  return hash;
}

/**
 * 根据板块名生成固定颜色
 * @param {string} sector - 板块名称
 * @returns {string} 颜色值（hex）
 */
export function getColorBySector(sector) {
  if (!sector) return '#CCCCCC';
  // 特别处理：其他概念板块使用配置的默认颜色
  if (sector === '其他概念') {
    return BUSINESS_CONFIG.defaultSectorColor;
  }
  const hash = stringToHash(sector);
  const r = (hash & 0xFF0000) >> 16;
  const g = (hash & 0x00FF00) >> 8;
  const b = hash & 0x0000FF;
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/**
 * 根据背景色计算合适的文字颜色（黑或白）
 * @param {string} hexColor - 背景色（hex）
 * @returns {string} 文字颜色（#333333 或 #FFFFFF）
 */
export function getContrastColor(hexColor) {
  hexColor = hexColor || '#CCCCCC';
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128 ? '#333333' : '#FFFFFF';
}

/**
 * 获取板块对应的颜色（优先动态映射，无则生成）
 * @param {string} sector - 板块名称
 * @param {Object} dynamicSectorColorMap - 动态颜色映射
 * @returns {string} 颜色值
 */
export function getSectorColor(sector, dynamicSectorColorMap) {
  if (dynamicSectorColorMap[sector]) {
    return dynamicSectorColorMap[sector];
  }
  // 其他概念默认颜色
  if (sector === '其他概念') {
    return BUSINESS_CONFIG.defaultSectorColor;
  }
  // 生成新颜色并缓存
  const newColor = getColorBySector(sector);
  dynamicSectorColorMap[sector] = newColor;
  return newColor;
}