import AppState from '../state/appState.js';
import { loadDataByIndex, updateDateSelector } from '../main.js'; // 循环依赖，后续通过入口文件整合
import { showKlineButton } from '../components/ShowKlineButton.js';


/**
 * 初始化日期导航按钮事件
 */
export function initDateNavigation() {
  const prevBtn = document.getElementById('prev-date');
  const nextBtn = document.getElementById('next-date');

  // 初始禁用按钮
  updateNavButtonState();

  // 前一天按钮：索引+1（右栏往前切换）
  prevBtn.addEventListener('click', async () => {
//    AppState.toggleKlineShow();//重置K线显示状态
    forceHideKline();
    const validDates = AppState.getValidDates();
    const currentIndex = AppState.getCurrentIndex();

    if (AppState.getIsFinding() || currentIndex >= validDates.length - 2) return;

    AppState.setIsFinding(true);
    AppState.setIsDateChanging(true); // 设置日期切换标志
    AppState.setCurrentIndex(currentIndex + 1);
    await loadDataByIndex();
    AppState.setIsDateChanging(false); // 清除日期切换标志
    AppState.setIsFinding(false);
  });

  // 后一天按钮：索引-1（右栏往后切换）
  nextBtn.addEventListener('click', async () => {
//      AppState.toggleKlineShow();//重置K线显示状态
    forceHideKline();

    const currentIndex = AppState.getCurrentIndex();

    if (AppState.getIsFinding() || currentIndex <= 0) return;

    AppState.setIsFinding(true);
    AppState.setIsDateChanging(true); // 设置日期切换标志
    AppState.setCurrentIndex(currentIndex - 1);
    await loadDataByIndex();
    AppState.setIsDateChanging(false); // 清除日期切换标志
    AppState.setIsFinding(false);
  });
}

/**
 * 强制隐藏K线（同步状态+按钮样式+DOM+图表实例）
 */
function forceHideKline() {
  const isKlineShow = AppState.getIsKlineShow();
  console.log('forceHideKline - 当前K线显示状态：', isKlineShow);  // 1. 检查当前K线是否处于显示状态，仅在显示时执行隐藏逻辑
  if (isKlineShow|| true) {
    // 2. 重置AppState的K线显示状态（强制设为false，而非切换）
    AppState.setIsKlineShow(false); // 关键：需要确保AppState有setIsKlineShow方法
    // 3. 同步显示K线按钮的样式和文本（置为未显示状态）
    const klineBtn = showKlineButton.button;
    if (klineBtn) {
      klineBtn.textContent = '显示K线'; // 按钮文本恢复为“显示K线”
      klineBtn.style.background = '#409eff'; // 背景色恢复为初始色
    }

    // 4. 隐藏所有股票单元格的K线区域
    const allStockCells = document.querySelectorAll('.stock-cell');
    allStockCells.forEach(cell => {
      const klineArea = cell.querySelector('.kline-area');
      if (klineArea) klineArea.style.display = 'none';
    });

    // 5. 销毁所有K线图表实例（释放内存，避免残留）
    AppState.destroyAllKlineCharts();

    console.log('日期切换，强制隐藏K线');
  }
}
/**
 * 更新导航按钮状态（根据当前索引禁用/启用）
 */
export function updateNavButtonState() {
  const validDates = AppState.getValidDates();
  const currentIndex = AppState.getCurrentIndex();
  const prevBtn = document.getElementById('prev-date');
  const nextBtn = document.getElementById('next-date');

  prevBtn.disabled = currentIndex >= validDates.length - 2;
  nextBtn.disabled = currentIndex <= 0;
}