// 版型颜色映射
export const TYPE_COLOR_MAP = {
  "换": "#409eff",
  "一": "#67c23a",
  "T": "#e6a23c",
  "反": "#f56c6c",
  "地": "#580765FF",
  default: "#e37b10"
};

// 弹窗样式
export const POPUP_STYLES = {
  stockDetail: `
    position: fixed;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 15px;
    z-index: 10000;
    display: none;
    max-width: 40vw;
    max-height: 50vh;
    border: 1px solid #eee;
    box-sizing: border-box;
    overflow: auto;
  `,
  sectorTooltip: `
    position: fixed;
    background: rgba(0, 0, 0, 0.85);
    color: #fff;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    line-height: 1.4;
    max-width: 300px;
    z-index: 9999;
    display: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    pointer-events: none;
  `,
  downloadButton: `
    position: fixed; top: 20px; right: 20px; padding: 10px 20px;
    background: #409eff; color: #fff; border: none; border-radius: 4px;
    cursor: pointer; font-size: 14px; z-index: 999;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  `
};

// 表格样式
export const TABLE_STYLES = {
  header: `padding:6px 8px;text-align:center;border:1px solid #eee;background:#f5f5f5;white-space:nowrap;font-size:12px;`,
  cell: `padding:6px 8px;text-align:center;border:1px solid #eee;white-space:nowrap;font-size:12px;`,
  cellRight: `padding:6px 8px;text-align:right;border:1px solid #eee;white-space:nowrap;font-size:12px;`,
  boardCell: `
    width: 20px;
    min-width: 20px;
    max-width: 20px;
    padding: 4px 0;
    letter-spacing: 2px;
    line-height: 20px;
    border-right: 1px solid #eee;
  `,
  stockCell: `
    padding: 4px;
    vertical-align: top;
    position: relative;
    min-height: 150px;
    box-sizing: border-box;
  `,
  typeIcon: `
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background-color: rgba(64, 158, 255, 0.1);
    margin-right: 4px;
    font-size: 10px;
    font-weight: 600;
    vertical-align: middle;
  `
};

// 加载提示模板
export const LOADING_TEMPLATE = '<tr><td colspan="4" style="text-align:center;padding:50px;color:#666;">加载中...</td></tr>';