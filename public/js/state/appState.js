/**
 * 全局状态管理器（单例模式）
 * 统一管理全局状态，提供get/set方法，避免直接操作状态
 */
const AppState = (function() {
  // 私有状态
  const state = {
    dynamicSectorColorMap: {}, // 动态板块颜色映射
    sectorReasonMap: {}, // 板块→原因映射
    validDates: [], // 有数据的日期列表（降序）
    currentIndex: 0, // 当前选中索引
    isFinding: false, // 查找锁
    isDateChanging: false, // 日期切换标志
    containerSelectedSectors: {}, // 不同容器的选中板块集合，key: containerId, value: Set

    isKlineShow: false, // K线区域显示状态（默认隐藏）
    klineDataCache: {}, // K线数据缓存（key：股票名称，value：K线数据）
    klineCacheInfo: {}, // K线缓存信息（key：股票名称，value：{ timestamp: 缓存时间 }）
    klineChartInstances: {}, // ECharts图表实例缓存（避免重复初始化）

  };

  return {
    // 获取完整状态（调试用）
    getState() {
      return { ...state };
    },

    // 动态板块颜色映射
    getDynamicSectorColorMap() {
      return { ...state.dynamicSectorColorMap };
    },
    setDynamicSectorColorMap(map) {
      state.dynamicSectorColorMap = { ...state.dynamicSectorColorMap, ...map };
    },

    // 板块→原因映射
    getSectorReasonMap() {
      return { ...state.sectorReasonMap };
    },
    setSectorReasonMap(map) {
      state.sectorReasonMap = { ...state.sectorReasonMap, ...map };
    },

    // 有数据的日期列表
    getValidDates() {
      return [...state.validDates];
    },
    setValidDates(dates) {
      state.validDates = [...dates];
    },

    // 当前选中索引
    getCurrentIndex() {
      return state.currentIndex;
    },
    setCurrentIndex(index) {
      state.currentIndex = index;
    },

    // 查找锁
    getIsFinding() {
      return state.isFinding;
    },
    setIsFinding(isFinding) {
      state.isFinding = isFinding;
    },
    
    // 日期切换标志
    getIsDateChanging() {
      return state.isDateChanging;
    },
    setIsDateChanging(isDateChanging) {
      state.isDateChanging = isDateChanging;
    },

    getIsKlineShow() {
      return state.isKlineShow;
    },
      // 补充：直接设置K线显示状态（而非切换）
    setIsKlineShow(show) {
      state.isKlineShow = Boolean(show);
      return state.isKlineShow;
    },
    // 切换K线显示状态
    toggleKlineShow() {
      state.isKlineShow = !state.isKlineShow; // 修复：访问私有state，而非this
      return state.isKlineShow;
    },

  getKlineData(gpName) {
    // 先判断缓存容器是否存在，再判断是否有对应股票的缓存
    if (!state.klineDataCache || typeof state.klineDataCache !== 'object') {
      state.klineDataCache = {}; // 兜底：如果缓存容器异常，重新初始化
      return null;
    }
    // 返回缓存数据（无则返回 null，而非 undefined）
    return state.klineDataCache[gpName] || null;
  },

  // 3. 修复 setKlineData：确保缓存容器存在
  setKlineData(gpName, data) {
    if (!state.klineDataCache || typeof state.klineDataCache !== 'object') {
      state.klineDataCache = {};
    }
    state.klineDataCache[gpName] = data || []; // 存入数据（空数据兜底）
  },

    // 缓存ECharts实例
    setKlineChartInstance(gpName, instance) {
      state.klineChartInstances[gpName] = instance; // 修复：访问state.klineChartInstances
    },

    // 获取ECharts实例
    getKlineChartInstance(gpName) {
      return state.klineChartInstances[gpName] || null; // 修复：访问state.klineChartInstances，添加默认值
    },

    // 销毁所有K线图表实例（收起时释放资源）
    destroyAllKlineCharts() {
      // 修复：遍历state.klineChartInstances，添加判断避免实例不存在时报错
      Object.values(state.klineChartInstances).forEach(instance => {
        if (instance && typeof instance.dispose === 'function') {
          instance.dispose();
        }
      });
      state.klineChartInstances = {}; // 重置缓存
    },

    // K线缓存信息管理
    getKlineCacheInfo(gpName) {
      return state.klineCacheInfo[gpName] || { timestamp: 0 };
    },
    setKlineCacheInfo(gpName, info) {
      state.klineCacheInfo[gpName] = info;
    },

    // 选中的板块集合（按容器ID管理）
  getSelectedSectors(containerId) {
    if (!containerId) {
      return new Set();
    }
    return new Set(state.containerSelectedSectors[containerId] || []);
  },
  setSelectedSectors(containerId, sectors) {
    if (!containerId) {
      return;
    }
    state.containerSelectedSectors[containerId] = new Set(sectors);
  },
  
  // 检查容器是否已经初始化
  isContainerInitialized(containerId) {
    if (!containerId) {
      return false;
    }
    return containerId in state.containerSelectedSectors;
  }

  };
})();

export default AppState;