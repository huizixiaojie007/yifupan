import AppState from './state/appState.js';
import { getAllValidDates, fetchSingleDateData } from './api/stockApi.js';
import { sectorTooltip } from './components/SectorTooltip.js';
import { downloadButton } from './components/DownloadButton.js';
import { initDateNavigation, updateNavButtonState, setLoadDataByIndexFn, setUpdateDateSelectorFn } from './navigation/dateNavigation.js';
import { renderSingleTable, showLoading, hideLoading } from './renderer/tableRenderer.js';
import { formatDateToMd, formatDateToYmd } from './utils/dateUtils.js';
import { BUSINESS_CONFIG } from './constants/configConstants.js';

/**
 * 根据当前索引加载左右栏数据（核心逻辑，新增 user 参数传递）
 */
export async function loadDataByIndex() {
  const validDates = AppState.getValidDates();
  const currentIndex = AppState.getCurrentIndex();

  // 获取DOM元素
  const leftContainer = document.getElementById('left-table-body');
  const rightContainer = document.getElementById('right-table-body');
  const leftTitle = document.getElementById('left-title');
  const rightTitle = document.getElementById('right-title');
  const leftDateText = document.getElementById('left-date-text');
  const rightDateText = document.getElementById('right-date-text');

  // 无数据处理
  if (validDates.length === 0) {
    hideLoading(leftContainer);
    hideLoading(rightContainer);
    leftTitle.textContent = BUSINESS_CONFIG.noDataText;
    rightTitle.textContent = BUSINESS_CONFIG.noDataText;
    return;
  }

  // ================================= 新增：获取当前登录用户 =================================
  // 实际项目替换为：登录接口返回后存入 localStorage 的用户标识（用户名/用户ID）
  const user = localStorage.getItem('loginUser') || 'default_user';
  console.log('user:::',user)
  // 备注：如果有登录页面，登录成功后执行 localStorage.setItem('loginUser', 真实用户标识)
  // ========================================================================================

  // 确定左右栏日期（validDates 格式：['2025-11-27', '2025-11-26', ...]）
  const rightDate = new Date(validDates[currentIndex]); // 转为 Date 对象
  const leftDate = validDates[currentIndex + 1] ? new Date(validDates[currentIndex + 1]) : rightDate;

//  // 更新日期显示
//  leftDateText.textContent = formatDateToMd(leftDate);
//  rightDateText.textContent = formatDateToMd(rightDate);

  // 显示加载
  showLoading(leftContainer);
  showLoading(rightContainer);

  // 并行获取左右栏数据
  const [rightData, leftData] = await Promise.all([
    fetchSingleDateData(formatDateToYmd(rightDate)),
    fetchSingleDateData(formatDateToYmd(leftDate))
  ]);

  // 提取右侧股票名称集合（用于左侧匹配）
  const rightStockNames = new Set();
  if (rightData) {
    rightData.forEach(boardData => {
      boardData.stocks?.forEach(stock => {
        const gpName = stock.gp_name?.trim();
        if (gpName) rightStockNames.add(gpName);
      });
    });
  }

  // ================================= 关键修改：传递 user 参数 =================================
  // 调用 renderSingleTable 时，最后一个参数补充传递 user（用户标识）
  await renderSingleTable(leftData || [], leftContainer, leftTitle, leftDate, rightStockNames, user);
  await renderSingleTable(rightData || [], rightContainer, rightTitle, rightDate, new Set(), user);
  // ==========================================================================================

  // 更新导航按钮状态和日期选择器
  updateNavButtonState();
  updateDateSelector();
}

/**
 * DOM加载完成后初始化（入口流程）
 */
document.addEventListener('DOMContentLoaded', async () => {
  // 初始化UI组件
  sectorTooltip.init();
  downloadButton.init();
  // 设置dateNavigation使用的函数引用
  setLoadDataByIndexFn(loadDataByIndex);
  setUpdateDateSelectorFn(updateDateSelector);
  initDateNavigation();

  // 获取DOM容器
  const leftContainer = document.getElementById('left-table-body');
  const rightContainer = document.getElementById('right-table-body');

  // 显示初始加载
  showLoading(leftContainer);
  showLoading(rightContainer);

  // 添加renderTable事件监听，用于板块选择后重新渲染表格
  document.addEventListener('renderTable', async (event) => {
    const { date } = event.detail;
    // 更新当前索引到对应日期
    const validDates = AppState.getValidDates();
    const dateStr = formatDateToYmd(date);
    const index = validDates.indexOf(dateStr);
    if (index !== -1) {
      AppState.setCurrentIndex(index);
      await loadDataByIndex();
    }
  });

  try {
    // 1. 获取所有有数据的日期
    await getAllValidDates();
    // 2. 初始化当前索引（默认0，最新日期）
    AppState.setCurrentIndex(0);
    // 3. 初始化日期选择器
    initDateSelector();
    // 4. 加载初始数据（调用修改后的 loadDataByIndex，自动传递 user）
    await loadDataByIndex();
  } catch (error) {
    hideLoading(leftContainer);
    hideLoading(rightContainer);
    alert('初始化失败：' + (error.message || '网络异常'));
    console.error('初始化异常:', error);
  } finally {
    AppState.setIsFinding(false);
  }
});

/**
 * 初始化日期选择器
 */
function initDateSelector() {
  const dateSelect = document.getElementById('date-select');
  if (!dateSelect) return;
  
  // 获取有效日期列表
  const validDates = AppState.getValidDates();
  if (!validDates || validDates.length === 0) return;
  
  // 清空现有选项
  dateSelect.innerHTML = '';
  
  // 添加日期选项
  validDates.forEach(date => {
    const option = document.createElement('option');
    option.value = date;
    option.textContent = formatDateToMd(new Date(date));
    dateSelect.appendChild(option);
  });
  
  // 设置当前选中的日期
  const currentIndex = AppState.getCurrentIndex();
  dateSelect.value = validDates[currentIndex];
  
  // 添加日期选择事件监听器
  dateSelect.addEventListener('change', async () => {
    const selectedDate = dateSelect.value;
    const validDates = AppState.getValidDates();
    const index = validDates.indexOf(selectedDate);
    if (index !== -1) {
      AppState.setIsDateChanging(true); // 设置日期切换标志
      AppState.setCurrentIndex(index);
      await loadDataByIndex();
      AppState.setIsDateChanging(false); // 清除日期切换标志
    }
  });
}

/**
 * 更新日期选择器的选中状态
 */
export function updateDateSelector() {
  const dateSelect = document.getElementById('date-select');
  if (!dateSelect) return;
  
  const validDates = AppState.getValidDates();
  const currentIndex = AppState.getCurrentIndex();
  if (validDates.length > 0 && currentIndex >= 0 && currentIndex < validDates.length) {
    dateSelect.value = validDates[currentIndex];
  }
}