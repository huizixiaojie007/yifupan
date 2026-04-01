import { POPUP_STYLES, TABLE_STYLES } from '../constants/styleConstants.js';
import { BUSINESS_CONFIG } from '../constants/configConstants.js';
import { sectorTooltip } from '../components/SectorTooltip.js';


/**
 * 股票详情弹窗组件（单例）
 */
class StockDetailPopup {
  constructor() {
    this.popup = null;
    this.init();
  }

  // 初始化弹窗DOM
  init() {
    this.popup = document.getElementById('stock-detail-popup');
    if (this.popup) return;

    this.popup = document.createElement('div');
    this.popup.id = 'stock-detail-popup';
    this.popup.style.cssText = POPUP_STYLES.stockDetail;

    document.body.appendChild(this.popup);
    this._bindCloseEvent();
  }

  /**
   * 绑定点击外部关闭事件
   */
  _bindCloseEvent() {
    document.addEventListener('click', (e) => {
      if (this.popup && !this.popup.contains(e.target) && e.target.className !== 'stock-name-text') {
        this.popup.style.display = 'none';
      }
    });
  }

  /**
   * 显示股票详情弹窗
   * @param {Array} data - 股票详情数据
   * @param {number} x - 鼠标X坐标
   * @param {number} y - 鼠标Y坐标
   */
  showPopup(data, x, y) {
    if (!this.popup) this.init();

    // 关键修复：显示弹窗时隐藏悬浮框
    sectorTooltip.hideTooltip();

    // 无数据处理
    if (!data || data.length === 0) {
      this.popup.innerHTML = `<div style="color:#f56c6c;padding:10px;width:100%">${BUSINESS_CONFIG.noDataText}</div>`;
      this.popup.style.display = 'block';
      return;
    }

    // 渲染表格内容
    this.popup.innerHTML = this._renderTable(data);

    // 定位弹窗（避免超出视口）
    this._positionPopup(x, y);

    this.popup.style.display = 'block';
  }

  /**
   * 渲染表格HTML
   * @param {Array} data - 股票详情数据
   * @returns {string} 表格HTML
   */
  _renderTable(data) {
    const stockName = data[0]?.gp_name || '股票';
    const labels = ['日期', '时间', '换手率', '封板额', '封成比', '炸板', '龙虎榜', '板型', '板块', '涨停原因'];

    let html = `<h3 style="margin:0 0 10px;padding-bottom:8px;border-bottom:1px solid #eee;font-size:14px;">${stockName} 详情列表</h3>`;
    html += `<table style="border-collapse:collapse;border:1px solid #eee;min-width:100%;">`;

    // 表头
    html += `<tr>`;
    labels.forEach(label => {
      html += `<th style="${TABLE_STYLES.header}">${label}</th>`;
    });
    html += `</tr>`;

    // 数据行
    data.forEach(item => {
      html += `<tr>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.date?.split('T')[0] || '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.last_limitup_time || '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cellRight}">${item.turnover_rate ? `${item.turnover_rate}%` : '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.limitup_order_amount ? `${(item.limitup_order_amount / 100000000).toFixed(2)}亿` : '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cellRight}">${item.limitup_seal_ratio ? `${parseFloat(item.limitup_seal_ratio).toFixed(2)}%` : '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.limitup_open_times || '0'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.longhu || '0'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.limitup_type?.split('板')[0] || '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.sector || '未知'}</td>`;
      html += `<td style="${TABLE_STYLES.cell}">${item.limitup_reason || '无'}</td>`;
      html += `</tr>`;
    });

    html += `</table>`;
    return html;
  }

  /**
   * 定位弹窗
   * @param {number} x - 鼠标X坐标
   * @param {number} y - 鼠标Y坐标
   */
  _positionPopup(x, y) {
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;
    const popupWidth = this.popup.offsetWidth;
    const popupHeight = this.popup.offsetHeight;

    let left = x - 100;
    if (left + popupWidth > windowWidth) left = x - popupWidth + 100;

    let top = y + 10;
    if (top + popupHeight > windowHeight) top = y - popupHeight - 10;

    this.popup.style.left = `${left}px`;
    this.popup.style.top = `${top}px`;
  }
}

// 单例导出
export const stockDetailPopup = new StockDetailPopup();