console.log('模块开始加载');

// 导入API函数
import {
    fetchStockCollectionStatus,
    fetchStockDetails,
    fetchStockKlineData,
    getStockInfo
} from './api/stockApi.js';

import AppState from './state/appState.js';
import { formatDateToYmd, formatDateToMd } from './utils/dateUtils.js';
import { getColorBySector, getContrastColor } from './utils/colorUtils.js';
import { trimStr, safeStr } from './utils/stringUtils.js';
import { sectorTooltip } from './components/SectorTooltip.js';
import { stockDetailPopup } from './components/StockDetailPopup.js';

console.log('模块加载完成');
console.log('fetchStockCollectionStatus:', typeof fetchStockCollectionStatus);

// 全局变量
let dynamicSectorColorMap = {};

// Tab切换功能
document.addEventListener('DOMContentLoaded', function() {
    const tabMy = document.getElementById('tab-my');
    const tabConsensus = document.getElementById('tab-consensus');
    const contentMy = document.getElementById('content-my');
    const contentConsensus = document.getElementById('content-consensus');
    
    tabMy.addEventListener('click', function() {
        tabMy.classList.add('tab-active');
        tabConsensus.classList.remove('tab-active');
        contentMy.classList.remove('hidden');
        contentConsensus.classList.add('hidden');
        loadMyFavorites();
    });
    
    tabConsensus.addEventListener('click', function() {
        tabConsensus.classList.add('tab-active');
        tabMy.classList.remove('tab-active');
        contentConsensus.classList.remove('hidden');
        contentMy.classList.add('hidden');
        loadConsensusFavorites();
    });
    
    // 初始加载我的收藏
    loadMyFavorites();
});

// 缓存键
const CACHE_KEY = 'favorites_cache';
const CACHE_EXPIRY = 3600000; // 缓存过期时间：1小时

// 保存数据到缓存
function saveToCache(data, type = 'my') {
    try {
        const cacheKey = `${CACHE_KEY}_${type}`;
        const cacheData = {
            data: data,
            timestamp: Date.now()
        };
        localStorage.setItem(cacheKey, JSON.stringify(cacheData));
        console.log('数据已保存到缓存:', type);
    } catch (error) {
        console.error('保存缓存失败:', error);
    }
}

// 从缓存读取数据
function getFromCache(type = 'my') {
    try {
        const cacheKey = `${CACHE_KEY}_${type}`;
        const cacheStr = localStorage.getItem(cacheKey);
        if (!cacheStr) return null;
        
        const cacheData = JSON.parse(cacheStr);
        const now = Date.now();
        
        // 检查缓存是否过期
        if (now - cacheData.timestamp > CACHE_EXPIRY) {
            console.log('缓存已过期:', type);
            localStorage.removeItem(cacheKey);
            return null;
        }
        
        console.log('从缓存读取数据:', type);
        return cacheData.data;
    } catch (error) {
        console.error('读取缓存失败:', error);
        return null;
    }
}

// 获取当前激活的timeline-container
function getActiveTimelineContainer() {
    // 检查哪个tab是激活的
    const tabMy = document.getElementById('tab-my');
    const tabConsensus = document.getElementById('tab-consensus');
    
    if (tabMy.classList.contains('tab-active')) {
        // 我的tab激活
        return document.querySelector('#content-my #timeline-container');
    } else if (tabConsensus.classList.contains('tab-active')) {
        // 共识tab激活
        return document.querySelector('#content-consensus #timeline-container');
    }
    // 默认返回第一个
    return document.getElementById('timeline-container');
}

// 渲染时间轴
function renderTimeline(stocksByDate) {
    const timelineContainer = getActiveTimelineContainer();
    console.log('使用的timeline-container:', timelineContainer);
    if (!timelineContainer) {
        console.error('找不到活跃的timeline-container');
        return;
    }
    
    timelineContainer.innerHTML = '';
    
    // 按日期倒序排列
    const sortedDates = Object.keys(stocksByDate).sort((a, b) => new Date(b) - new Date(a));
    console.log('排序后的日期:', sortedDates);
    
    // 默认展开最近5个日期
    for (let i = 0; i < sortedDates.length; i++) {
        const date = sortedDates[i];
        const stocks = stocksByDate[date];
        const isExpanded = i < 5; // 最近5个日期默认展开
        const timelineItem = createTimelineItem(date, stocks, isExpanded);
        timelineContainer.appendChild(timelineItem);
        
        // 如果是展开状态，在添加到DOM后加载数据
        if (isExpanded) {
            const dateObj = new Date(date);
            const dateStr = formatDateToYmd(dateObj);
            loadStockDetails(date, stocks, dateStr);
        }
    }
}

// 加载共识收藏
async function loadConsensusFavorites() {
    const timelineContainer = getActiveTimelineContainer();
    console.log('共识收藏使用的timeline-container:', timelineContainer);
    if (!timelineContainer) {
        console.error('找不到活跃的timeline-container');
        return;
    }
    timelineContainer.innerHTML = `
        <div class="text-center py-12 text-gray-500">
            <i class="fa fa-spinner fa-spin text-4xl mb-4"></i>
            <p>加载中...</p>
        </div>
    `;
    
    try {
        // 尝试从缓存读取数据
        const cachedData = getFromCache('consensus');
        if (cachedData) {
            console.log('使用缓存数据');
            renderTimeline(cachedData);
            return;
        }
        
        // 使用专门的共识接口
        console.log('接口URL:', '/api/zhangting/stock/collect/consensus');
        
        try {
            
            const response = await fetch('/api/zhangting/stock/collect/consensus', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            console.log('接口响应状态:', response.status);
            console.log('接口响应状态文本:', response.statusText);
            
            if (!response.ok) {
                throw new Error(`接口返回错误: ${response.status}`);
            }
            
            const collectionData = await response.json();
            console.log('收藏数据:', collectionData);
            
            if (!collectionData || !Array.isArray(collectionData)) {
                timelineContainer.innerHTML = `
                    <div class="text-center py-12 text-gray-500">
                        <i class="fa fa-folder-open text-4xl mb-4"></i>
                        <p>暂无收藏股票</p>
                    </div>
                `;
                return;
            }
            
            if (collectionData.length === 0) {
                timelineContainer.innerHTML = `
                    <div class="text-center py-12 text-gray-500">
                        <i class="fa fa-folder-open text-4xl mb-4"></i>
                        <p>暂无收藏股票</p>
                    </div>
                `;
                return;
            }
            
            // 按日期分组，只保留基本信息，不请求详细数据
            const stocksByDate = {};
            collectionData.forEach(stockRecord => {
                const date = stockRecord.date;
                if (!stocksByDate[date]) {
                    stocksByDate[date] = [];
                }
                stocksByDate[date].push({
                    gp_name: stockRecord.gp_name,
                    date: stockRecord.date,
                    collection_time: stockRecord.create_time || new Date().toLocaleTimeString('zh-CN')
                });
            });
            
            console.log('按日期分组:', stocksByDate);
            
            // 保存到缓存
            saveToCache(stocksByDate, 'consensus');
            
            // 渲染时间轴
            renderTimeline(stocksByDate);
        } catch (apiError) {
            console.error('接口调用失败:', apiError);
            timelineContainer.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fa fa-exclamation-circle text-4xl mb-4"></i>
                    <p>接口调用失败</p>
                    <p class="text-xs text-gray-400 mt-2">${apiError.message}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载收藏失败:', error);
        timelineContainer.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <i class="fa fa-exclamation-circle text-4xl mb-4"></i>
                <p>加载失败，请重试</p>
                <p class="text-xs text-gray-400 mt-2">${error.message}</p>
            </div>
        `;
    }
}

// 加载我的收藏
async function loadMyFavorites() {
    const timelineContainer = getActiveTimelineContainer();
    console.log('我的收藏使用的timeline-container:', timelineContainer);
    if (!timelineContainer) {
        console.error('找不到活跃的timeline-container');
        return;
    }
    timelineContainer.innerHTML = `
        <div class="text-center py-12 text-gray-500">
            <i class="fa fa-spinner fa-spin text-4xl mb-4"></i>
            <p>加载中...</p>
        </div>
    `;
    
    try {
        // 尝试从缓存读取数据
        const cachedData = getFromCache();
        if (cachedData) {
            console.log('使用缓存数据');
            renderTimeline(cachedData);
            return;
        }
        
        // 暂时使用固定用户"测试呀"来测试接口
        const user = "测试呀";
        console.log('使用固定用户:', user);
        console.log('接口URL:', '/api/zhangting/stock/collect?user=' + encodeURIComponent(user));
        
        try {
            
            const response = await fetch('/api/zhangting/stock/collect?user=' + encodeURIComponent(user), {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            console.log('接口响应状态:', response.status);
            console.log('接口响应状态文本:', response.statusText);
            
            if (!response.ok) {
                throw new Error(`接口返回错误: ${response.status}`);
            }
            
            const collectionData = await response.json();
            console.log('收藏数据:', collectionData);
            
            if (!collectionData || !Array.isArray(collectionData)) {
                timelineContainer.innerHTML = `
                    <div class="text-center py-12 text-gray-500">
                        <i class="fa fa-folder-open text-4xl mb-4"></i>
                        <p>暂无收藏股票</p>
                    </div>
                `;
                return;
            }
            
            if (collectionData.length === 0) {
                timelineContainer.innerHTML = `
                    <div class="text-center py-12 text-gray-500">
                        <i class="fa fa-folder-open text-4xl mb-4"></i>
                        <p>暂无收藏股票</p>
                    </div>
                `;
                return;
            }
            
            // 按日期分组，只保留基本信息，不请求详细数据
            const stocksByDate = {};
            collectionData.forEach(stockRecord => {
                const date = stockRecord.date;
                if (!stocksByDate[date]) {
                    stocksByDate[date] = [];
                }
                stocksByDate[date].push({
                    gp_name: stockRecord.gp_name,
                    date: stockRecord.date,
                    collection_time: stockRecord.create_time || new Date().toLocaleTimeString('zh-CN')
                });
            });
            
            console.log('按日期分组:', stocksByDate);
            
            // 保存到缓存
            saveToCache(stocksByDate);
            
            // 渲染时间轴
            renderTimeline(stocksByDate);
        } catch (apiError) {
            console.error('接口调用失败:', apiError);
            timelineContainer.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <i class="fa fa-exclamation-circle text-4xl mb-4"></i>
                    <p>接口调用失败</p>
                    <p class="text-xs text-gray-400 mt-2">${apiError.message}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载收藏失败:', error);
        timelineContainer.innerHTML = `
            <div class="text-center py-12 text-gray-500">
                <i class="fa fa-exclamation-circle text-4xl mb-4"></i>
                <p>加载失败，请重试</p>
                <p class="text-xs text-gray-400 mt-2">${error.message}</p>
            </div>
        `;
    }
}