import { POPUP_STYLES } from '../constants/styleConstants.js';
import AppState from '../state/appState.js';

/**
 * 板块/原因悬浮框组件（单例）
 */
class SectorTooltip {
  constructor() {
    this.tooltip = null;
    this.triggerElements = []; // 记录所有触发元素
    this.init();
    this.bindGlobalEvents(); // 绑定全局事件
  }

  // 初始化悬浮框DOM（补充换行相关样式）
  init() {
    this.tooltip = document.getElementById('sector-tooltip');
    if (!this.tooltip) { // 仅当不存在时创建，避免重复
      this.tooltip = document.createElement('div');
      this.tooltip.id = 'sector-tooltip';
      // 关键：补充换行样式 + 最大宽度（避免文本溢出）
      this.tooltip.style.cssText = `${POPUP_STYLES.sectorTooltip}; white-space: pre-line; max-width: 400px;`;
      document.body.appendChild(this.tooltip);
    }
  }

  /**
   * 绑定全局事件（兜底隐藏）
   */
  bindGlobalEvents() {
    // 鼠标移动时检查是否远离触发元素
    document.addEventListener('mousemove', (e) => {
      if (!this.tooltip || this.tooltip.style.display === 'none') return;

      // 检查鼠标是否在任何触发元素或悬浮框上
      const isOverTrigger = this.triggerElements.some(el => el.contains(e.target));
      const isOverTooltip = this.tooltip.contains(e.target);

      if (!isOverTrigger && !isOverTooltip) {
        this.hideTooltip();
      }
    });

    // 页面点击时隐藏
    document.addEventListener('click', () => {
      this.hideTooltip();
    });
  }

  /**
   * 记录触发元素（用于全局检查）
   * @param {HTMLElement} el - 触发元素
   */
  addTriggerElement(el) {
    if (!this.triggerElements.includes(el)) {
      this.triggerElements.push(el);
    }
  }

  /**
   * 移除触发元素（避免内存泄漏）
   * @param {HTMLElement} el - 触发元素
   */
  removeTriggerElement(el) {
    this.triggerElements = this.triggerElements.filter(item => item !== el);
  }

  // 重写showTooltip方法：用innerHTML支持换行标签
  _showTooltip(content, x, y, triggerEl) {
    if (!this.tooltip) return;

    // 关键修改：用innerHTML替代textContent，解析<br>换行
    this.tooltip.innerHTML = content;
    this.tooltip.style.display = 'block';

    // 记录触发元素
    if (triggerEl) {
      this.addTriggerElement(triggerEl);
    }

    // 原有定位逻辑不变
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const tooltipWidth = this.tooltip.offsetWidth;
    const tooltipHeight = this.tooltip.offsetHeight;

    let left = x + 10;
    if (left + tooltipWidth > windowWidth) left = x - tooltipWidth - 10;

    let top = y + 10;
    if (top + tooltipHeight > windowHeight) top = y - tooltipHeight - 10;

    this.tooltip.style.left = `${left}px`;
    this.tooltip.style.top = `${top}px`;
  }

  // 重写公开方法，传递触发元素
  showSectorTooltip(sector, x, y, triggerEl) {
    const sectorReasonMap = AppState.getSectorReasonMap();
    const sectorReason = sectorReasonMap[sector] || '暂无接口返回的板块原因';
    this._showTooltip(sectorReason, x, y, triggerEl);
  }

  // 核心修复：用<br>拼接，支持HTML换行
  showReasonDetailTooltip(detail, x, y, triggerEl) {
    const text = detail
      .split(/[Iｉ。．]/) // 按"I"或"。"分割
      .filter(s => s.trim()) // 过滤空值
      .map(s => s.trim()) // 清理前后空格
      .join('<br>'); // 用HTML换行标签拼接（关键）

    const reason = text || '暂无原因详情';
    this._showTooltip(reason, x, y, triggerEl);
  }

  // 重写hideTooltip，清空触发元素
  hideTooltip() {
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
    this.triggerElements = []; // 清空触发元素
  }
}

// 单例导出
export const sectorTooltip = new SectorTooltip();