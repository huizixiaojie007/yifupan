import AppState from '../state/appState.js';
import { POPUP_STYLES } from '../constants/styleConstants.js';
import { initKlineChart } from '../renderer/tableRenderer.js';
import { fetchStockKlineData } from '../api/stockApi.js';

class ShowKlineButton {
  constructor() {
    console.log('ShowKlineButton 实例创建');
    this.button = null;
    this.isClicking = false;
    this.pendingRequests = new Map(); // key: gpName, value: Promise
    this.maxConcurrentRequests = 5; // 最大并发请求数
    this.cacheExpiryTime = 3600000; // 缓存过期时间，1小时
    this.init();
  }

  init() {
    console.log('ShowKlineButton init');
    this.button = document.getElementById('kline-toggle-btn');

    if (!this.button) {
      console.log('ShowKlineButton 动态创建按钮');
      this.button = document.createElement('button');
      this.button.id = 'kline-toggle-btn';
      this.button.style.cssText = POPUP_STYLES?.downloadButton || `
        padding: 8px 16px;
        background: #409eff;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        margin-right: 10px;
        font-size: 14px;
      `;
      this.button.textContent = '显示K线';

      const downloadBtn = document.getElementById('download-img-btn');
      if (downloadBtn && downloadBtn.parentNode) {
        downloadBtn.parentNode.insertBefore(this.button, downloadBtn);
      } else {
        document.body.appendChild(this.button);
      }
    }

    this._bindClickEvent();
  }

  // 并发控制器，限制同时进行的请求数量
  async _withConcurrentControl(promises, maxConcurrency) {
    const results = [];
    const executing = new Set();
    const queue = [...promises];

    while (queue.length > 0 || executing.size > 0) {
      // 当有空闲位置且队列中有任务时，执行任务
      while (executing.size < maxConcurrency && queue.length > 0) {
        const promiseCreator = queue.shift();
        const promise = promiseCreator();
        results.push(promise);
        executing.add(promise);
        
        promise.finally(() => {
          executing.delete(promise);
        });
      }

      // 等待一个任务完成
      if (executing.size > 0) {
        await Promise.race(executing);
      }
    }

    return Promise.all(results);
  }

  // 检查缓存是否过期
  _isCacheValid(gpName) {
    const cacheInfo = AppState.getKlineCacheInfo(gpName);
    if (!cacheInfo || !cacheInfo.timestamp) {
      return false;
    }
    return Date.now() - cacheInfo.timestamp < this.cacheExpiryTime;
  }

  // 加载单个股票的K线数据
  async _loadKlineDataForCell(cell) {
    const klineArea = cell.querySelector('.kline-area');
    const klineChartDom = klineArea?.querySelector('div[id^="kline-chart-"]');
    const loadingTip = klineArea?.querySelector('.kline-loading');
    if (!klineArea || !klineChartDom || !loadingTip) return;

    // 显示K线容器+加载提示
    klineArea.style.display = 'block';
    klineChartDom.offsetHeight; // 强制重绘（确保宽高正确）
    loadingTip.style.display = 'flex';
    loadingTip.textContent = '加载中...';

    // 获取股票核心信息
    const gpName = klineArea.dataset.gpName;
    const gpNo = klineArea.dataset.gpNo;
    if (!gpName || !gpNo) {
      loadingTip.textContent = '数据异常';
      return;
    }

    try {
      // 优先从AppState缓存获取数据（添加缓存过期检查）
      let klineData = AppState.getKlineData(gpName);
      if (klineData && klineData.length && this._isCacheValid(gpName)) {
        console.log(`[${gpName}] 从缓存获取K线数据，无需请求接口`);
      } else {
        // 无缓存：调用接口获取（用pendingRequests防止重复请求）
        if (!this.pendingRequests.has(gpName)) {
          console.log(`[${gpName}] 无缓存或缓存过期，发起接口请求`);
          this.pendingRequests.set(gpName, fetchStockKlineData(gpNo, 50));
        }
        // 等待请求结果
        klineData = await this.pendingRequests.get(gpName);
      }

      // 数据校验：无数据/格式错误处理
      if (!klineData || !klineData.length) {
        loadingTip.textContent = '暂无K线数据';
        // 存入空缓存，避免重复请求无数据的股票
        AppState.setKlineData(gpName, []);
        AppState.setKlineCacheInfo(gpName, { timestamp: Date.now() });
        klineChartDom.dataset.klineData = JSON.stringify([]);
        return;
      }

      // 数据有效：存入缓存（双缓存：AppState+DOM dataset）
      AppState.setKlineData(gpName, klineData);
      AppState.setKlineCacheInfo(gpName, { timestamp: Date.now() });
      klineChartDom.dataset.klineData = JSON.stringify(klineData);

      // 初始化K线图表
      initKlineChart(gpName, klineData, klineChartDom);
      loadingTip.style.display = 'none'; // 隐藏加载提示

    } catch (apiError) {
      // 接口请求失败处理
      console.error(`[${gpName}] K线数据请求失败：`, apiError);
      loadingTip.textContent = '加载失败';
    } finally {
      // 移除pending请求（无论成功/失败）
      this.pendingRequests.delete(gpName);
    }
  }

  // 获取可见区域的股票单元格
  _getVisibleCells(cells) {
    const visibleCells = [];
    const viewportHeight = window.innerHeight;
    const viewportTop = window.scrollY;
    const viewportBottom = viewportTop + viewportHeight;

    cells.forEach(cell => {
      const cellRect = cell.getBoundingClientRect();
      const cellTop = viewportTop + cellRect.top;
      const cellBottom = cellTop + cellRect.height;

      // 检查单元格是否与视口重叠
      if (cellBottom >= viewportTop && cellTop <= viewportBottom) {
        visibleCells.push(cell);
      }
    });

    return visibleCells;
  }

  // 加载所有K线数据，使用并发控制和可见区域优先
  async _loadAllKlineData() {
    // 检查导航栏状态
    let sidebar;
    try {
      // 通过 parent 访问父窗口的导航栏
      sidebar = window.parent.document.getElementById('sidebar');
    } catch (e) {
      console.log('无法访问父窗口，可能是跨域限制:', e);
    }
    
    // 判断导航栏是否收起
    const isSidebarCollapsed = sidebar && sidebar.classList.contains('sidebar-collapsed');
    
    // 根据导航栏状态决定加载哪些容器的K线
    let stockCells = [];
    if (isSidebarCollapsed) {
      // 导航栏收起，加载左右两个容器的K线
      console.log('导航栏收起，加载左右两个容器的K线');
      stockCells = Array.from(document.querySelectorAll('.stock-cell'));
    } else {
      // 导航栏展开，只加载右侧容器的K线
      console.log('导航栏展开，只加载右侧容器的K线');
      const rightContainer = document.getElementById('right-container');
      if (rightContainer) {
        stockCells = Array.from(rightContainer.querySelectorAll('.stock-cell'));
      }
    }
    
    // 优先处理可见区域的股票
    const visibleCells = this._getVisibleCells(stockCells);
    const nonVisibleCells = stockCells.filter(cell => !visibleCells.includes(cell));
    const prioritizedCells = [...visibleCells, ...nonVisibleCells];

    // 创建请求函数数组
    const requestFunctions = prioritizedCells.map(cell => async () => {
      await this._loadKlineDataForCell(cell);
    });

    // 使用并发控制器执行请求
    await this._withConcurrentControl(requestFunctions, this.maxConcurrentRequests);
  }

  _bindClickEvent() {
    console.log('ShowKlineButton 绑定点击事件');

    this.button.addEventListener('mousedown', () => {
      this.button.style.background = '#308eff';
    });

    this.button.addEventListener('mouseup', () => {
      this.button.style.background = this.button.textContent === '隐藏K线' ? '#67c23a' : '#409eff';
    });

    this.button.addEventListener('click', async () => {
      if (this.isClicking) return;
      this.isClicking = true;

      try {
        console.log('click 事件触发');
        const isShow = AppState.toggleKlineShow();

        console.log('K线切换状态：', isShow);

        this.button.textContent = isShow ? '隐藏K线' : '显示K线';
        this.button.style.background = isShow ? '#67c23a' : '#409eff';

        if (isShow) {
          await this._loadAllKlineData();
        } else {
          let sidebar;
          try {
            sidebar = window.parent.document.getElementById('sidebar');
          } catch (e) {
            console.log('无法访问父窗口，可能是跨域限制:', e);
          }
          
          const isSidebarCollapsed = sidebar && sidebar.classList.contains('sidebar-collapsed');
          
          let stockCellsToHide = [];
          if (isSidebarCollapsed) {
            console.log('导航栏收起，隐藏左右两个容器的K线');
            stockCellsToHide = Array.from(document.querySelectorAll('.stock-cell'));
          } else {
            console.log('导航栏展开，只隐藏右侧容器的K线');
            const rightContainer = document.getElementById('right-container');
            if (rightContainer) {
              stockCellsToHide = Array.from(rightContainer.querySelectorAll('.stock-cell'));
            }
          }
          
          stockCellsToHide.forEach(cell => {
            const klineArea = cell.querySelector('.kline-area');
            if (klineArea) klineArea.style.display = 'none';
          });
          AppState.destroyAllKlineCharts();
          console.log('隐藏K线区域并销毁图表');
        }
      } catch (error) {
        console.error('K线切换失败：', error);
        // 异常时恢复按钮状态
        this.button.textContent = AppState.isKlineShow() ? '隐藏K线' : '显示K线';
        this.button.style.background = AppState.isKlineShow() ? '#67c23a' : '#409eff';
      } finally {
        setTimeout(() => {
          this.isClicking = false;
        }, 300);
      }
    });

    this.button.addEventListener('mouseout', () => {
      if (!this.isClicking) {
        this.button.style.background = this.button.textContent === '隐藏K线' ? '#67c23a' : '#409eff';
      }
    });
  }
}

export const showKlineButton = new ShowKlineButton();
// 将实例赋值给window对象，以便其他模块访问
window.showKlineButtonInstance = showKlineButton;