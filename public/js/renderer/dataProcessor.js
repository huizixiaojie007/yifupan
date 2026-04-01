import { BUSINESS_CONFIG } from '../constants/configConstants.js';
//import { formatTime } from '../utils/dateUtils.js';

/**
 * 按板块分组股票数据
 * @param {Array} stocks - 股票列表
 * @returns {Object} 按板块分组后的对象
 */
export function groupStocksBySector(stocks) {
  const groups = {};
  stocks.forEach(stock => {
    const sector = stock.sector || '未知板块';
    if (!groups[sector]) groups[sector] = [];
    groups[sector].push(stock);
  });
  return groups;
}

/**
 * 排序板块（其他概念后置，按股票数量降序）
 * @param {Object} groups - 按板块分组的股票数据
 * @returns {Array} 排序后的板块名称列表
 */
export function sortSectors(groups) {
  return Object.keys(groups).sort((a, b) => {
    if (a === '其他概念') return 1;
    if (b === '其他概念') return -1;
    return groups[b].length - groups[a].length;
  });
}

/**
 * 解析时间字符串（容错处理）
 * @param {string} timeStr - 时间字符串
 * @returns {number} 时间戳（毫秒）
 */
export function parseTime(timeStr) {
  if (!timeStr) return Infinity;
  timeStr = timeStr.replace(/^\s+|\s+$/g, '');

  // 处理纯数字格式（如"093000"）
  if (/^\d{4,6}$/.test(timeStr)) {
    const hh = parseInt(timeStr.slice(0, 2), 10);
    const mm = parseInt(timeStr.slice(2, 4), 10);
    const ss = timeStr.length >= 6 ? parseInt(timeStr.slice(4, 6), 10) : 0;
    const d = new Date();
    d.setHours(hh, mm, ss, 0);
    return d.getTime();
  }

  // 处理标准日期字符串
  let date = new Date(timeStr);
  if (!isNaN(date.getTime())) return date.getTime();

  // 拼接当前日期处理
  const now = new Date();
  const dateTimeStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${timeStr}`;
  date = new Date(dateTimeStr);
  return !isNaN(date.getTime()) ? date.getTime() : Infinity;
}

/**
 * 排序股票（按涨停时间升序，名称拼音升序）
 * @param {Array} stocks - 股票列表
 * @returns {Array} 排序后的股票列表
 */
export function sortStocks(stocks) {
  return stocks.slice().sort((s1, s2) => {
    const t1 = parseTime(s1.last_limitup_time);
    const t2 = parseTime(s2.last_limitup_time);
    if (t1 !== t2) return t1 - t2;
    return s1.gp_name.localeCompare(s2.gp_name, 'zh-CN');
  });
}

/**
 * 分组股票（每N个一组）
 * @param {Array} stocks - 排序后的股票列表
 * @returns {Array} 分组后的股票列表
 */
export function groupStocks(stocks) {
  const groups = [];
  for (let i = 0; i < stocks.length; i += BUSINESS_CONFIG.stockGroupSize) {
    groups.push(stocks.slice(i, i + BUSINESS_CONFIG.stockGroupSize));
  }
  return groups;
}

/**
 * 格式化板数名称（1板→首板，数字板数简化）
 * @param {string} boardName - 原始板数名称
 * @returns {string} 格式化后的板数名称
 */
export function formatBoardName(boardName) {
  const boardNum = parseInt(boardName, 10);
  return isNaN(boardNum) ? boardName : (boardNum === 1 ? '首' : boardNum);
}