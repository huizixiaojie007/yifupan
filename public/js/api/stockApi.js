import { API_PATHS, BUSINESS_CONFIG } from '../constants/configConstants.js';
import { formatDateToYmd } from '../utils/dateUtils.js';
import AppState from '../state/appState.js';
import { getColorBySector } from '../utils/colorUtils.js';

/**
 * 调用后端接口获取所有有数据的日期（降序排列）
 * @returns {Promise<Date[]>} 日期对象列表
 */
export async function getAllValidDates() {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = API_PATHS.validDates;
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();

    if (!result || !Array.isArray(result)) {
      console.error('获取有效日期失败：返回格式错误');
      return [];
    }

    // 确保日期格式为YYYY-MM-DD，并进行排序（降序）
    const dateList = result
      .filter(dateStr => /^\d{4}-\d{2}-\d{2}$/.test(dateStr))
      .sort((a, b) => new Date(b) - new Date(a));
    
    AppState.setValidDates(dateList);
    return dateList;
  } catch (error) {
    console.error('获取有效日期接口请求失败：', error);
    return [];
  }
}

/**
 * 从接口获取单个日期的数据
 * @param {Date|string} date - 日期对象或YYYY-MM-DD字符串
 * @returns {Promise<Array|null>} 处理后的股票数据，null表示无数据
 */
export async function fetchSingleDateData(date) {
  const dateStr = typeof date === 'string' ? date : formatDateToYmd(date);

  return new Promise((resolve, reject) => {
    // 超时处理
    const timeoutTimer = setTimeout(() => {
      reject(new Error(`获取 ${dateStr} 数据超时（${BUSINESS_CONFIG.requestTimeout}ms）`));
    }, BUSINESS_CONFIG.requestTimeout);

    // 构建请求URL，使用相对路径
    const apiUrl = `${API_PATHS.singleDateData}?date=${encodeURIComponent(dateStr)}`;

    fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    }).then(response => {
      clearTimeout(timeoutTimer);
      if (!response.ok) {
        console.warn(`获取 ${dateStr} 数据失败：HTTP状态${response.status}`);
        resolve(null);
        return;
      }
      return response.json();
    }).then(rawData => {
      if (!rawData || rawData.length === 0) {
        resolve(null);
        return;
      }
      console.log('fetchSingleDateData rawData', rawData);

      // 处理板块原因映射（确保板块名称不丢失）
      const currentSectorReasonMap = {};
      rawData.forEach(stock => {
        const sector = stock.sector || '未知板块'; // 强制赋值默认值
        const sectorReason = stock.sector_reason || '';
        if (sectorReason.trim() && !currentSectorReasonMap[sector]) {
          currentSectorReasonMap[sector] = sectorReason.trim();
        }
      });
      AppState.setSectorReasonMap(currentSectorReasonMap);

      // 处理股票数据（确保板块字段被保留）
      const boards = {};
      const sectorsSet = new Set();
      rawData.forEach(stock => {
        const limitup_days = stock.limitup_days || '';
        const sector = stock.sector || '未知板块'; // 强制赋值默认值
        const gp_name = stock.gp_name || '';
        if (!limitup_days || !gp_name) return;

        sectorsSet.add(sector); // 确保板块被添加到集合
        if (!boards[limitup_days]) boards[limitup_days] = [];
        boards[limitup_days].push({
          ...stock,
          sector: sector, // 显式保留板块字段（关键）
          value: stock.value || 0
        });
      });

      // 生成板块颜色映射（确保每个板块都有颜色）
      const dynamicSectorColorMap = AppState.getDynamicSectorColorMap();
      Array.from(sectorsSet).forEach(sector => {
        if (!dynamicSectorColorMap[sector]) {
          dynamicSectorColorMap[sector] = sector === '其他概念'
            ? BUSINESS_CONFIG.defaultSectorColor
            : getColorBySector(sector);
        }
      });
      AppState.setDynamicSectorColorMap(dynamicSectorColorMap);

      // 按板数排序（修正排序逻辑）
      const processedData = Object.keys(boards).map(board => ({
        limitup_days: board,
        stocks: boards[board]
      })).sort((a, b) => {
        // 修正后的getBoardNumber函数
        const getBoardNumber = (boardStr) => {
          // 第一步：优先处理"首"相关特殊字符，返回1
          if (/首/.test(boardStr)) return 1;
          // 第二步：提取所有数字，组成完整数值（解决10、11等多位数问题）
          const numStr = boardStr.replace(/\D/g, '');
          if (numStr) return parseInt(numStr, 10);
          // 第三步：无数字返回0
          return 0;
        };
        return getBoardNumber(b.limitup_days) - getBoardNumber(a.limitup_days);
      });

      resolve(processedData);
    }).catch(error => {
      clearTimeout(timeoutTimer);
      console.error(`获取 ${dateStr} 数据失败:`, error);
      resolve(null);
    });
  });
}

/**
 * 调用接口获取股票详情
 * @param {string} gpName - 股票名称
 * @returns {Promise<Array|null>} 股票详情数据
 */
export async function fetchStockDetails(gpName) {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = `${API_PATHS.stockDetail}?gp_name=${encodeURIComponent(gpName)}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`股票详情接口返回异常: ${response.status}`);
    }

    const data = await response.json();
    console.log(`股票${gpName}详情接口返回：`, data);
    return data;
  } catch (error) {
    console.error(`获取${gpName}详情失败:`, error);
    return null;
  }
}

/**
 * 从数据库获取股票基本信息（避免爬虫风控）
 * @param {string} gp_no - 股票代码（支持带后缀如 600000.SH 或纯数字 600000）
 * @returns {Promise<Object|null>} 股票详情数据
 */
export async function getStockInfo(gp_no) {
  try {
    // 使用已有的 /api/zhangting/stock/info 接口（已改为从数据库获取）
    const apiUrl = `${API_PATHS.stockInfo}?gp_no=${encodeURIComponent(gp_no)}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`股票信息接口返回异常: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`获取${gp_no}详情失败:`, error);
    return null;
  }
}

//获取概念板块列表
export async function getBoardInfo(fs = 'm:90+t:3+f:!50') {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = `${API_PATHS.boardInfo}?fs=${encodeURIComponent(fs)}`;
    console.log('API请求URL:', apiUrl);

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`股票信息接口返回异常: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`获取概念详情失败:`, error);
    return null;
  }
}

//获取指定概念板块的k线
export async function getBoardKline(secid) {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = `${API_PATHS.boardKline}?secid=${encodeURIComponent(secid)}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`股票信息接口返回异常: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`获取概念详情失败:`, error);
    return null;
  }
}

//获取指定概念板块的股票列表
export async function getBoardStock(block_code) {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = `${API_PATHS.boardStock}?block_code=${encodeURIComponent(block_code)}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`板块股票信息接口返回异常: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`板块${block_code}详情失败:`, error);
    return null;
  }
}
//日内分时
export async function fetchStockTimeSharingData(gp_no, date){
    try {
        console.log('分时图API请求参数:::', gp_no, date);
        console.log('日期类型:::', typeof date);
        
        // 参数校验
        if (!gp_no || !date) {
            console.error('分时图API请求参数缺失：', { gp_no, date });
            return [];
        }
        
        // 构建完整的API URL，使用相对路径
        const apiUrl = `${API_PATHS.timeSharingData}?gp_no=${encodeURIComponent(gp_no)}&date=${encodeURIComponent(date)}`;
        console.log('分时图API请求URL:::', apiUrl);

        const response = await fetch(apiUrl, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const statusText = response.statusText || '未知错误';
            throw new Error(`分时图数据请求失败: ${response.status} ${statusText}`);
        }
        
        const rawData = await response.json();
        console.log('分时图原始数据:::', rawData);
        
        // 检查原始数据格式
        if (!Array.isArray(rawData)) {
            console.error('分时图API返回数据格式错误，不是数组：', rawData);
            return [];
        }
        
        if (rawData.length === 0) {
            console.warn('分时图API返回空数据');
            return [];
        }

        // 检查数据结构
        if (rawData.length === 0) {
            console.warn('分时图API返回空数据');
        }
        
        return rawData;
    } catch (error) {
        console.error('分时图数据请求异常：', error);
        return []; // 失败返回空数组，显示无数据提示
  }
}
/**
 * 获取股票K线数据（假设接口接收股票名称，返回近30天K线）
 * @param {string} gpName - 股票名称
 * @returns {Promise<Array>} K线数据（格式：[[时间, 开盘, 收盘, 最高, 最低], ...]）
 */
export async function fetchStockKlineData(gp_no, days) {
  try {
    // 参数校验
    if (!gp_no) {
      console.error('K线数据请求参数缺失：gp_no');
      return [];
    }

    // 构建请求URL，使用相对路径
    const apiUrl = `${API_PATHS.klineData}?gp_no=${encodeURIComponent(gp_no)}&days=${encodeURIComponent(days || 100)}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      console.error('K线数据请求失败：', response.status);
      return [];
    }

    let rawData;
    try {
      rawData = await response.json();
    } catch (jsonError) {
      console.error('K线数据解析失败：', jsonError);
      return [];
    }

    console.log('K线原始数据：', rawData);

    // 适配ECharts K线格式：转换为 [[时间戳, 开盘, 收盘, 最高, 最低], ...]
    if (!rawData || !Array.isArray(rawData)) {
      console.error('K线数据格式错误：', rawData);
      return [];
    }
    
    const formatData = [];
    for (let i = 0; i < rawData.length; i++) {
      const item = rawData[i];
      if (item && typeof item === 'object') {
        formatData.push([
          new Date(item.date || new Date()).getTime(), // 时间戳（ECharts要求）
          parseFloat(item.open || 0), // 开盘价
          parseFloat(item.close || 0), // 收盘价
          parseFloat(item.high || 0), // 最高价
          parseFloat(item.low || 0), // 最低价
          parseInt(item.volume || 0) // 成交量
        ]);
      }
    }

    return formatData;
  } catch (error) {
    console.error('K线数据请求异常：', error);
    return []; // 失败返回空数组，显示无数据提示
  }
}

//获取股票评分
export async function getStockComment(gp_no) {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = `${API_PATHS.stockComment}?gp_no=${encodeURIComponent(gp_no)}`;

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();
    console.log('getStockComment API返回原始数据:', result);
    
    // 验证result是否为数组
    if (Array.isArray(result)) {
      // 如果是数组，直接返回
      console.log('getStockComment API返回数据:', result);
      return result;
    } else {
      // 如果不是数组，记录错误并返回空数组
      console.error('getStockComment API返回数据格式错误，预期是数组:', result);
      return [];
    }
  } catch (error) {
    console.error('获取股票综合指标接口请求失败：', error);
    return [];
  }
}
/**
 * 查询股票收藏状态（接收 user 和 date 参数，不再依赖 AppState）
 * @param {string} user - 操作用户标识（用户名/ID）
 * @param {string} date - 日期（YYYY-MM-DD，可选）
 * @returns {Array} 收藏的股票列表
 */
export async function fetchStockCollectionStatus(user, date) {
  try {
    // 构建请求URL，使用相对路径
    let apiUrl = API_PATHS.stockCollectStatus;
    const params = new URLSearchParams();
    
    if (user) {
      params.append('user', user);
    }
    if (date) {
      params.append('date', date);
    }
    
    const queryString = params.toString();
    if (queryString) {
      apiUrl += `?${queryString}`;
    }

    const response = await fetch(apiUrl, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });
    const data = await response.json();
    
    // 将对象数组转换为股票名称数组
    if (Array.isArray(data)) {
      return data.map(item => item.gp_name || '');
    }
    return [];
  } catch (error) {
    console.error(`查询收藏状态失败：`, error);
    return [];
  }
}

/**
 * 切换股票收藏状态（接收 user 和 date 参数，不再依赖 AppState）
 * @param {string} gpNo - 股票代码
 * @param {string} gpName - 股票名称
 * @param {boolean} isCollect - true=收藏，false=取消收藏
 * @param {string} user - 操作用户标识（用户名/ID）
 * @param {string} date - 日期（YYYY-MM-DD）
 * @returns {Object} { success: boolean, message?: string }
 */
export async function toggleStockCollection(gpName, collect, user, date) {
  try {
    // 参数校验
    if (!gpName || !user || !date) {
      console.warn('切换收藏状态：缺少必要参数（gpName/user/date）');
      return { success: false, message: '参数不全' };
    }
    const requestBody = { gp_name: gpName, user, date, collect };
    // 构建请求URL，使用相对路径
    const apiUrl = API_PATHS.collectToggle;
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    return await response.json();
  } catch (error) {
    console.error(`[${gpName}] 切换收藏状态失败：`, error);
    return { success: false, message: '网络异常，请重试' };
  }
}

//获取所有板块概念信息
export async function getAllSectors() {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = API_PATHS.sectors;
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();
    // 转换为Date对象并返回
    return result;
  } catch (error) {
    console.error('获取板块概念接口请求失败：', error);
    return [];
  }
}

//获取每日概念对应股票的的统计结果
export async function getSectorCount(startDate = '', endDate = '') {
  try {
    // 构建完整的API URL，使用相对路径
    let apiUrl = API_PATHS.sectorCount;
    
    // 添加日期范围参数
    const params = new URLSearchParams();
    if (startDate) {
      params.append('startDate', startDate);
    }
    if (endDate) {
      params.append('endDate', endDate);
    }
    
    const queryString = params.toString();
    if (queryString) {
      apiUrl += `?${queryString}`;
    }
    
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    const result = await response.json();
    // 转换为Date对象并返回
    return result;
  } catch (error) {
    console.error('获取板块概念接口请求失败：', error);
    return [];
  }
}




//获取连续涨停天数大于等于2的股票列表
export async function getConsecutiveLimitupStocks() {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = '/api/zhangting/stocks/consecutive-limitup';

    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
      throw new Error(`获取连续涨停股票失败: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('获取连续涨停股票失败:', error);
    return [];
  }
}

//获取板块概念中的所有股票数据
export async function getStocksBySector(sector) {
  try {
    // 构建完整的API URL，使用相对路径
    const apiUrl = `${API_PATHS.stocksBySector}?sector=${encodeURIComponent(sector)}`;

    const response = await fetch(apiUrl, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });

    const result = await response.json();
//    console.log("板块概念中的股票信息返回：", result);
    return result;
  } catch (error) {
    console.error('获取板块概念接口请求失败：', error);
    return [];
  }
}

