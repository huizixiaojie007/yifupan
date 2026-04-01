/**
 * 格式化日期为 YYYY-MM-DD
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的日期字符串
 */
export function formatDateToYmd(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * 格式化日期为 月.日
 * @param {Date} date - 日期对象
 * @returns {string} 格式化后的日期字符串
 */
export function formatDateToMd(date) {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${month}.${day}`;
}

/**
 * 增减日期（days为正数加，负数减）
 * @param {Date} date - 原始日期
 * @param {number} days - 增减天数
 * @returns {Date} 新日期对象
 */
export function addDays(date, days) {
  const newDate = new Date(date);
  newDate.setDate(newDate.getDate() + days);
  return newDate;
}

/**
 * 比较两个日期是否相同（忽略时间）
 * @param {Date} date1 - 日期1
 * @param {Date} date2 - 日期2
 * @returns {boolean} 是否相同
 */
export function isSameDate(date1, date2) {
  return date1.getFullYear() === date2.getFullYear() &&
         date1.getMonth() === date2.getMonth() &&
         date1.getDate() === date2.getDate();
}

/**
 * 格式化时间显示（适配接口返回的time/date类型）
 * @param {string|Date|Object} timeValue - 时间值
 * @returns {string} 格式化后的时间字符串
 */
export function formatTime(timeValue) {
  if (!timeValue) return '';
  // 处理字符串格式时间（如"10:04:33"）
  if (typeof timeValue === 'string') {
    return timeValue.trim();
  }
  // 处理Date对象（完整datetime）
  if (timeValue instanceof Date) {
    return timeValue.toTimeString().slice(0, 8);
  }
  // 处理Time对象（仅时间，如datetime.time）
  if (timeValue instanceof Object && 'getHours' in timeValue) {
    const hh = String(timeValue.getHours()).padStart(2, '0');
    const mm = String(timeValue.getMinutes()).padStart(2, '0');
    const ss = String(timeValue.getSeconds()).padStart(2, '0');
//    return `${hh}:${mm}:${ss}`;
    return `${hh}:${mm}`;
  }
  // 其他情况直接转换为字符串
  return String(timeValue).trim();
}