// 接口路径配置
export const API_PATHS = {
  validDates: '/api/zhangting/dates',
  sectors: '/api/zhangting/sectors',
  sectorCount: '/api/zhangting/sector/count',
  stocksBySector: '/api/zhangting/sector/stocks',
  singleDateData: '/api/zhangting/info/list',
  stockDetail: '/api/zhangting/stock/detail',
  stockInfo: '/api/zhangting/stock/info',
  boardInfo: '/api/zhangting/board/info',
  boardKline: '/api/zhangting/board/kline',
  boardStock: '/api/zhangting/board/stock',
  stockComment: '/api/zhangting/stock/comment',
  stockTfp: '/api/zhangting/stock/suspension',
  klineData:'/api/zhangting/stock/kline',
  timeSharingData:'/api/zhangting/stock/time/sharing',
  stockCollectStatus:'/api/zhangting/stock/collect',
  collectToggle:'/api/zhangting/stock/collect/toggle'
};

// 业务配置
export const BUSINESS_CONFIG = {
  batchSize: 50, // 下载时分块大小
  requestTimeout: 5000, // 接口请求超时时间（ms）
  stockGroupSize: 3, // 每行列数（股票分组大小）
  defaultSectorColor: '#999999', // 其他概念默认颜色
  noDataText: '暂无数据' // 无数据提示文本
};