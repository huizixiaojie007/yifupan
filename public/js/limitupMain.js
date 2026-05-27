import AppState from './state/appState.js';
import { getAllValidDates, fetchSingleDateData, fetchStockCollectionStatus } from './api/stockApi.js';
import { sectorTooltip } from './components/SectorTooltip.js';
import { downloadButton } from './components/DownloadButton.js';
import { initDateNavigation, updateNavButtonState, setLoadDataByIndexFn, setUpdateDateSelectorFn } from './navigation/dateNavigation.js';
import { renderSingleTable, showLoading, hideLoading } from './renderer/tableRenderer.js';
import { formatDateToMd, formatDateToYmd } from './utils/dateUtils.js';
import { BUSINESS_CONFIG } from './constants/configConstants.js';

export async function loadDataByIndex() {
  const validDates = AppState.getValidDates();
  const currentIndex = AppState.getCurrentIndex();

  const leftContainer = document.getElementById('left-table-body');
  const rightContainer = document.getElementById('right-table-body');
  const leftTitle = document.getElementById('left-title');
  const rightTitle = document.getElementById('right-title');

  if (validDates.length === 0) {
    hideLoading(leftContainer);
    hideLoading(rightContainer);
    leftTitle.textContent = BUSINESS_CONFIG.noDataText;
    rightTitle.textContent = BUSINESS_CONFIG.noDataText;
    return;
  }

  const user = localStorage.getItem('loginUser') || 'default_user';

  const rightDate = new Date(validDates[currentIndex]);
  const leftDate = validDates[currentIndex + 1] ? new Date(validDates[currentIndex + 1]) : rightDate;

  showLoading(leftContainer);
  showLoading(rightContainer);

  const [rightData, leftData] = await Promise.all([
    fetchSingleDateData(formatDateToYmd(rightDate)),
    fetchSingleDateData(formatDateToYmd(leftDate))
  ]);

  const rightStockNames = new Set();
  if (rightData) {
    rightData.forEach(boardData => {
      boardData.stocks?.forEach(stock => {
        const gpName = stock.gp_name?.trim();
        if (gpName) rightStockNames.add(gpName);
      });
    });
  }

  // 优化：只获取一次收藏状态，使用当前日期(rightDate)而不是leftDate
  const collected = await fetchStockCollectionStatus(user, formatDateToYmd(rightDate));

  await renderSingleTable(leftData || [], leftContainer, leftTitle, leftDate, rightStockNames, user, collected);
  await renderSingleTable(rightData || [], rightContainer, rightTitle, rightDate, new Set(), user, collected);

  updateNavButtonState();
  updateDateSelector();
}

function initDateSelector() {
  const dateSelect = document.getElementById('date-select');
  if (!dateSelect) return;

  const validDates = AppState.getValidDates();
  if (!validDates || validDates.length === 0) return;

  dateSelect.innerHTML = '';

  validDates.forEach(date => {
    const option = document.createElement('option');
    option.value = date;
    option.textContent = formatDateToMd(new Date(date));
    dateSelect.appendChild(option);
  });

  const currentIndex = AppState.getCurrentIndex();
  dateSelect.value = validDates[currentIndex];

  dateSelect.addEventListener('change', async () => {
    const selectedDate = dateSelect.value;
    const validDates = AppState.getValidDates();
    const index = validDates.indexOf(selectedDate);
    if (index !== -1) {
      AppState.setIsDateChanging(true);
      AppState.setCurrentIndex(index);
      await loadDataByIndex();
      AppState.setIsDateChanging(false);
    }
  });
}

function updateDateSelector() {
  const dateSelect = document.getElementById('date-select');
  if (!dateSelect) return;

  const validDates = AppState.getValidDates();
  const currentIndex = AppState.getCurrentIndex();

  if (validDates && validDates.length > 0) {
    dateSelect.value = validDates[currentIndex];
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    sectorTooltip.init();
    downloadButton.init();
    setLoadDataByIndexFn(loadDataByIndex);
    setUpdateDateSelectorFn(updateDateSelector);
    initDateNavigation();

    const validDates = await getAllValidDates();
    if (validDates && validDates.length > 0) {
      AppState.setValidDates(validDates);
      AppState.setCurrentIndex(0);

      // 初始化日期选择器选项
      initDateSelector();

      await loadDataByIndex();
    }
  } catch (error) {
    console.error('初始化失败:', error);
    hideLoading(document.getElementById('left-table-body'));
    hideLoading(document.getElementById('right-table-body'));
  }
});