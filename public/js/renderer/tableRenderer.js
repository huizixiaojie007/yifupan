import { TABLE_STYLES, LOADING_TEMPLATE } from '../constants/styleConstants.js';
import { TYPE_COLOR_MAP } from '../constants/styleConstants.js';
import { formatDateToMd, formatTime, formatDateToYmd } from '../utils/dateUtils.js'; // 新增 formatDateToYmd
import { getContrastColor } from '../utils/colorUtils.js';
import { trimStr, safeStr } from '../utils/stringUtils.js';
import { groupStocksBySector, sortSectors, sortStocks, groupStocks, formatBoardName } from './dataProcessor.js';
import { sectorTooltip } from '../components/SectorTooltip.js';
import { stockDetailPopup } from '../components/StockDetailPopup.js';
// 新增：导入收藏相关接口函数
import {
  fetchStockDetails,
  fetchStockKlineData,
  fetchStockCollectionStatus, // 新增
  toggleStockCollection,      // 新增
  fetchSingleDateData,        // 新增，用于板块点击后重新获取数据
  getStockInfo,               // 新增，用于获取实时股票信息
  getAllValidDates            // 新增，用于获取有效日期列表
} from '../api/stockApi.js';
import AppState from '../state/appState.js';

/**
 * 懒加载ECharts库（优先使用父窗口已加载的ECharts）
 * @returns {Promise<object>} ECharts对象
 */
async function loadECharts() {
    // 优先使用父窗口已加载的ECharts
    if (window.parent && window.parent.echarts && window.parent.echartsReady) {
        window.echarts = window.parent.echarts;
        return window.parent.echarts;
    }

    if (window.echarts) {
        return window.echarts;
    }

    // 如果父窗口也没有，则动态加载
    const script = document.createElement('script');
    script.src = 'https://cdn.bootcdn.net/ajax/libs/echarts/5.4.3/echarts.min.js';
    script.async = true;

    return new Promise((resolve, reject) => {
        script.onload = () => {
            resolve(window.echarts);
        };
        script.onerror = () => {
            reject(new Error('Failed to load ECharts'));
        };
        document.head.appendChild(script);
    });
}

/**
 * 检查当前时间是否在交易时间内（9:15 - 15:00）
 * @returns {boolean} 是否在交易时间内
 */
function isWithinTradingHours() {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  
  // 9:15 到 15:00
  if (hours === 9) {
    return minutes >= 15;
  } else if (hours > 9 && hours < 15) {
    return true;
  } else if (hours === 15) {
    return minutes === 0;
  }
  return false;
}

/**
 * 检查当前时间是否在交易时段内（9:15-11:30 和 13:00-15:00）
 * @returns {boolean} 是否在交易时段内
 */
function isWithinTradingSessionHours() {
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  
  // 上午交易时段：9:15 - 11:30
  if (hours === 9) {
    return minutes >= 15;
  } else if (hours === 10) {
    return true;
  } else if (hours === 11) {
    return minutes <= 30;
  } 
  // 下午交易时段：13:00 - 15:00
  else if (hours === 13 || hours === 14) {
    return true;
  } else if (hours === 15) {
    return minutes === 0;
  }
  return false;
}

/**
 * 统计当日涨停股票数据（总数量+各板块数量） @param {Array} stockData - 当日股票数据（boardData数组）
 * @returns {Object} 统计结果：{total: 总数量, sectors: 板块统计对象, sortedSectors: 按数量降序的板块数组}
 */
function calculateDailySectorStats(stockData) {
  // 1. 汇总当日所有股票并去重（按gp_no，避免重复统计）
  const allStocks = [];
  const stockNoSet = new Set(); // 去重用：存储股票代码
  stockData.forEach(boardData => {
    (boardData.stocks || []).forEach(stock => {
      if (stock.gp_no && !stockNoSet.has(stock.gp_no)) {
        stockNoSet.add(stock.gp_no);
        allStocks.push(stock);
      }
    });
  });

  // 2. 统计总数量
  const total = allStocks.length;

  // 3. 按板块分组统计数量
  const sectorStats = {};
  allStocks.forEach(stock => {
    const sector = safeStr(stock.sector, '未知板块');
    sectorStats[sector] = (sectorStats[sector] || 0) + 1;
  });

  // 4. 按数量降序排序板块（便于展示），"其他概念"始终在最后
  const sortedSectors = Object.entries(sectorStats)
    .sort((a, b) => {
      // 处理"其他概念"始终在最后
      if (a[0] === '其他概念' && b[0] !== '其他概念') {
        return 1; // a在后
      }
      if (a[0] !== '其他概念' && b[0] === '其他概念') {
        return -1; // a在前
      }
      // 其他情况按数量降序
      return b[1] - a[1];
    })
    .map(([sector, count]) => ({ sector, count }));

  return {
    total,
    sectors: sectorStats,
    sortedSectors
  };
}
/**
 * 渲染当日统计栏（返回DOM，不再直接插入）
 * @param {Object} stats - 统计结果
 * @param {Object} dynamicSectorColorMap - 板块颜色映射
 * @returns {HTMLElement} 统计栏DOM
 */
function renderDailyStatsBar(stats, dynamicSectorColorMap, dateMd, containerId) {
  // 1. 统计栏容器（核心：强制横向排列，仅超宽时换行）
  const statsBar = document.createElement('div');
  statsBar.className = `daily-stats-bar stats-bar-${dateMd.replace(/\//g, '-').replace(/:/g, '')}`;
  statsBar.dataset.date = dateMd; // 日期数据属性
  statsBar.dataset.containerId = containerId; // 容器ID数据属性
  statsBar.className = 'daily-stats-bar';
  statsBar.style.cssText = `
    width: 100%;
    padding: 6px 12px;
    margin: 8px 0;
    background-color: #f8f9fa;
    border-radius: 4px;
    border: 1px solid #eee;
    font-size: 12px;
    /* 核心：强制横向排列，仅超宽时换行 */
    display: flex;
    flex-direction: row; /* 显式指定横向 */
    flex-wrap: wrap;     /* 超宽时换行，而非一行一个 */
    justify-content: flex-start; /* 左对齐 */
    align-items: center; /* 垂直居中 */
    gap: 10px; /* 元素间距（适中，避免太挤） */
    box-sizing: border-box; /* 内边距不占宽度 */
    white-space: nowrap; /* 防止文本内部换行 */
  `;

  // 2. 总数量（红色加粗，固定样式）
  const totalSpan = document.createElement('span');
  totalSpan.style.cssText = `
    font-weight: 600;
    font-size: 15px;
    color: #dc3545;
    flex-shrink: 0; /* 不被挤压 */
  `;
  totalSpan.textContent = `总数：${stats.total}`;
  statsBar.appendChild(totalSpan);
  
  // 获取当前容器选中的板块
  const selectedSectors = AppState.getSelectedSectors(containerId);

  // 3. 板块数量标签（横向排列，紧凑且不换行）
  stats.sortedSectors.forEach(({ sector, count }) => {
    const sectorColor = dynamicSectorColorMap[sector] || '#CCCCCC';
    const textColor = getContrastColor(sectorColor);
    const isSelected = selectedSectors.has(sector);

    const sectorSpan = document.createElement('span');
    sectorSpan.style.cssText = `
      padding: 2px 8px;
      border-radius: 3px;
      background-color: ${isSelected ? sectorColor : '#e0e0e0'};
      color: ${isSelected ? textColor : '#666666'};
      font-size: 12px;
      flex-shrink: 0; /* 关键：不被挤压，保持横向 */
      white-space: nowrap; /* 板块名不换行 */
      line-height: 1.4; /* 垂直居中 */
      cursor: pointer;
      border: 2px solid ${isSelected ? '#2196f3' : 'transparent'};
      transition: all 0.2s ease;
    `;
    sectorSpan.textContent = `${sector}:${count}`;
    sectorSpan.dataset.sector = sector;

    // 存储容器ID到板块元素上
    sectorSpan.dataset.containerId = containerId;
    
    // 添加点击事件，实现选中/取消选中功能
    sectorSpan.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        // 1. 切换选中状态
        let currentSectors = new Set(AppState.getSelectedSectors(containerId));
        if (currentSectors.has(sector)) {
          currentSectors.delete(sector);
        } else {
          currentSectors.add(sector);
        }
        AppState.setSelectedSectors(containerId, currentSectors);
        
        // 2. 更新统计栏中所有板块的视觉状态
        const statsBar = sectorSpan.closest('.daily-stats-bar');
        const allSectorSpans = statsBar.querySelectorAll('[data-sector]');
        allSectorSpans.forEach(span => {
          const spanSector = span.dataset.sector;
          const isSelected = currentSectors.has(spanSector);
          const spanSectorColor = dynamicSectorColorMap[spanSector] || '#CCCCCC';
          const spanTextColor = getContrastColor(spanSectorColor);
          
          if (isSelected) {
            span.style.borderColor = '#2196f3';
            span.style.backgroundColor = spanSectorColor;
            span.style.color = spanTextColor;
          } else {
            span.style.borderColor = 'transparent';
            span.style.backgroundColor = '#e0e0e0';
            span.style.color = '#666666';
          }
        });
        
        // 3. 更新全选按钮的状态
        const selectAllButton = statsBar.querySelector('button[data-container-id]');
        if (selectAllButton) {
          const isAllSelected = stats.sortedSectors.every(({ sector }) => currentSectors.has(sector));
          selectAllButton.innerHTML = isAllSelected ? '✓' : '';
        }
        
        // 4. 重新渲染表格，使用完整的stockData，让renderSingleTable内部处理过滤
        const container = document.getElementById(containerId);
        if (container && container.dataset.date) {
          // 显示加载状态
          container.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #666;">加载中...</td></tr>';
          
          // 获取完整数据并重新渲染，让renderSingleTable内部根据选中状态过滤
          const dateStr = container.dataset.date;
          const date = new Date(dateStr);
          const dateYmd = formatDateToYmd(date);
          const stockData = await fetchSingleDateData(dateYmd) || [];
          
          const user = localStorage.getItem('loginUser') || 'default_user';
          const containerTitle = containerId === 'left-table-body' ? document.getElementById('left-title') : document.getElementById('right-title');
          
          // 使用完整的stockData，让renderSingleTable内部根据选中状态过滤
          await renderSingleTable(stockData, container, containerTitle, date, new Set(), user);
        }
      } catch (error) {
        console.error('板块点击事件处理错误:', error);
        const container = document.getElementById(containerId);
        if (container) {
          container.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #dc3545;">加载失败，请重试</td></tr>';
        }
      }
    });

    sectorSpan.addEventListener('mouseover', (e) => {
      sectorTooltip.showSectorTooltip(sector, e.clientX, e.clientY, e.target);
    });
    sectorSpan.addEventListener('mouseout', () => {
      sectorTooltip.hideTooltip();
    });

    statsBar.appendChild(sectorSpan);
  });

  // 4. 添加全选/取消全选按钮（使用更简单的按钮方案）
  const isAllSelected = stats.sortedSectors.every(({ sector }) => selectedSectors.has(sector));
  const selectAllButton = document.createElement('button');
  selectAllButton.style.cssText = `
    padding: 2px 6px;
    border-radius: 3px;
    background-color: #409eff;
    color: white;
    font-size: 10px;
    flex-shrink: 0;
    white-space: nowrap;
    line-height: 1.2;
    cursor: pointer;
    border: none;
    transition: all 0.2s ease;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
  `;
  // 根据当前状态设置按钮图标
  selectAllButton.innerHTML = isAllSelected ? '✓' : '';
  
  // 存储容器ID到按钮上
  selectAllButton.dataset.containerId = containerId;
  
  // 添加点击事件，实现全选/取消全选功能
  selectAllButton.addEventListener('click', async (e) => {
    e.stopPropagation();
    try {
      // 获取容器ID
      const containerId = selectAllButton.dataset.containerId;
      
      // 1. 根据按钮图标判断当前状态
      const isCurrentlyAllSelected = selectAllButton.innerHTML === '✓';
      
      // 2. 强制重置AppState中的选中板块
      let newSelectedSectors = new Set();
      if (!isCurrentlyAllSelected) {
        // 全选：选中所有板块
        stats.sortedSectors.forEach(({ sector }) => newSelectedSectors.add(sector));
      }
      
      // 3. 强制更新AppState - 使用公共方法确保状态同步
      AppState.setSelectedSectors(containerId, newSelectedSectors);
      
      // 4. 立即更新按钮图标，确保用户看到状态变化
      if (isCurrentlyAllSelected) {
        selectAllButton.innerHTML = '';
      } else {
        selectAllButton.innerHTML = '✓';
      }
      
      // 5. 强制更新所有板块的视觉状态
      const statsBar = selectAllButton.closest('.daily-stats-bar');
      const allSectorSpans = statsBar.querySelectorAll('[data-sector]');
      allSectorSpans.forEach(span => {
        const spanSector = span.dataset.sector;
        const isSelected = newSelectedSectors.has(spanSector);
        const spanSectorColor = dynamicSectorColorMap[spanSector] || '#CCCCCC';
        const spanTextColor = getContrastColor(spanSectorColor);
        
        // 强制更新视觉状态
        if (isSelected) {
          span.style.borderColor = '#2196f3';
          span.style.backgroundColor = spanSectorColor;
          span.style.color = spanTextColor;
        } else {
          span.style.borderColor = 'transparent';
          span.style.backgroundColor = '#e0e0e0';
          span.style.color = '#666666';
        }
      });
      
      // 6. 强制重新渲染表格
      const container = document.getElementById(containerId);
      if (container && container.dataset.date) {
        // 显示加载状态
        container.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #666;">加载中...</td></tr>';
        
        // 强制获取数据并重新渲染
        const dateStr = container.dataset.date;
        const date = new Date(dateStr);
        const dateYmd = formatDateToYmd(date);
        
        // 直接调用fetchSingleDateData获取数据
        const stockData = await fetchSingleDateData(dateYmd) || [];
        
        const user = localStorage.getItem('loginUser') || 'default_user';
        const containerTitle = containerId === 'left-table-body' ? document.getElementById('left-title') : document.getElementById('right-title');
        
        // 强制重新渲染表格
        await renderSingleTable(stockData, container, containerTitle, date, new Set(), user);
      }
    } catch (error) {
      console.error('全选按钮点击事件处理错误:', error);
      // 错误处理
      const containerId = selectAllButton.dataset.containerId;
      const container = document.getElementById(containerId);
      if (container) {
        container.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #dc3545;">加载失败，请重试</td></tr>';
      }
    }
  });
  
  statsBar.appendChild(selectAllButton);

  return statsBar;
}
/**
 * 显示加载提示
 * @param {HTMLElement} container - 目标容器
 */
export function showLoading(container) {
  container.innerHTML = LOADING_TEMPLATE;
}

/**
 * 隐藏加载提示（清空容器）
 * @param {HTMLElement} container - 目标容器
 */
export function hideLoading(container) {
  container.innerHTML = '';
}

// 新增：渲染K线区域
export function renderKlineArea(stock) {
  const gpName = stock.gp_name || '未知股票';
  const gpNo = stock.gp_no || '未知代码';
  const limitupDate = stock.date || ''; // 新增：获取涨停日期
  const klineArea = document.createElement('div');
  klineArea.className = 'kline-area';
  klineArea.dataset.gpName = gpName; // 增加数据属性，方便后续查找
  klineArea.dataset.gpNo = gpNo; // 关键补充：存储股票代码（供按钮调用接口）
  klineArea.dataset.limitupDate = limitupDate; // 新增：存储涨停日期

  klineArea.style.cssText = `
    width: 100%;
    height: 200px; /* K线图高度 */
    display: none; /* 默认隐藏 */
    border: 1px solid #eee;
    border-radius: 1px;
    box-sizing: border-box;
    overflow: hidden; /* 避免K线图超出容器 */
  `;

  // K线图容器（ECharts渲染目标）
  const klineChartDom = document.createElement('div');
  klineChartDom.id = `kline-chart-${gpName.replace(/\s/g, '')}`; // 唯一ID（去除股票名称空格）
  klineChartDom.style.width = '100%';
  klineChartDom.style.height = '100%';
  klineArea.appendChild(klineChartDom);

  // 加载提示
  const loadingTip = document.createElement('div');
  loadingTip.className = 'kline-loading';
  loadingTip.style.cssText = `
    position: absolute;
    top: 0px;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.8);
    color: #666;
    font-size: 12px;
    z-index: 10; /* 确保加载提示在最上层 */
  `;
  loadingTip.textContent = '加载K线数据中...';
  klineArea.appendChild(loadingTip);
  // 初始化为空数据（避免按钮逻辑误判）
  klineChartDom.dataset.klineData = JSON.stringify([]);
  return Promise.resolve(klineArea);
}

/**
 * 初始化ECharts K线图表
 * @param {string} gpName - 股票名称
 * @param {Array} klineData - 格式化后的K线数据
 * @param {HTMLElement} dom - 图表渲染DOM
 */
/**
 * 渲染日期选择器栏
 * @param {Date} currentDate - 当前日期
 * @param {string} containerId - 容器ID
 * @param {HTMLElement} targetTitle - 标题元素
 * @param {string} user - 操作用户
 * @returns {Promise<HTMLElement>} 日期选择器栏DOM
 */
async function renderDateSelectorBar(currentDate, containerId, targetTitle, user) {
  // 创建日期选择器容器
  const selectorContainer = document.createElement('div');
  selectorContainer.className = 'date-selector-bar';
  selectorContainer.style.cssText = `
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    padding: 8px 0;
    border-bottom: 1px solid #eee;
  `;
  
  // 获取有效日期列表
  let validDates = AppState.getValidDates();
  if (!validDates || validDates.length === 0) {
    validDates = await getAllValidDates();
  }
  
  // 转换为YYYY-MM-DD格式，用于显示和比较
  const formattedDates = validDates.map(date => formatDateToYmd(date));
  
  // 创建日期选择器
  const dateSelect = document.createElement('select');
  dateSelect.style.cssText = `
    padding: 4px 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 12px;
    background-color: white;
    cursor: pointer;
  `;
  
  // 添加选项
  formattedDates.forEach(dateStr => {
    const option = document.createElement('option');
    option.value = dateStr;
    // 显示格式：YYYY-MM-DD
    option.textContent = dateStr;
    // 设置当前日期为默认选项
    if (dateStr === formatDateToYmd(currentDate)) {
      option.selected = true;
    }
    dateSelect.appendChild(option);
  });
  
  // 创建标签
  const label = document.createElement('span');
  label.style.cssText = `
    font-size: 12px;
    color: #666;
    font-weight: 500;
  `;
  label.textContent = '选择日期：';
  
  // 添加到容器
  selectorContainer.appendChild(label);
  selectorContainer.appendChild(dateSelect);
  
  // 日期选择事件处理
  dateSelect.addEventListener('change', async () => {
    const selectedDateStr = dateSelect.value;
    const selectedDate = new Date(selectedDateStr);
    
    // 获取选中日期在有效日期列表中的索引
    const selectedIndex = formattedDates.indexOf(selectedDateStr);
    
    // 获取当前容器
    const container = document.getElementById(containerId);
    if (!container) return;
    
    try {
      // 显示加载状态
      container.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #666;">加载中...</td></tr>';
      
      // 获取当前日期的数据
      const currentDateData = await fetchSingleDateData(selectedDateStr);
      
      // 获取前一个日期的数据
      let prevDateData = [];
      if (selectedIndex > 0) {
        const prevDateStr = formattedDates[selectedIndex - 1];
        prevDateData = await fetchSingleDateData(prevDateStr);
      }
      
      // 渲染当前日期的表格
      await renderSingleTable(currentDateData, container, targetTitle, selectedDate, new Set(), user);
      
      // 如果是左侧容器，更新右侧容器的数据（假设右侧容器ID为right-table-body）
      if (containerId === 'left-table-body') {
        const rightContainer = document.getElementById('right-table-body');
        const rightTitle = document.getElementById('right-title');
        if (rightContainer && rightTitle && selectedIndex > 0) {
          const prevDate = new Date(formattedDates[selectedIndex - 1]);
          await renderSingleTable(prevDateData, rightContainer, rightTitle, prevDate, new Set(), user);
        }
      }
      
    } catch (error) {
      console.error('日期切换失败:', error);
      container.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 20px; color: #dc3545;">加载失败，请重试</td></tr>';
    }
  });
  
  return selectorContainer;
}

export async function initKlineChart(gpName, klineData, dom, limitupDate = '') {
  dom.style.display = 'block';
  dom.parentNode.style.display = 'block';

  // 确保echarts已加载
  await loadECharts();

  // 确保使用全局的echarts对象
  const chartInstance = window.echarts.init(dom);
  AppState.setKlineChartInstance(gpName, chartInstance);

  // 过滤有效数据（K线+成交量数据都需有效）
  const validData = klineData.filter(item =>
    item.length >= 6 && // 关键：成交量数据需在第6位（[时间,开,收,高,低,成交量]）
    item[1] !== null && item[1] !== undefined &&
    item[5] !== null && item[5] !== undefined // 确保成交量有效
  );

  // 提取日期并格式化，用于X轴显示
  const dates = validData.map(item => {
    const d = new Date(item[0]);
    return `${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`;
  });

  // 计算5日均线数据（只包含数值，不包含时间戳）
  const ma5Data = [];
  for (let i = 0; i < validData.length; i++) {
    if (i < 4) {
      // 前4天数据不足，不计算5日均线
      ma5Data.push(null);
    } else {
      // 计算过去5天收盘价的平均值
      const sum = validData.slice(i - 4, i + 1).reduce((acc, item) => acc + item[2], 0);
      const ma5 = sum / 5;
      ma5Data.push(ma5);
    }
  }

  // 准备K线数据（只包含数值，不包含时间戳）
  const candlestickData = validData.map(item => [
    parseFloat(item[1]), // 开盘价
    parseFloat(item[2]), // 收盘价
    parseFloat(item[3]), // 最低价
    parseFloat(item[4])  // 最高价
  ]);

  // 准备成交量数据（只包含数值，不包含时间戳）
  const volumeData = validData.map(item => parseFloat(item[5]));

  // ========== 新增：涨停日期标记 ==========
  let markLineData = [];
  if (limitupDate) {
    // 格式化涨停日期为 MM-DD 格式，与dates数组格式一致
    const limitupDateObj = new Date(limitupDate);
    const limitupDateStr = `${(limitupDateObj.getMonth() + 1).toString().padStart(2, '0')}-${limitupDateObj.getDate().toString().padStart(2, '0')}`;
    
    // 获取今日日期（格式化相同格式）
    const today = new Date();
    const todayStr = `${(today.getMonth() + 1).toString().padStart(2, '0')}-${today.getDate().toString().padStart(2, '0')}`;
    
    // 如果是今日，不显示标记线
    if (limitupDateStr === todayStr) {
      console.log(`[${gpName}] 涨停日期是今日，不显示标记线`);
    } else {
      // 查找涨停日期在K线数据中的索引
      const limitupDateIndex = dates.indexOf(limitupDateStr);
      if (limitupDateIndex !== -1) {
        markLineData = [{
          name: '涨停日期',
          xAxis: limitupDateIndex,
          lineStyle: {
            color: '#ff9800', // 与收藏页面标记线颜色一致
            width: 2,
            type: 'dashed'
          },
          label: {
            show: true,
            position: 'end',
            formatter: '涨停',
            fontSize: 10,
            color: '#ff9800' // 与收藏页面标记线颜色一致
          }
        }];
        console.log(`[${gpName}] 涨停日期标记已添加，索引: ${limitupDateIndex}`);
      } else {
        console.log(`[${gpName}] 未找到涨停日期 ${limitupDateStr} 在K线数据中`);
      }
    }
  }
  // ========== 涨停日期标记结束 ==========

  // K线+成交量 联动配置
  const option = {
    // 关键1：共享Tooltip，同时显示K线和成交量数据
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
      zIndex: 99999, // 提升层级，避免遮挡
      appendToBody: true, // 挂载到body，彻底解决遮挡
      width: 180,
      textStyle: { fontSize: 10, color: '#333' },
      formatter: params => {
        const klineParams = params.find(p => p.seriesType === 'candlestick');
        if (!klineParams) return '';

        // 获取当前数据索引
        const dataIndex = klineParams.dataIndex;
        // 从dates数组中获取对应的日期
        const formatDate = dates[dataIndex] || '';
        // 获取K线数据
        const klineData = klineParams.data;
        // 获取成交量数据（直接从volumeData数组获取）
        const volume = volumeData[dataIndex] || 0;

        return `
          <div style="font-size: 10px; margin-bottom: 1px; font-weight: 500;">日期：${formatDate}</div>
          <div style="font-size: 10px; margin-bottom: 1px;">开盘：${klineData[0].toFixed(2)}</div>
          <div style="font-size: 10px; margin-bottom: 1px;">收盘：${klineData[1].toFixed(2)}</div>
          <div style="font-size: 10px; margin-bottom: 1px;">最低：${klineData[2].toFixed(2)}</div>
          <div style="font-size: 10px; margin-bottom: 1px;">最高：${klineData[3].toFixed(2)}</div>
          <div style="font-size: 10px;">成交量：${(volume/1000000).toFixed(2)}万</div>
        `;
      }
    },
    // 关键3：两个Grid布局（上：K线，下：成交量）
    grid: [
      // 上Grid：K线图（占70%高度）
      {
        left: '1%',
        right: '1%',
        top: '2%',
        bottom: '32%', // 预留32%高度给成交量+滑动条
        containLabel: true
      },
      // 下Grid：成交量图（占28%高度）
      {
        left: '5%',
        right: '1%',
        top: '70%', // 从70%位置开始（与上Grid间距2%）
        bottom: '4%',
        containLabel: true
      }
    ],

    // 关键4：两个x轴（分别对应两个Grid，同步联动）
    xAxis: [
      // 上x轴（K线图）：隐藏标签（避免重复）
      {
        type: 'category',
        gridIndex: 0, // 绑定上Grid
        data: dates,
        axisLabel: { show: false }, // 隐藏上x轴标签
        axisTick: { show: false }, // 隐藏上x轴刻度
        splitLine: { show: false },
        alignTicks: true // 与下x轴刻度对齐
      },
      // 下x轴（成交量图）：显示标签
      {
        type: 'category',
        gridIndex: 1, // 绑定下Grid
        data: dates,
        axisLabel: {
          fontSize: 8,
          interval: Math.floor(dates.length / 5), // 显示适量的日期标签
          rotate: 30
        },
        axisTick: { alignWithLabel: true },
        splitLine: { show: false },
        alignTicks: true // 与上x轴刻度对齐
      }
    ],

    // 关键5：两个y轴（分别对应两个图表）
    yAxis: [
      // 上y轴（K线图）：价格轴
      {
        type: 'value',
        gridIndex: 0, // 绑定上Grid
        scale: true,
        axisLabel: { fontSize: 10 },
        splitLine: { lineStyle: { color: '#eee' } }
      },
      // 下y轴（成交量图）：成交量轴
      {
        type: 'value',
        gridIndex: 1, // 绑定下Grid
        scale: true,
        axisLabel: { show: true,  formatter: '  '}, // 隐藏上y轴标签
        max: function(value) {
          // 成交量轴最大刻度设为最大值的1.3倍，避免顶部贴边
          return value.max * 1.2;
        }
      }
    ],

    // 关键6：三个Series（K线+MA5+成交量）
    series: [
      // 原有K线Series（绑定上Grid和上y轴）
      {
        type: 'candlestick',
        name: 'K线',
        xAxisIndex: 0, // 绑定上x轴
        yAxisIndex: 0, // 绑定上y轴
        data: candlestickData, // 使用处理后的K线数据
        itemStyle: {
          color: '#ef4444', // 阳线红
          color0: '#22c55e', // 阴线绿
          borderColor: '#ef4444',
          borderColor0: '#22c55e'
        },
        barWidth: '45%',
        // 新增：添加涨停日期标记线
        markLine: {
          symbol: 'none',
          data: markLineData
        }
      },
      // 新增MA5均线Series（绑定上Grid和上y轴）
      {
        type: 'line',
        name: 'MA5',
        xAxisIndex: 0, // 绑定上x轴
        yAxisIndex: 0, // 绑定上y轴
        data: ma5Data, // 使用处理后的MA5数据
        symbol: 'none', // 不显示点
        lineStyle: {
          color: '#FF9500', // 5日均线用橙色
          width: 1.5
        },
        smooth: false, // 不使用平滑曲线
        emphasis: {
          focus: 'series'
        }
      },
      // 新增成交量Series（绑定下Grid和下y轴）
      {
        type: 'bar',
        name: '成交量',
        xAxisIndex: 1, // 绑定下x轴
        yAxisIndex: 1, // 绑定下y轴
        data: volumeData, // 使用处理后的成交量数据
        // 成交量颜色与K线涨跌对应（阳线红，阴线绿）
        itemStyle: {
          color: params => {
            const dataIndex = params.dataIndex;
            const klineData = candlestickData[dataIndex];
            // 收盘>开盘：阳线（红），否则：阴线（绿）
            return klineData[1] > klineData[0] ? '#ef4444' : '#22c55e';
          }
        },
        barWidth: '60%' // 成交量柱宽度
      }
    ]
  };

  chartInstance.setOption(option);

  // 窗口resize防抖适配
  const debounce = (fn, delay = 200) => {
    let timer = null;
    return () => {
      clearTimeout(timer);
      timer = setTimeout(fn, delay);
    };
  };
  window.addEventListener('resize', debounce(() => chartInstance.resize()));

  return chartInstance;
}

/**
 * 渲染单个日期的表格（新增 user 和 date 参数）
 * @param {Array} stockData - 股票数据
 * @param {HTMLElement} targetContainer - 目标容器
 * @param {HTMLElement} targetTitle - 标题元素
 * @param {Date} date - 日期（Date 对象）
 * @param {Set} matchStockNames - 匹配股票名称集合
 * @param {string} user - 操作用户标识（新增参数）
 * @returns {Promise<void>}
 */
export async function renderSingleTable(stockData, targetContainer, targetTitle, date, matchStockNames = new Set(), user, collected = null) {
  hideLoading(targetContainer);
  const dateMd = formatDateToMd(date);
  const dynamicSectorColorMap = AppState.getDynamicSectorColorMap();
  // 格式化日期为 YYYY-MM-DD（传递给接口）
  const dateYmd = formatDateToYmd(date);
  targetTitle.textContent = `${dateMd}日连板天梯`;

  // ========== 最终修正：插入到「标题下、表格前」 ==========
  // 1. 方案1：清除「标题父元素内」所有统计栏（最精准）
  const titleParent = targetTitle.parentElement;
  if (titleParent) {
    const oldStatsBars = titleParent.querySelectorAll('.daily-stats-bar');
    oldStatsBars.forEach(bar => bar.remove());
  }
    // 2. 方案2：兜底清除「表格容器所在区域」所有统计栏（双重保障）
  const tableParent = targetContainer.closest('.table-container') || targetContainer.parentElement?.parentElement;
  if (tableParent) {
    const oldStatsBars = tableParent.querySelectorAll('.daily-stats-bar');
    oldStatsBars.forEach(bar => bar.remove());
  }

  // 2. 计算统计数据
  const dailyStats = calculateDailySectorStats(stockData);

  // 3. 获取当前容器的选中状态，用于过滤股票和渲染统计栏
  const containerId = targetContainer.id;
  
  // 4. 获取当前日期所有可用板块
  const currentDateSectors = new Set();
  dailyStats.sortedSectors.forEach(({ sector }) => {
    currentDateSectors.add(sector);
  });
  
  // 5. 获取当前选中的板块集合
  let selectedSectors = AppState.getSelectedSectors(containerId);
  
  // 6. 检查是否正在切换日期
  const isDateChanging = AppState.getIsDateChanging();
  
  // 7. 检查是否是首次加载（容器是否已经初始化）
  const isFirstLoad = !AppState.isContainerInitialized(containerId);
  
  if (isDateChanging || isFirstLoad) {
    // 正在切换日期或首次加载：选中当前日期的所有板块
    AppState.setSelectedSectors(containerId, currentDateSectors);
    selectedSectors = AppState.getSelectedSectors(containerId);
  } else {
    // 不是正在切换日期：过滤选中板块，只保留当前日期存在的板块
    const filteredSelectedSectors = new Set(
      Array.from(selectedSectors).filter(sector => currentDateSectors.has(sector))
    );
    
    // 只有当原始选中板块不为空，但过滤后为空时，才默认选中所有板块
    // 这样可以允许用户主动取消全选（即选中板块为空）
    if (selectedSectors.size > 0 && filteredSelectedSectors.size === 0) {
      AppState.setSelectedSectors(containerId, currentDateSectors);
      selectedSectors = AppState.getSelectedSectors(containerId);
    } else {
      // 否则，使用过滤后的板块集合（包括空集合，允许用户取消全选）
      AppState.setSelectedSectors(containerId, filteredSelectedSectors);
      selectedSectors = AppState.getSelectedSectors(containerId);
    }
  }
  
  // 5. 为targetContainer设置data-date属性，以便点击板块时能够获取到日期信息
  targetContainer.dataset.date = formatDateToYmd(date);
  
  // 6. 渲染统计栏，此时selectedSectors已经正确初始化
  const statsBar = renderDailyStatsBar(dailyStats, dynamicSectorColorMap, dateMd, containerId);

  // 7. 精准插入：表格（table）标签的正前方（标题下方、表格上方）
  const tableElement = targetContainer.parentElement; // tbody 的父元素是 table 标签
  if (tableElement) {
    // 核心：插入到 <table> 前面（标题下、表格上）
    tableElement.before(statsBar);
  } else {
    // 兜底：标题后方（兼容特殊DOM结构）
    targetTitle.after(statsBar);
  }
  // =========================================

  for (const boardData of stockData) {
    const stocks = boardData.stocks || [];
    let boardName = boardData.limitup_days || '';

    // 根据选中的板块过滤股票
    const filteredStocks = stocks.filter(stock => {
      const sector = safeStr(stock.sector, '未知板块');
      return selectedSectors.has(sector);
    });

    const stocksBySector = groupStocksBySector(filteredStocks);
    const sortedSectorNames = sortSectors(stocksBySector);
    const sortedStocks = [];
    sortedSectorNames.forEach(sector => sortedStocks.push(...sortStocks(stocksBySector[sector])));
    const stockGroups = groupStocks(sortedStocks);
    const formattedBoardName = formatBoardName(boardName);
    // 如果没有传入collected，则获取收藏状态
    if (collected === null) {
      collected = await fetchStockCollectionStatus(user, dateYmd);
    }

    for (const [groupIndex, stockGroup] of stockGroups.entries()) {
      const row = document.createElement('tr');
      row.style.borderBottom = '1px solid #eee';
      row.appendChild(renderBoardCell(formattedBoardName, groupIndex));

      // 批量渲染：传递 user 和 dateYmd 给 renderStockCell
      const cellPromises = stockGroup.slice(0, 3).map(stock =>
        renderStockCell(stock, targetContainer.id, matchStockNames, dynamicSectorColorMap, collected)
      );
      // 补充空单元格（不足3列时）
      while (cellPromises.length < 3) {
        cellPromises.push(renderStockCell(null, targetContainer.id, matchStockNames, dynamicSectorColorMap, collected));
      }

      const stockCells = await Promise.all(cellPromises);
      stockCells.forEach(cell => row.appendChild(cell));
      targetContainer.appendChild(row);
    }
  }

  // 新增：检查K线是否处于显示状态，如果是，重新初始化K线图表
  if (AppState.getIsKlineShow?.()) {
    console.log('表格重新渲染后，K线处于显示状态，开始重新初始化K线图表');
    // 获取所有新渲染的股票单元格
    const allStockCells = document.querySelectorAll('.stock-cell');
    const stockCells = Array.from(allStockCells);

    // 从showKlineButton实例获取loadAllKlineData方法，用于处理没有缓存数据的情况
    const showKlineButton = window.showKlineButtonInstance;

    // 为每个股票单元格重新初始化K线图表
    for (const cell of stockCells) {
      const klineArea = cell.querySelector('.kline-area');
      const klineChartDom = klineArea?.querySelector('div[id^="kline-chart-"]');
      const loadingTip = klineArea?.querySelector('.kline-loading');
      if (!klineArea || !klineChartDom || !loadingTip) continue;

      // 获取股票核心信息
      const gpName = klineArea.dataset.gpName;
      const gpNo = klineArea.dataset.gpNo;
      const limitupDate = klineArea.dataset.limitupDate; // 新增：获取涨停日期
      if (!gpName || !gpNo) continue;

      // 优先从AppState缓存获取数据
      const klineData = AppState.getKlineData(gpName);
      if (klineData && klineData.length) {
        console.log(`[${gpName}] 表格重新渲染后，使用缓存数据初始化K线图表`);
        // 显示K线容器
        klineArea.style.display = 'block';
        klineChartDom.style.display = 'block';
        // 使用缓存数据初始化图表（传递涨停日期）
        await initKlineChart(gpName, klineData, klineChartDom, limitupDate);
        // 隐藏加载提示
        loadingTip.style.display = 'none';
      } else {
        // 如果没有缓存数据，确保K线容器显示并显示加载提示
        console.log(`[${gpName}] 表格重新渲染后，无缓存数据，准备加载`);
        klineArea.style.display = 'block';
        klineChartDom.style.display = 'block';
        loadingTip.style.display = 'flex';
      }
    }

    // 如果showKlineButton实例存在，调用其_loadAllKlineData方法处理没有缓存数据的情况
    if (showKlineButton && typeof showKlineButton._loadAllKlineData === 'function') {
      console.log('调用showKlineButton._loadAllKlineData处理无缓存数据的股票');
      showKlineButton._loadAllKlineData();
    }
  }
}
/**
 * 渲染板数单元格
 * @param {string} boardName - 格式化后的板数名称
 * @param {number} groupIndex - 分组索引（0为第一个分组，显示板数）
 * @returns {HTMLElement} 板数单元格DOM
 */
function renderBoardCell(boardName, groupIndex) {
  const boardCell = document.createElement('td');
  boardCell.className = 'board-cell';
  boardCell.style.cssText = TABLE_STYLES.boardCell;

  if (groupIndex === 0) {
    boardCell.textContent = `${boardName}板`;
  }

  return boardCell;
}

/**
 * 渲染股票单元格（新增 user 和 date 参数）
 * @param {Object|null} stock - 股票数据
 * @param {string} containerId - 容器ID
 * @param {Set} matchStockNames - 匹配股票名称集合
 * @param {Object} dynamicSectorColorMap - 板块颜色映射
 * @param {string} user - 操作用户标识（新增参数）
 * @param {string} date - 日期（YYYY-MM-DD，新增参数）
 * @returns {Promise<HTMLElement>}
 */
async function renderStockCell(stock, containerId, matchStockNames, dynamicSectorColorMap, collected) {
  const stockCell = document.createElement('td');
  stockCell.className = 'stock-cell';
  stockCell.style.cssText = `${TABLE_STYLES.stockCell} position: relative; padding: 8px; cursor: pointer;`;

  if (!stock) return stockCell;

  const sector = safeStr(stock.sector, '未知板块');
  const sectorColor = dynamicSectorColorMap[sector] || '#CCCCCC';
  const textColor = getContrastColor(sectorColor);
  const isLeftContainer = containerId === 'left-table-body';
  const gpName = trimStr(stock.gp_name);
  const gpNo = stock.gp_no || '';

  if (isLeftContainer && gpName && matchStockNames.has(gpName)) {
    stockCell.style.border = '2px solid #dc3545';
    stockCell.style.borderRadius = '4px';
  }
  if (stock.day_limitup && stock.day_limitup !== '首板涨停') {
    stockCell.style.backgroundColor = '#ffebeb';
  }

  const contentWrapper = document.createElement('div');
  contentWrapper.style.cssText = 'display: flex; flex-direction: column; gap: 2px; width: 100%;';
  stockCell.appendChild(contentWrapper);

  // 只有右侧容器且在交易时间内才显示实时股票涨跌信息
  // if (containerId === 'right-table-body' && isWithinTradingHours()) {
  //   contentWrapper.appendChild(await renderRealTimeStockInfoArea(stock));
  // }
  contentWrapper.appendChild(renderTimeSectorArea(stock, sector, sectorColor, textColor, collected));
  contentWrapper.appendChild(renderStockNameArea(stock, gpName));
  contentWrapper.appendChild(renderReasonArea(stock));
  contentWrapper.appendChild(renderBottomInfoArea(stock));

  // K线区域
  const klineArea = await renderKlineArea(stock);
  stockCell.appendChild(klineArea);
  if (AppState.getIsKlineShow?.()) { // 可选链避免方法不存在报错
    klineArea.style.display = 'block';
  }

  // 为整个股票单元格添加点击事件，在新窗口中打开
  stockCell.addEventListener('click', (e) => {
    e.stopPropagation();
    if (gpNo) {
      window.open(`/public/stock_detail.html?gp_no=${gpNo}`, '_blank');
    }
  });

  return stockCell;
}

/**
 * 渲染实时股票涨跌信息区域
 * @param {Object} stock - 股票数据
 * @returns {Promise<HTMLElement>} 实时股票涨跌信息区域DOM
 */
async function renderRealTimeStockInfoArea(stock) {
  const realTimeArea = document.createElement('div');
  realTimeArea.className = 'real-time-stock-info';
  realTimeArea.style.cssText = `
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 2px;
    padding: 2px 0;
  `;

  // 存储股票代码，用于后续刷新
  realTimeArea.dataset.stockNo = stock.gp_no;

  // 显示加载状态
  realTimeArea.innerHTML = '<span style="color: #666;">加载中...</span>';

  // 定义更新函数
  const updateRealTimeInfo = async () => {
    try {
      // 调用getStockInfo接口获取实时数据
      const realTimeData = await getStockInfo(stock.gp_no);
      
      if (realTimeData) {
        // 清空当前内容
        realTimeArea.innerHTML = '';

        // 计算开盘涨跌幅
        if (realTimeData['今开'] && realTimeData['昨收']) {
          const openPrice = parseFloat(realTimeData['今开']);
          const prevClose = parseFloat(realTimeData['昨收']);
          if (!isNaN(openPrice) && !isNaN(prevClose) && prevClose > 0) {
            const openChangePercent = ((openPrice - prevClose) / prevClose * 100).toFixed(1);
            if (!isNaN(parseFloat(openChangePercent))) {
              const openChangeColor = parseFloat(openChangePercent) >= 0 ? '#ef4444' : '#22c55e';
              const openChangeSpan = document.createElement('span');
              openChangeSpan.style.cssText = `
                color: ${openChangeColor};
                font-weight: 500;
              `;
              openChangeSpan.textContent = `开:${openChangePercent}%`;
              realTimeArea.appendChild(openChangeSpan);
            } else {
              const openChangeSpan = document.createElement('span');
              openChangeSpan.style.cssText = `
                color: #999;
                font-weight: 500;
              `;
              openChangeSpan.textContent = `开:--`;
              realTimeArea.appendChild(openChangeSpan);
            }
          } else {
            const openChangeSpan = document.createElement('span');
            openChangeSpan.style.cssText = `
              color: #999;
              font-weight: 500;
            `;
            openChangeSpan.textContent = `开:--`;
            realTimeArea.appendChild(openChangeSpan);
          }
        } else {
          const openChangeSpan = document.createElement('span');
          openChangeSpan.style.cssText = `
            color: #999;
            font-weight: 500;
          `;
          openChangeSpan.textContent = `开:--`;
          realTimeArea.appendChild(openChangeSpan);
        }

        // 涨跌幅
        if (realTimeData['涨跌幅(%)']) {
          const changePercentValue = parseFloat(realTimeData['涨跌幅(%)']);
          if (!isNaN(changePercentValue)) {
            const changePercent = (changePercentValue / 100).toFixed(1);
            if (!isNaN(parseFloat(changePercent))) {
              const changePercentColor = parseFloat(changePercent) >= 0 ? '#ef4444' : '#22c55e';
              const changePercentSpan = document.createElement('span');
              changePercentSpan.style.cssText = `
                color: ${changePercentColor};
                font-weight: 500;
              `;
              changePercentSpan.textContent = `现:${changePercent}%`;
              realTimeArea.appendChild(changePercentSpan);
            } else {
              const changePercentSpan = document.createElement('span');
              changePercentSpan.style.cssText = `
                color: #999;
                font-weight: 500;
              `;
              changePercentSpan.textContent = `现:--`;
              realTimeArea.appendChild(changePercentSpan);
            }
          } else {
            const changePercentSpan = document.createElement('span');
            changePercentSpan.style.cssText = `
              color: #999;
              font-weight: 500;
            `;
            changePercentSpan.textContent = `现:--`;
            realTimeArea.appendChild(changePercentSpan);
          }
        } else {
          const changePercentSpan = document.createElement('span');
          changePercentSpan.style.cssText = `
            color: #999;
            font-weight: 500;
          `;
          changePercentSpan.textContent = `现:--`;
          realTimeArea.appendChild(changePercentSpan);
        }

        // 换手率
        if (realTimeData['换手率(%)']) {
          const turnoverRateValue = parseFloat(realTimeData['换手率(%)']);
          if (!isNaN(turnoverRateValue)) {
            const turnoverRate = (turnoverRateValue / 100).toFixed(1);
            if (!isNaN(parseFloat(turnoverRate))) {
              const turnoverRateSpan = document.createElement('span');
              turnoverRateSpan.style.cssText = `
                color: #b7179cff;
              `;
              turnoverRateSpan.textContent = `换: ${turnoverRate}%`;
              realTimeArea.appendChild(turnoverRateSpan);
            } else {
              const turnoverRateSpan = document.createElement('span');
              turnoverRateSpan.style.cssText = `
                color: #999;
              `;
              turnoverRateSpan.textContent = `换: --`;
              realTimeArea.appendChild(turnoverRateSpan);
            }
          } else {
            const turnoverRateSpan = document.createElement('span');
            turnoverRateSpan.style.cssText = `
              color: #999;
            `;
            turnoverRateSpan.textContent = `换: --`;
            realTimeArea.appendChild(turnoverRateSpan);
          }
        } else {
          const turnoverRateSpan = document.createElement('span');
          turnoverRateSpan.style.cssText = `
            color: #999;
          `;
          turnoverRateSpan.textContent = `换: --`;
          realTimeArea.appendChild(turnoverRateSpan);
        }
      } else {
        // 无数据时显示默认信息
        realTimeArea.innerHTML = '<span style="color: #999;">暂无实时数据</span>';
      }
    } catch (error) {
      console.error('获取实时股票信息失败:', error);
      realTimeArea.innerHTML = '<span style="color: #999;">实时数据获取失败</span>';
    }
  };

  // 初始加载数据
  await updateRealTimeInfo();

  // 只有在交易时段内才添加定时刷新功能（1分钟刷新一次）
  if (isWithinTradingSessionHours()) {
    const refreshInterval = setInterval(updateRealTimeInfo, 600000);
    
    // 存储定时器ID到DOM元素上，以便后续清除
    realTimeArea.dataset.refreshIntervalId = refreshInterval;

    // 添加清理函数，当元素被移除时清除定时器
    realTimeArea._cleanup = () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  } else {
    // 非交易时段，不添加定时刷新
    realTimeArea._cleanup = () => {};
  }

  return realTimeArea;
}

/**
 * 渲染时间+板块区域（修复：添加 collected 参数）
 * @param {Object} stock - 股票数据
 * @param {string} sector - 板块名称
 * @param {string} sectorColor - 板块颜色
 * @param {string} textColor - 文字颜色
 * @param {boolean} collected - 是否已收藏（新增参数）
 * @returns {HTMLElement} 时间+板块区域DOM
 */
function renderTimeSectorArea(stock, sector, sectorColor, textColor, collected) {
  const timeSectorDiv = document.createElement('div');
  timeSectorDiv.className = 'time-sector';
  timeSectorDiv.style.display = 'flex';
  timeSectorDiv.style.alignItems = 'center';
  timeSectorDiv.style.gap = '4px'; // 增加间距，避免按钮挤在一起
  timeSectorDiv.style.marginBottom = '2px';

  // ================================= 新增：收藏按钮 =================================
  const collectBtn = document.createElement('span');
  collectBtn.className = 'collect-btn';
  collectBtn.dataset.gpName = stock.gp_name || '';
  collectBtn.style.cssText = `
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    user-select: none;
  `;
  // 修复：collected 参数已传入，可正常使用
  if (collected.includes(stock.gp_name)) {
    collectBtn.textContent = '★';
    collectBtn.style.color = '#ff4d4f';
    collectBtn.dataset.collected = 'true';
  } else {
    collectBtn.textContent = '★';
    collectBtn.style.color = '#ccc';
    collectBtn.dataset.collected = 'false';
  }

  // hover效果增强
  collectBtn.addEventListener('mouseover', () => {
    if (collectBtn.dataset.collected === 'false') {
      collectBtn.style.color = '#ff7875';
    } else {
      collectBtn.style.color = '#ff1f1f';
    }
  });
  collectBtn.addEventListener('mouseout', () => {
    if (collectBtn.dataset.collected === 'false') {
      collectBtn.style.color = '#ccc';
    } else {
      collectBtn.style.color = '#ff4d4f';
    }
  });

  // 点击事件：切换收藏状态+同步数据库
  collectBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    const gpName = stock.gp_name;
    const isCurrentlyCollected = collectBtn.dataset.collected === 'true';
    // 直接使用函数参数中的 user 和 date（不再报错）
//    const currentUser = localStorage.getItem('loginUser') || 'default_user';
    const currentUser = localStorage.getItem('loginUser');
    console.log("time  currentUser::::",currentUser)
    const currentDate = stock.date;

    if (collectBtn.disabled) return;
    collectBtn.disabled = true;

    try {
      // 传递所有必要参数（含 user 和 date）
      const result = await toggleStockCollection(gpName, !isCurrentlyCollected, currentUser, currentDate);
      if (result) {
        collectBtn.textContent = '★';
        collectBtn.style.color = !isCurrentlyCollected ? '#ff4d4f' : '#ccc';
        collectBtn.dataset.collected = String(!isCurrentlyCollected);
      } else {
        alert(`操作失败：${result.message || '服务器异常'}`);
      }
    } catch (error) {
      alert('收藏操作失败，请重试');
    } finally {
      collectBtn.disabled = false;
    }
  });
  // =================================================================================

  timeSectorDiv.appendChild(collectBtn);

    // 分数显示（优化：加粗+醒目色+超链接）
    const scoreSpan = document.createElement('span');
    scoreSpan.className = 'score-info';
    scoreSpan.style.fontSize = '12px';
    scoreSpan.style.color = '#FF4400'; // 备用色（无分数时显示）
    const score = stock.score ? parseFloat(stock.score).toFixed(1) : '';

    // 有分数时才创建超链接
    if (score) {
        // 创建超链接标签
        const scoreLink = document.createElement('a');
        scoreLink.target = "_blank"; // 强制在新标签页打开

        // 超链接地址（按需替换：比如股票详情页链接，示例用股票代码拼接）
         //① 若有股票代码：
        const gp_no = stock.gp_no.split('.')[0];
        scoreLink.href = `https://data.eastmoney.com/stockcomment/stock/${gp_no}.html`;

        // 超链接样式（加粗+醒目色+去除下划线）
        scoreLink.style.fontSize = '12px';
        scoreLink.style.fontWeight = 'bold'; // 字体加粗
        scoreLink.style.color = '#FF9500'; // 醒目橙红色（可换：#E63946 红 / #FF9500 橙）
//        scoreLink.style.textDecoration = 'none'; // 去除默认下划线
        // 鼠标悬浮样式（可选：加深颜色+加下划线）
        scoreLink.style.cursor = 'pointer';
//        scoreLink.onmouseover = () => {
//            scoreLink.style.color = '#E03A3E'; // 悬浮加深色
//            scoreLink.style.textDecoration = 'underline';
//        };
//        scoreLink.onmouseout = () => {
//            scoreLink.style.color = '#FF4400'; // 恢复原颜色
//            scoreLink.style.textDecoration = 'none';
//        };

        // 设置超链接文本
        scoreLink.textContent = score;
        // 超链接放入span
        scoreSpan.appendChild(scoreLink);
    } else {
         scoreSpan.textContent = '--';
    }

    timeSectorDiv.appendChild(scoreSpan);

    // 时间显示
  const timeSpan = document.createElement('span');
  timeSpan.className = 'time-info';
  timeSpan.style.fontSize = '10px';
  timeSpan.style.color = '#666';
  // 核心处理：取前5位，空则显示"未知时间"
  const rawTime = stock.last_limitup_time || '';
  const shortTime = rawTime ? rawTime.slice(0, 5) : '';
  timeSpan.textContent = shortTime || '未知时间';
  timeSectorDiv.appendChild(timeSpan);

  // 龙虎榜标识
  if (stock.longhu) {
    const longhuSpan = document.createElement('span');
    longhuSpan.className = 'longhu-info';
    longhuSpan.style.fontSize = '11px';
    
    // 根据龙虎榜详情的第一个字设置颜色
    const longhuDetail = stock.longhu_detail || '';
    const firstChar = longhuDetail.charAt(0);
    let longhuColor = '#00FF00'; // 默认绿色
    
    if (firstChar === '1') {
      longhuColor = '#1582e8ff'; // 黄色
    } else if (firstChar === '2') {
      longhuColor = '#FF9800'; // 橙色
    } else if (firstChar >= '3' && firstChar <= '9') {
      longhuColor = '#FF4D4F'; // 红色
    }
    
    longhuSpan.style.color = longhuColor;
    longhuSpan.textContent = '榜';
    
    // 添加龙虎榜详情tooltip
    longhuSpan.addEventListener('mouseover', (e) => {
      sectorTooltip.showReasonDetailTooltip(stock.longhu_detail || '暂无龙虎榜详情', e.clientX, e.clientY, e.target);
    });
    longhuSpan.addEventListener('mouseout', () => {
      sectorTooltip.hideTooltip();
    });
    
    timeSectorDiv.appendChild(longhuSpan);
  }

  // 板块元素（保持不变）
  const sectorSpan = document.createElement('span');
  sectorSpan.className = 'sector-info';
  sectorSpan.dataset.sector = sector;
  sectorSpan.style.cssText = `
    background-color: ${sectorColor};
    color: ${textColor};
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 500;
    cursor: help;
    display: inline-block;
    min-width: 40px;
    text-align: center;
  `;
  sectorSpan.textContent = sector;

  sectorSpan.addEventListener('mouseover', (e) => {
    sectorTooltip.showSectorTooltip(e.target.dataset.sector, e.clientX, e.clientY, e.target);
  });
  sectorSpan.addEventListener('mouseout', () => {
    sectorTooltip.hideTooltip();
  });

  timeSectorDiv.appendChild(sectorSpan);
  return timeSectorDiv;
}

/**
 * 渲染股票名称区域（含版型图标、封单额、点击事件）
 * @param {Object} stock - 股票数据
 * @param {string} gpName - 股票名称（去空格）
 * @returns {HTMLElement} 股票名称区域DOM
 */
function renderStockNameArea(stock, gpName) {
  const nameDiv = document.createElement('div');
  nameDiv.className = 'stock-name';
  nameDiv.style.fontSize = '16px';
  nameDiv.style.fontWeight = '500';
  nameDiv.style.marginBottom = '2px';

  // 版型图标
  const typeIcon = renderTypeIcon(stock.limitup_type);
  nameDiv.appendChild(typeIcon);

  // 股票名称（带点击事件）
  const stockName = safeStr(stock.gp_name, '未知股票');
  const limitupRange = parseFloat(stock.limitup_range) || 0;
  const stockNameColor = limitupRange >= 19 ? '#9333ea' : '#333333';

  const stockNameSpan = document.createElement('span');
  stockNameSpan.className = 'stock-name-text';
  stockNameSpan.style.color = stockNameColor;
  stockNameSpan.textContent = stockName;
  nameDiv.appendChild(stockNameSpan);

  // 封单额+封成比
  const orderAmount = stock.limitup_order_amount
    ? (parseFloat(stock.limitup_order_amount) / 100000000).toFixed(2)
    : '';
  const sealRatio = stock.limitup_seal_ratio
    ? parseFloat(stock.limitup_seal_ratio).toFixed(2)
    : '';
  const valueText = orderAmount ? `(${orderAmount}亿｜${sealRatio}%)` : '';
  nameDiv.innerHTML += `<span style="font-size: 11px; color: red;">${valueText}</span>`;

  // 点击事件：与股票单元格的点击事件保持一致，在新窗口中打开
  nameDiv.addEventListener('click', async (e) => {
    e.stopPropagation();
    const gpNo = stock.gp_no;
    if (!gpNo) return;
    window.open(`/public/stock_detail.html?gp_no=${gpNo}`, '_blank');
  });

  return nameDiv;
}

/**
 * 渲染版型图标
 * @param {string} limitupType - 板型（如"换手板"）
 * @returns {HTMLElement} 版型图标DOM
 */
function renderTypeIcon(limitupType) {
  const typeIcon = document.createElement('span');
  typeIcon.style.cssText = TABLE_STYLES.typeIcon;

  if (limitupType && trimStr(limitupType)) {
    const firstChar = trimStr(limitupType).charAt(0);
    const typeColor = TYPE_COLOR_MAP[firstChar] || TYPE_COLOR_MAP.default;
    typeIcon.style.border = `1px solid ${typeColor}`;
    typeIcon.style.color = typeColor;
    typeIcon.textContent = firstChar;
  } else {
    typeIcon.style.display = 'none';
  }

  return typeIcon;
}

/**
 * 渲染涨停原因区域（带悬浮提示）
 * @param {Object} stock - 股票数据
 * @returns {HTMLElement} 涨停原因区域DOM
 */
function renderReasonArea(stock) {
  const reasonDiv = document.createElement('div');
  reasonDiv.className = 'reason';
  reasonDiv.style.cssText = `
    font-size: 11px;
    color: #666;
    white-space: normal;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  `;
  reasonDiv.textContent = safeStr(stock.limitup_reason, '暂无原因');

  reasonDiv.addEventListener('mouseover', (e) => {
    sectorTooltip.showReasonDetailTooltip(stock.limitup_reason_detail, e.clientX, e.clientY, e.target);
  });
  reasonDiv.addEventListener('mouseout', () => {
    sectorTooltip.hideTooltip();
  });

  return reasonDiv;
}

/**
 * 渲染底部信息栏（换手、价格、炸板次数等）
 * @param {Object} stock - 股票数据
 * @returns {HTMLElement} 底部信息栏DOM
 */
function renderBottomInfoArea(stock) {
  const bottomDiv = document.createElement('div');
  bottomDiv.style.cssText = `
    display: flex;
    gap: 1px;
    font-size: 10px;
    width: 100%;
    background-color: inherit;
    margin-top: 1px;
  `;

  // 底部信息项配置（保持不变）
  const bottomItems = [
    {
      width: '25%',
      textAlign: 'left',
      content: () => {
        if (stock.day_limitup && stock.day_limitup !== '首板涨停') {
          return `<span style="color: blue; border-radius: 2px;">${stock.day_limitup}</span>`;
        }
        return '';
      }
    },
    {
      width: '22%',
      textAlign: 'left',
      content: () => {
        const turnoverText = stock.turnover_rate ? `换:${stock.turnover_rate}` : '换:-';
        return `<span style="color: red;">${turnoverText}</span>`;
      }
    },
    {
      width: '38%',
      textAlign: 'left',
      content: () => {
        const totalValue = stock.value ? Math.round(parseFloat(stock.value) / 100000000) : '';
        const totalValueText = totalValue ? `${totalValue}亿` : '-亿';
        const currPriceText = safeStr(stock.curr_price, '-');
        return `<span style="color: green;">${currPriceText} / ${totalValueText}</span>`;
      }
    },
    {
      width: '15%',
      textAlign: 'left',
      content: () => {
        const breakoutText = stock.limitup_open_times ? `炸:${stock.limitup_open_times}` : '炸:-';
        if(stock.limitup_open_times > 0){
          return `<span style="color: orange;">${breakoutText}</span>`;
        }
        return '';
      }
    }
  ];

  // 渲染每个信息项（保持不变）
  bottomItems.forEach(item => {
    const itemWrapper = document.createElement('div');
    itemWrapper.style.width = item.width;
    itemWrapper.style.textAlign = item.textAlign;
    itemWrapper.style.whiteSpace = 'nowrap';
    itemWrapper.style.overflow = 'hidden';
    itemWrapper.style.textOverflow = 'ellipsis';
    itemWrapper.innerHTML = item.content();
    bottomDiv.appendChild(itemWrapper);
  });

  // 添加点击事件：显示股票详情弹窗
  bottomDiv.addEventListener('click', async (e) => {
    e.stopPropagation();
    const gpName = stock.gp_name;
    if (!gpName) return;
    const data = await fetchStockDetails(gpName);
    stockDetailPopup.showPopup(data, e.clientX, e.clientY);
  });

  return bottomDiv;
}