import { getAllSectors, getStocksBySector, getSectorCount, fetchStockKlineData, fetchStockTimeSharingData, getStockInfo } from '../api/stockApi.js';
import AppState from '../state/appState.js';
import { getContrastColor, getColorBySector } from '../utils/colorUtils.js';
import { sectorTooltip } from '../components/SectorTooltip.js';

// 全局状态管理
const state = {
    currentStock: null,
    sectors: [],
    sectorRelayData: {},
    klineChart: null,
    sectorCollapseState: {} // 记录各板块1板的展开/收起状态（key: 板块名, value: 是否收起）
};

// 页面初始化
document.addEventListener('DOMContentLoaded', async () => {
    await loadSectors();
    bindEvents();
    // 延迟初始化K线图，避免阻塞页面加载
    setTimeout(async () => await initKlineChart(), 500);
    // 绘制板块直方图
    drawSectorHistogram();
});

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
    script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
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
 * 工具函数：创建DOM元素（简化重复操作）
 * @param {string} tag - 标签名
 * @param {object} options - 配置项（class、attributes、text、children）
 * @returns {HTMLElement} 创建的DOM元素
 */
function createElement(tag, options = {}) {
    const el = document.createElement(tag);
    if (options.class) el.className = options.class;
    if (options.attributes) {
        Object.entries(options.attributes).forEach(([key, value]) => el.setAttribute(key, value));
    }
    if (options.text) el.textContent = options.text;
    // 新增：支持动态style
    if (options.style) {
        if (typeof options.style === 'string') {
            el.style.cssText = options.style;
        } else {
            Object.entries(options.style).forEach(([key, value]) => el.style[key] = value);
        }
    }
    if (options.children && Array.isArray(options.children)) {
        options.children.forEach(child => child instanceof HTMLElement && el.appendChild(child));
    }
    return el;
}

/**
 * 加载所有板块数据并渲染抽屉
 */
async function loadSectors() {
    const sectorsListEl = document.getElementById('sectorsList');
    try {
        showLoading();
        const sectors = await getAllSectors();
        state.sectors = sectors;

        sectorsListEl.innerHTML = '';
        sectors.forEach((sector, index) => {
            // 初始化该板块1板收起状态（默认：true=收起）
            if (state.sectorCollapseState[sector.sector] === undefined) {
                state.sectorCollapseState[sector.sector] = true;
            }

            const sectorColor = getColorBySector(sector.sector) || '#CCCCCC';
            // 计算文字对比色（保证背景色上文字可读）
            const textColor = getContrastColor(sectorColor);
            const drawerEl = createElement('div', {
                class: 'border border-gray-200 rounded-lg overflow-hidden mb-4'
            });
            if (index === 0) drawerEl.classList.add('drawer-expanded');

            const headerEl = createElement('div', {
                class: 'drawer-header bg-gray-50 px-4 py-3 flex items-center justify-between cursor-pointer',
                attributes: { 'data-sector-index': index }
            });

            const headerLeft = createElement('div', { class: 'flex items-center' });
            // ========== 关键修改2：动态设置板块名称的背景色/文字色 ==========
            const sectorText = createElement('span', {
                class: 'font-medium sector-name px-2 py-0.5 rounded text-xs', // 优化样式：内边距+圆角
                text: `${sector.sector || '未知板块'}`,
                // 动态设置样式（替代全局CSS的硬编码）
                style: `
                    background-color: ${sectorColor};
                    color: ${textColor};
                    font-size: 12px;
                    white-space: nowrap;
                `
            });
            // =================================================================

            const sectorReasonText = createElement('span', {
                class: 'text-gray-500 text-xs ml-2', // 调整字号+间距
                text: `${sector.sector_reason || ''}`
            });
            const stockCountBadge = createElement('span', {
                class: 'ml-2 bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full',
                text: `共${sector.total_stock_count}只`
            });
            const latestDateCount = createElement('span', {
                class: 'ml-2 bg-red-100 text-red-500 text-xs px-2 py-0.5 rounded-full',
                text: `${sector.latest_date.split('T')[0]}：${sector.latest_date_stock_count}只`
            });


            headerLeft.appendChild(sectorText);
            headerLeft.appendChild(sectorReasonText);
            headerLeft.appendChild(stockCountBadge);
            headerLeft.appendChild(latestDateCount);

            const arrowEl = createElement('i', { class: 'fa fa-chevron-down drawer-arrow text-gray-500' });
            headerEl.appendChild(headerLeft);
            headerEl.appendChild(arrowEl);

            const contentEl = createElement('div', {
                class: 'drawer-content px-4 py-3',
                attributes: { style: 'max-height: 80vh; overflow-y: auto; overflow-x: visible;' }
            });

            const timelineContainer = createElement('div', {
                class: 'timeline-container overflow-x-auto mb-4',
                attributes: { style: 'width: 100%; max-width: 100%;' }
            });
            const timelineInitText = createElement('div', {
                class: 'text-center text-gray-500 py-3 text-xs',
                text: index === 0 ? '点击右侧箭头，展开股票详细内容...' : '点击展开加载数据'
            });
            timelineContainer.appendChild(timelineInitText);

            const stocksBatchContainer = createElement('div', {
                class: 'stocks-batch-container space-y-6',
                attributes: { id: `stocksBatchContainer_${index}` }
            });

            contentEl.appendChild(timelineContainer);
            contentEl.appendChild(stocksBatchContainer);
            drawerEl.appendChild(headerEl);
            drawerEl.appendChild(contentEl);
            sectorsListEl.appendChild(drawerEl);
        });

    } catch (err) {
        const errorEl = createElement('div', { class: 'text-center text-red-500 py-6' });
        const errorIcon = createElement('i', { class: 'fa fa-exclamation-circle mr-2' });
        const errorText = createElement('span', { text: `加载失败：${err.message}` });
        errorEl.appendChild(errorIcon);
        errorEl.appendChild(errorText);
        sectorsListEl.appendChild(errorEl);
        console.error('加载板块失败：', err);
    } finally {
        hideLoading();
        // 数据加载完成后重新绘制直方图
        drawSectorHistogram();
    }
}

/**
 * 加载单个板块的封板接力数据并渲染时间轴
 */
async function loadSectorRelayData(sectorName, container, sectorIndex) {
    try {
        console.log(`加载板块${sectorName}数据，sectorIndex=${sectorIndex}`);
        if (state.sectorRelayData[sectorName]) {
            const stocks = state.sectorRelayData[sectorName];
            renderTableTimeline(stocks, container, sectorIndex, sectorName);
            await loadStockDataToDrawer(stocks, sectorIndex);
            return;
        }

        const stocks = await getStocksBySector(sectorName);
        console.log('stocks:::',stocks)
        state.sectorRelayData[sectorName] = stocks;

        renderTableTimeline(stocks, container, sectorIndex, sectorName);
        await loadStockDataToDrawer(stocks, sectorIndex);

    } catch (err) {
        container.innerHTML = '';
        const errorEl = createElement('div', { class: 'text-center text-red-500 py-3 text-xs' });
        const errorIcon = createElement('i', { class: 'fa fa-exclamation-circle mr-2' });
        const errorText = createElement('span', { text: `加载失败：${err.message}` });
        errorEl.appendChild(errorIcon);
        errorEl.appendChild(errorText);
        container.appendChild(errorEl);
        console.error(`加载板块${sectorName}封板数据失败：`, err);
    }
}

/**
 * 渲染表格形式的时间轴（保持原有顺序：日期升序、板数降序）
 * @param {array} stocks - 股票数据
 * @param {HTMLElement} container - 容器元素
 * @param {number} sectorIndex - 板块索引
 * @param {string} sectorName - 板块名
 */
function renderTableTimeline(stocks, container, sectorIndex, sectorName) {
    const validStocks = Array.isArray(stocks) ? stocks.filter(stock =>
        stock.date && stock.limitup_days && stock.gp_name &&
        !isNaN(stock.limitup_days) && stock.limitup_days >= 1
    ) : [];

    container.innerHTML = '';
    if (validStocks.length === 0) {
        const emptyEl = createElement('div', {
            class: 'text-center text-gray-500 py-3 text-xs',
            text: '该板块暂无有效封板数据'
        });
        container.appendChild(emptyEl);
        return;
    }

    // 数据处理：保持原有顺序（日期升序、板数降序）
    const formatDateOnly = (dateStr) => {
        const date = new Date(dateStr);
        return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
    };
    // 日期升序（左到右：最早→最新）- 保持原样
    const allDates = [...new Set(validStocks.map(stock => formatDateOnly(stock.date)))]
        .sort((a, b) => new Date(a) - new Date(b));
    // 板数降序（上到下：多板→少板）- 保持原样
    const allSealNums = [...new Set(validStocks.map(stock => parseInt(stock.limitup_days)))]
        .filter(num => num >= 1)
        .sort((a, b) => b - a);

    // 关键逻辑：1板隐藏规则
    const hasOneBoard = allSealNums.includes(1);
    const hasMultiBoards = allSealNums.length > 1;
    state.sectorCollapseState[sectorName] = hasMultiBoards && hasOneBoard; // 多板时默认收起1板

    // 构建股票映射
    const stockMap = {};
    validStocks.forEach(stock => {
        const dateKey = formatDateOnly(stock.date);
        const numKey = parseInt(stock.limitup_days);
        const key = `${dateKey}_${numKey}`;
        if (!stockMap[key]) stockMap[key] = [];
        stockMap[key].push(stock);
    });

    // 【新增】预先构建：股票代码 → 已排序的出现日期列表（升序）
    // 用于快速统计「当前列日期之前」的出现次数，避免O(n²)扫描
    const codeSortedDates = new Map();
    validStocks.forEach(s => {
        if (!s.gp_no) return;
        const d = formatDateOnly(s.date);
        if (!codeSortedDates.has(s.gp_no)) codeSortedDates.set(s.gp_no, []);
        codeSortedDates.get(s.gp_no).push(d);
    });
    codeSortedDates.forEach(arr => arr.sort());
    // 统计函数：code在targetDate之前的出现次数（按涨停记录计数：多日/多板都算，同板同日只算1次）
    function countBefore(code, targetDate) {
        const arr = codeSortedDates.get(code) || [];
        let n = 0;
        for (const d of arr) if (d < targetDate) n++;
        return n;
    }

    // 【新增】预先统计每天（跨所有板数）的股票总只数
    const dateStockCount = {};
    allDates.forEach(d => dateStockCount[d] = 0);
    Object.entries(stockMap).forEach(([key, list]) => {
        const [d] = key.split('_');
        if (dateStockCount[d] !== undefined) dateStockCount[d] += (list?.length || 0);
    });

    // 1. 创建表格容器（包含表格和右侧按钮）
    const tableWrapper = createElement('div', {
        class: 'relative w-full',
        attributes: { style: 'display: flex; flex-direction: column; width: 100%;' } // 纵向布局，确保宽度100%
    });

    // 2. 创建表格
    const table = createElement('table', {
        class: 'border-collapse w-full bg-white', // 使用w-full而不是min-w-full，避免表格过宽
        attributes: { 'data-sector-name': sectorName }
    });

    // 3. 表头（日期升序：左旧右新）- 两行：日期 + 当天股票总数badge
    const thead = createElement('thead');
    const headerTr = createElement('tr', { class: 'bg-gray-50' });
    allDates.forEach(date => {
        const dateTh = createElement('th', {
            class: 'border border-gray-200 px-2 py-1 text-center text-gray-700 font-medium w-[60px] align-middle',
            attributes: { title: `${date}：共 ${dateStockCount[date] || 0} 只股票涨停` }
        });
        // 第一行：日期 08/13
        const dateLine = createElement('div', {
            class: 'text-[10px] leading-tight',
            text: date.replace(/-/g, '/')
        });
        // 第二行：共N只 badge（颜色：当日数量>15红/10~14橙/<10蓝）
        const totalN = dateStockCount[date] || 0;
        let badgeBg = '#eff6ff', badgeFg = '#1d4ed8', badgeBd = '#93c5fd';
        if (totalN >= 15)      { badgeBg = '#fef2f2'; badgeFg = '#b91c1c'; badgeBd = '#fca5a5'; } // 红：>15只
        else if (totalN >= 10) { badgeBg = '#fff7ed'; badgeFg = '#c2410c'; badgeBd = '#fdba74'; } // 橙：10-14
        const badgeLine = createElement('div', {
            class: 'mt-0.5 inline-block rounded px-1 py-[1px] text-[9px] font-bold',
            style: `background-color:${badgeBg}; color:${badgeFg}; border:1px solid ${badgeBd};`,
            text: `${totalN}只`
        });
        dateTh.appendChild(dateLine);
        dateTh.appendChild(badgeLine);
        headerTr.appendChild(dateTh);
    });
    const boardHeaderTh = createElement('th', {
        class: 'border border-gray-200 px-2 py-1.5 text-center text-gray-700 font-medium text-[10px] w-[50px]',
        text: '板数'
    });
    headerTr.appendChild(boardHeaderTh);
    thead.appendChild(headerTr);
    table.appendChild(thead);

    // 4. 表体（板数降序：多板在上）- 保持原样
    const tbody = createElement('tbody');
    allSealNums.forEach(sealNum => {
        const is1Board = sealNum === 1;
        const tr = createElement('tr', {
            class: `border-b border-gray-200 ${is1Board ? 'board-1-row' : ''}`,
            attributes: {
                'data-seal-num': sealNum,
                'id': is1Board ? `board1Row_${sectorName}` : '', // 1板行专属ID
                'data-hidden': is1Board && state.sectorCollapseState[sectorName] ? 'true' : 'false'
            }
        });

        // 日期单元格（左旧右新）- 保持原样
        allDates.forEach(date => {
            const key = `${date}_${sealNum}`;
            const stocksInCell = stockMap[key] || [];
            const td = createElement('td', {
                class: 'border border-gray-200 px-1.5 py-1 min-h-[36px] vertical-align-top',
                attributes: { title: stocksInCell.length > 0 ? stocksInCell.map(s => s.gp_name).join('、') : '无' }
            });

            if (stocksInCell.length === 0) {
                const emptyDiv = createElement('div', {
                    class: 'w-full h-full flex items-center justify-center text-gray-300 text-[9px]',
                    text: '无'
                });
                td.appendChild(emptyDiv);
            } else {
                const stocksContainer = createElement('div', { class: 'space-y-0.5 text-center' });
                // 单元格内股票保持原有顺序 - 还原原样（去掉之前的sort）
                stocksInCell.forEach(stock => {
                    const stockItem = createElement('div', {
                        class: 'stock-item-hover cursor-pointer px-1 py-0.5 rounded-md border border-transparent transition-colors text-[9px] bg-white shadow-sm flex items-center gap-0.5 whitespace-nowrap overflow-hidden',
                        attributes: {
                            'data-stock-code': stock.gp_no,
                            'data-stock-name': stock.gp_name,
                            'data-sector-index': sectorIndex,
                            'data-target-id': `stockCard_${sectorIndex}_${stock.gp_no}`
                        }
                    });
                    // 【新增】统计当前列(date)之前，这只股票在本板块里出现过多少次
                    const beforeCount = countBefore(stock.gp_no, date);
                    // 名称文本（4字截断）
                    const nameText = stock.gp_name.length > 4 ? stock.gp_name.substring(0, 4) + '…' : stock.gp_name;
                    const nameSpan = createElement('span', {
                        class: 'shrink-0 truncate',
                        text: nameText
                    });
                    stockItem.appendChild(nameSpan);
                    // 出现次数 badge：N=0不显示；1-2蓝色；3-4红色；≥5紫色（inline style保证颜色生效，避免Tailwind JIT漏扫）
                    if (beforeCount > 0) {
                        let bg, fg, bd, prefix;
                        if (beforeCount >= 5) {
                            bg = '#faf5ff'; fg = '#6b21a8'; bd = '#d8b4fe'; prefix = '★'; // 紫：深紫文字+浅紫底+紫色边框，★前缀区分
                        } else if (beforeCount >= 3) {
                            bg = '#fef2f2'; fg = '#b91c1c'; bd = '#fca5a5'; prefix = '×'; // 红
                        } else {
                            bg = '#eff6ff'; fg = '#1d4ed8'; bd = '#93c5fd'; prefix = '×'; // 蓝
                        }
                        const badgeSpan = createElement('span', {
                            class: 'shrink-0 px-1 rounded text-[8px] font-bold leading-none py-[2px] inline-flex items-center',
                            style: `background-color:${bg}; color:${fg}; border:1px solid ${bd};`,
                            attributes: { title: `此前列表中出现过 ${beforeCount} 次` },
                            text: `${prefix}${beforeCount}`
                        });
                        stockItem.appendChild(badgeSpan);
                    }
                    stocksContainer.appendChild(stockItem);
                });
                td.appendChild(stocksContainer);
            }
            tr.appendChild(td);
        });

        // 板数列单元格
        const boardTd = createElement('td', {
            class: 'border border-gray-200 px-2 py-1 text-center text-gray-700 font-medium text-[10px] bg-gray-50',
            text: `${sealNum}板`
        });
        tr.appendChild(boardTd);
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    
    // 清空容器内容
    container.innerHTML = '';
    
    // 设置容器样式为flex布局，纵向排列
    container.style.width = '100%';
    container.style.maxWidth = '100%';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.position = 'relative';
    
    // 创建一个单独的滚动容器用于表格
    const scrollContainer = createElement('div', {
        class: 'w-full',
        attributes: {
            style: `
                display: block !important;
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow-x: auto;
                overflow-y: visible;
            `
        }
    });
    
    // 确保表格占满宽度
    table.style.minWidth = '100%';
    table.style.tableLayout = 'auto';
    
    // 将表格添加到滚动容器
    scrollContainer.appendChild(table);
    
    // 将滚动容器添加到主容器
    container.appendChild(scrollContainer);
    
    // 5. 展开/收起按钮（居右显示）
    if (hasOneBoard && hasMultiBoards) {
        // 创建按钮容器，使其独立于滚动区域
        const btnContainer = createElement('div', {
            class: 'w-full',
            attributes: {
                style: `
                    display: flex !important;
                    justify-content: flex-end !important;
                    width: 100% !important;
                    margin: 0.5rem 0 0 0 !important;
                    padding: 0 !important;
                    clear: both !important;
                    position: relative !important;
                    z-index: 10 !important;
                `
            }
        });
        
        // 创建按钮
        const toggleBtn = createElement('button', {
            class: 'px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-xs flex items-center gap-1 transition-colors',
            attributes: {
                'data-sector-name': sectorName, 
                'id': `toggleBtn_${sectorName}`,
                'style': `
                    float: right !important;
                    display: inline-flex !important;
                    margin: 0 !important;
                    position: relative !important;
                    z-index: 10 !important;
                `
            }
        });
        
        const icon = createElement('i', {
            class: state.sectorCollapseState[sectorName] ? 'fa fa-chevron-down' : 'fa fa-chevron-up'
        });
        const btnText = createElement('span', {
            text: state.sectorCollapseState[sectorName] ? '展开1板' : '收起1板'
        });
        toggleBtn.appendChild(icon);
        toggleBtn.appendChild(btnText);

        // 点击事件：精准切换1板显示/隐藏
        toggleBtn.addEventListener('click', () => {
            const sectorName = toggleBtn.dataset.sectorName;
            const isCurrentlyCollapsed = state.sectorCollapseState[sectorName];
            const newState = !isCurrentlyCollapsed;

            // 更新全局状态
            state.sectorCollapseState[sectorName] = newState;

            // 精准找到1板行
            const board1Row = document.getElementById(`board1Row_${sectorName}`);
            if (board1Row) {
                board1Row.setAttribute('data-hidden', newState ? 'true' : 'false');
            }

            // 更新按钮状态
            icon.className = newState ? 'fa fa-chevron-down' : 'fa fa-chevron-up';
            btnText.textContent = newState ? '展开1板' : '收起1板';
        });
        
        btnContainer.appendChild(toggleBtn);
        container.appendChild(btnContainer);
    }

    // 滚动到最右侧（显示最新日期）- 还原原样
    setTimeout(() => {
        scrollContainer.scrollLeft = scrollContainer.scrollWidth;
    }, 10);
}

/**
 * 绑定页面交互事件
 */
function bindEvents() {
    const sectorsListEl = document.getElementById('sectorsList');

    // 1. 抽屉展开/收起事件
    sectorsListEl.addEventListener('click', async (e) => {
        const headerEl = e.target.closest('.drawer-header');
        if (!headerEl) return;

        const drawerEl = headerEl.parentElement;
        const sectorIndex = parseInt(headerEl.dataset.sectorIndex);
        const sector = state.sectors[sectorIndex];
        const timelineContainer = drawerEl.querySelector('.timeline-container');

        const isExpanded = drawerEl.classList.toggle('drawer-expanded');
        const arrowEl = headerEl.querySelector('.drawer-arrow');
        arrowEl.style.transform = isExpanded ? 'rotate(180deg)' : 'rotate(0)';

        if (isExpanded && !state.sectorRelayData[sector.sector]) {
            timelineContainer.innerHTML = '';
            const loadingEl = createElement('div', {
                class: 'text-center text-gray-500 py-3 text-xs',
                text: '加载封板数据中...'
            });
            timelineContainer.appendChild(loadingEl);
            await loadSectorRelayData(sector.sector, timelineContainer, sectorIndex, sector.sector);
        }
    });
    


    // 2. 股票项点击事件（核心修改：卡片存在则置顶，不存在则生成并置顶）
    sectorsListEl.addEventListener('click', async (e) => { // 改为异步函数
        const stockItem = e.target.closest('[data-stock-code]');
        if (!stockItem) return;

        // 1. 获取核心参数
        const stockCode = stockItem.dataset.stockCode;
        const sectorIndex = parseInt(stockItem.dataset.sectorIndex);
        const sector = state.sectors[sectorIndex];
        const sectorName = sector.sector;
        const targetCardId = stockItem.dataset.targetId;
        const stocksBatchContainer = document.getElementById(`stocksBatchContainer_${sectorIndex}`);

        // 容器不存在则终止
        if (!stocksBatchContainer) {
            console.error(`股票卡片容器未找到：stocksBatchContainer_${sectorIndex}`);
            return;
        }

        // 2. 清除所有激活状态
        document.querySelectorAll('[data-stock-code]').forEach(item => {
            item.classList.remove('stock-item-active');
        });
        document.querySelectorAll('.stock-card').forEach(card => {
            card.classList.remove('stock-card-active');
        });
        stockItem.classList.add('stock-item-active');

        // 3. 检查目标卡片是否存在
        const targetCard = document.getElementById(targetCardId);
        if (targetCard) {
            // 3.1 卡片存在：移到容器最前并激活
            if (targetCard.parentElement === stocksBatchContainer) {
                stocksBatchContainer.removeChild(targetCard);
                stocksBatchContainer.insertBefore(targetCard, stocksBatchContainer.firstChild);
            }
            targetCard.classList.add('stock-card-active');
            state.currentStock = { code: stockCode, name: stockItem.dataset.stockName };
            return;
        }

        // 3.2 卡片不存在：生成卡片并置顶
        try {
            // 显示加载提示
            const loadingEl = createElement('div', {
                class: 'text-center text-gray-500 py-3 text-xs',
                text: '加载股票详情中...'
            });
            stocksBatchContainer.insertBefore(loadingEl, stocksBatchContainer.firstChild);

            // 检查板块数据是否加载，未加载则先加载
            let sectorStocks = state.sectorRelayData[sectorName];
            if (!sectorStocks) {
                // 找到该板块的时间轴容器，加载板块数据
                const timelineContainer = document.querySelector(`[data-sector-index="${sectorIndex}"]`)
                    .closest('.drawer-header')
                    .nextElementSibling
                    .querySelector('.timeline-container');
                await loadSectorRelayData(sectorName, timelineContainer, sectorIndex);
                sectorStocks = state.sectorRelayData[sectorName];
            }

            // 找不到板块数据则抛出错误
            if (!sectorStocks || sectorStocks.length === 0) {
                throw new Error('板块股票数据加载失败');
            }

            // 找到对应股票数据
            const targetStock = sectorStocks.find(stock => stock.gp_no === stockCode);
            if (!targetStock) {
                throw new Error(`未找到股票【${stockCode}】的相关数据`);
            }

            // 二次检查卡片（防止并发点击重复生成）
            if (document.getElementById(targetCardId)) {
                loadingEl.remove();
                const newCard = document.getElementById(targetCardId);
                newCard.classList.add('stock-card-active');
                stocksBatchContainer.removeChild(newCard);
                stocksBatchContainer.insertBefore(newCard, stocksBatchContainer.firstChild);
                state.currentStock = { code: stockCode, name: stockItem.dataset.stockName };
                return;
            }

            // 生成卡片并插入到容器最前
            await renderSingleStockCard(targetStock, sectorIndex, stocksBatchContainer, stocksBatchContainer.firstChild);

            // 移除加载提示，激活新卡片
            loadingEl.remove();
            const newCard = document.getElementById(targetCardId);
            if (newCard) {
                newCard.classList.add('stock-card-active');
            }

            // 更新全局选中状态
            state.currentStock = { code: stockCode, name: stockItem.dataset.stockName };

        } catch (err) {
            console.error('生成股票卡片失败：', err);
            // 移除加载提示，显示错误信息
            const loadingEl = stocksBatchContainer.querySelector('.text-center.text-gray-500');
            if (loadingEl) loadingEl.remove();

            const errorEl = createElement('div', {
                class: 'text-center text-red-500 py-3 text-xs',
                text: `加载失败：${err.message}`
            });
            stocksBatchContainer.insertBefore(errorEl, stocksBatchContainer.firstChild);

            // 3秒后自动清除错误提示
            setTimeout(() => errorEl.remove(), 3000);
        }
    });

    // 4. 全部收起按钮事件
    document.getElementById('collapseAllBtn').addEventListener('click', () => {
        // 收起所有抽屉
        document.querySelectorAll('.drawer-expanded').forEach(drawer => {
            drawer.classList.remove('drawer-expanded');
            const arrowEl = drawer.querySelector('.drawer-arrow');
            arrowEl.style.transform = 'rotate(0)';
        });

        // 强制收起所有1板
        document.querySelectorAll('[id^="board1Row_"]').forEach(board1Row => {
            const sectorName = board1Row.id.replace('board1Row_', '');
            state.sectorCollapseState[sectorName] = true;
            board1Row.setAttribute('data-hidden', 'true');

            // 更新对应按钮
            const toggleBtn = document.getElementById(`toggleBtn_${sectorName}`);
            if (toggleBtn) {
                const icon = toggleBtn.querySelector('i');
                const btnText = toggleBtn.querySelector('span');
                icon.className = 'fa fa-chevron-down';
                btnText.textContent = '展开1板';
            }
        });
    });
}

/**
 * 批量加载并渲染板块内所有股票的详情和K线（核心修改：股票卡片排序逻辑+默认显示前5+显示所有按钮）
 */
async function loadStockDataToDrawer(stocks, sectorIndex) {
    const targetContainerId = `stocksBatchContainer_${sectorIndex}`;
    const batchContainer = document.getElementById(targetContainerId);

    if (!batchContainer) {
        console.error(`板块索引${sectorIndex}的批量渲染容器未找到！目标ID：${targetContainerId}`);
        return;
    }

    const validStocks = stocks.filter(stock => stock.gp_no && stock.gp_name);
    // 进阶去重：若有重复股票，保留板数最高→日期最新的那条
    const stockMap = new Map();

    validStocks.forEach(stock => {
        const gpNo = stock.gp_no;
        const currentBoard = parseInt(stock.limitup_days) || 0;
        const currentDate = new Date(stock.date || '').getTime();

        if (!stockMap.has(gpNo)) {
            // 第一次出现，直接存入
            stockMap.set(gpNo, stock);
        } else {
            // 已存在，比较板数和日期，保留更优的
            const existingStock = stockMap.get(gpNo);
            const existingBoard = parseInt(existingStock.limitup_days) || 0;
            const existingDate = new Date(existingStock.date || '').getTime();

            if (currentBoard > existingBoard || (currentBoard === existingBoard && currentDate > existingDate)) {
                stockMap.set(gpNo, stock);
//                console.log(`更新重复股票：${stock.gp_name}(${stock.gp_no})，保留板数更高/日期更新的记录`);
            }
        }
    });

    const uniqueStocks = Array.from(stockMap.values()); // 转为数组
    // 核心修改：排序逻辑（先按日期倒序 → 同一日期按板数降序）
    const sortedStocks = uniqueStocks.sort((a, b) => {
        // 1. 先按涨停日期倒序：最新的在前
        const dateA = new Date(a.date || '');
        const dateB = new Date(b.date || '');
        const dateCompare = dateB - dateA;

        // 2. 若日期相同，按板数降序：板数高的在前
        if (dateCompare === 0) {
            const boardA = parseInt(a.limitup_days) || 0;
            const boardB = parseInt(b.limitup_days) || 0;
            return boardB - boardA;
        }

        return dateCompare;
    });

    if (sortedStocks.length === 0) {
        batchContainer.innerHTML = '';
        const emptyEl = createElement('div', {
            class: 'text-center text-gray-500 py-6 text-xs',
            text: '该板块暂无有效股票数据'
        });
        batchContainer.appendChild(emptyEl);
        return;
    }

    try {
//        showLoading();
        batchContainer.innerHTML = '';

        // 核心新增：默认显示前5个股票，其余点击按钮后加载
        const DEFAULT_SHOW_COUNT = 5;
        const shownStocks = sortedStocks.slice(0, DEFAULT_SHOW_COUNT);
        const remainingStocks = sortedStocks.slice(DEFAULT_SHOW_COUNT);

        // 渲染默认显示的前5个股票
        for (const stock of shownStocks) {
            await renderSingleStockCard(stock, sectorIndex, batchContainer);
        }

        // 核心新增：有剩余股票时显示"显示所有K线"按钮
        if (remainingStocks.length > 0) {
            const showAllBtn = createElement('button', {
                class: 'w-full mt-4 px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors',
                attributes: { 'data-sector-index': sectorIndex },
                text: '显示所有K线'
            });
            const icon = createElement('i', { class: 'fa fa-angle-down' });
            showAllBtn.appendChild(icon);
            batchContainer.appendChild(showAllBtn);

            // 按钮点击事件：加载剩余股票
            showAllBtn.addEventListener('click', async () => {
                if (showAllBtn.disabled) return;
                // 防止重复点击
                showAllBtn.disabled = true;
                showAllBtn.innerHTML = '<i class="fa fa-spinner fa-spin mr-2"></i> 加载中...';

                try {
                    // 渲染剩余股票（插入到按钮前面）
                    for (const stock of remainingStocks) {
                        await renderSingleStockCard(stock, sectorIndex, batchContainer, showAllBtn);
                    }
                    // 所有股票加载完成后移除按钮
                    showAllBtn.remove();
                } catch (err) {
                    showAllBtn.disabled = false;
                    showAllBtn.innerHTML = '<i class="fa fa-exclamation-circle mr-2"></i> 加载失败，点击重试';
                    console.error('加载剩余股票失败：', err);
                }
            });
        }

    } catch (err) {
        batchContainer.innerHTML = '';
        const errorEl = createElement('div', {
            class: 'text-center text-red-500 py-6 text-xs',
            text: `批量加载股票数据失败：${err.message}`
        });
        batchContainer.appendChild(errorEl);
        console.error('批量加载股票数据异常：', err);
    } finally {
        hideLoading();
    }
}

/**
 * 核心新增：单独渲染单个股票卡片的工具函数（避免代码重复）
 * @param {object} stock - 股票数据
 * @param {number} sectorIndex - 板块索引
 * @param {HTMLElement} parentContainer - 父容器
 * @param {HTMLElement} insertBeforeEl - 插入到某个元素前面（可选）
 */
async function renderSingleStockCard(stock, sectorIndex, parentContainer, insertBeforeEl = null) {
    const stockCode = stock.gp_no;
    const stockName = stock.gp_name;
    const cardId = `stockCard_${sectorIndex}_${stockCode}`;

    // 创建股票卡片（紧凑布局）
    const stockCard = createElement('div', {
        attributes: { id: cardId },
        class: 'stock-card border border-gray-200 rounded-lg p-3 bg-white shadow-sm transition-all flex flex-col gap-3'
    });

    // 第一栏：股票详情（包含股名、代码、分数、涨停原因和详情数据 - 紧凑布局）
    const stockDetailSection = createElement('div', {
        class: 'stock-detail-section border-b border-gray-200 pb-2'
    });

    // ========== 股票信息头部（包含所有详情数据） ==========
    const detailHeader = createElement('div', {
        class: 'flex items-center gap-4 text-xs py-2'
    });

    // 左侧：股票名称 + 代码（垂直排列）
    const nameCodeWrapper = createElement('div', {
        class: 'flex flex-col gap-1 mr-4 flex-shrink-0'
    });
    const stockNameEl = createElement('span', {
        class: 'text-sm font-bold text-gray-800',
        text: `${stockName}`
    });
    const stockCodeEl = createElement('span', {
        class: 'text-[11px] text-gray-500',
        text: `${stockCode}`
    });
    nameCodeWrapper.appendChild(stockNameEl);
    nameCodeWrapper.appendChild(stockCodeEl);
    
    // 中间：分数
    const scoreWrapper = createElement('div', {
        class: 'text-lg font-bold text-red-800 mx-3 flex-shrink-0 mt-0.5',
        text: `${stock.score ? parseFloat(stock.score).toFixed(1) : '--'}`
    });

    // 右侧：涨停原因（留出合适宽度，超出换行）
    const reasonWrapper = createElement('div', {
        class: 'text-[11px] text-blue-600 max-w-[10%] flex-shrink-1',
        style: 'word-break: break-word; line-height: 1.2;'
    });
    const stockReasonText = stock.limitup_reason || '无涨停原因';
    const stockReasonEl = createElement('span', {
        text: stockReasonText
    });
    stockReasonEl.addEventListener('mouseover', (e) => {
        sectorTooltip.showReasonDetailTooltip(stock.limitup_reason_detail, e.clientX, e.clientY, e.target);
    });
    stockReasonEl.addEventListener('mouseout', () => {
        sectorTooltip.hideTooltip();
    });
    reasonWrapper.appendChild(stockReasonEl);

    // 最右侧：详情数据（超出可以换行）
    const detailDataWrapper = createElement('div', {
        class: 'flex flex-wrap items-center gap-1 flex-grow min-w-[250px]'
    });
    const loadingItem = createElement('div', {
        class: 'text-center text-gray-500 py-1 flex items-center justify-center w-full',
        text: '加载详情中...'
    });
    detailDataWrapper.appendChild(loadingItem);

    // 组装头部
    detailHeader.appendChild(nameCodeWrapper);
    detailHeader.appendChild(scoreWrapper);
    detailHeader.appendChild(reasonWrapper);
    detailHeader.appendChild(detailDataWrapper);
    // ===================================

    // 组装详情区域
    stockDetailSection.appendChild(detailHeader);
    // ===================================

    // 第二栏：图表区域（分时图和K线图左右分布）
    const chartSection = createElement('div', {
        class: 'chart-section flex gap-4'
    });

    // 分时图容器
    const timeSharingContainerId = `timeSharingContainer_${sectorIndex}_${stockCode}`;
    const timeSharingWrapper = createElement('div', {
        class: 'time-sharing-wrapper w-[50%] flex flex-col'
    });
    const timeSharingHeader = createElement('div', {
        class: 'flex justify-between items-center mb-2'
    });
    const timeSharingTitle = createElement('h5', {
        class: 'text-sm font-medium text-gray-700',
        text: '日内分时图'
    });
    timeSharingHeader.appendChild(timeSharingTitle);
    
    const timeSharingContainer = createElement('div', {
        attributes: { id: timeSharingContainerId },
        class: 'w-full h-[200px] border border-gray-100 rounded'
    });
    const timeSharingLoading = createElement('div', {
        class: 'w-full h-full flex items-center justify-center text-gray-500 text-xs'
    });
    const timeSharingLoadingIcon = createElement('i', { class: 'fa fa-spinner fa-spin mr-2' });
    const timeSharingLoadingText = createElement('span', { text: '加载中...' });
    timeSharingLoading.appendChild(timeSharingLoadingIcon);
    timeSharingLoading.appendChild(timeSharingLoadingText);
    timeSharingContainer.appendChild(timeSharingLoading);
    
    timeSharingWrapper.appendChild(timeSharingHeader);
    timeSharingWrapper.appendChild(timeSharingContainer);

    // K线图容器
    const klineContainerId = `klineContainer_${sectorIndex}_${stockCode}`;
    const klineWrapper = createElement('div', {
        class: 'kline-wrapper w-[60%] flex flex-col'
    });
    const klineHeader = createElement('div', {
        class: 'flex justify-between items-center mb-2'
    });
    const klineTitle = createElement('h5', {
        class: 'text-sm font-medium text-gray-700',
        text: 'K线图'
    });
    klineHeader.appendChild(klineTitle);
    
    const klineContainer = createElement('div', {
        attributes: { id: klineContainerId },
        class: 'w-full h-[200px] border border-gray-100 rounded'
    });
    const klineLoading = createElement('div', {
        class: 'w-full h-full flex items-center justify-center text-gray-500 text-xs'
    });
    const klineLoadingIcon = createElement('i', { class: 'fa fa-spinner fa-spin mr-2' });
    const klineLoadingText = createElement('span', { text: '加载中...' });
    klineLoading.appendChild(klineLoadingIcon);
    klineLoading.appendChild(klineLoadingText);
    klineContainer.appendChild(klineLoading);
    
    klineWrapper.appendChild(klineHeader);
    klineWrapper.appendChild(klineContainer);

    // 组装图表区域
    chartSection.appendChild(timeSharingWrapper);
    chartSection.appendChild(klineWrapper);
    // ===================================

    // 组装卡片
    stockCard.appendChild(stockDetailSection);
    stockCard.appendChild(chartSection);
    
    // 先将stockCard添加到parentContainer，确保容器元素在DOM中
    if (insertBeforeEl) {
        parentContainer.insertBefore(stockCard, insertBeforeEl);
    } else {
        parentContainer.appendChild(stockCard);
    }

    // 异步加载数据
    try {
        console.log('股票数据:::', stock);
        console.log('股票代码:::', stockCode);
        console.log('股票日期:::', stock.date);
        
        // 根据用户建议：分时图应该使用当前日期，确保与K线图数据一致
        const today = new Date();
        const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
        console.log('分时图使用当前日期:::', dateStr);
        console.log('格式化后的日期:::', dateStr);
        
        // 并行加载K线数据、分时图数据和股票基本信息
    const [klineData, rawTimeSharingData, stockInfo] = await Promise.all([
        fetchStockKlineData(stockCode, 100),
        fetchStockTimeSharingData(stockCode, dateStr),
        getStockInfo(stockCode)
    ]);
    
    // 处理K线数据
    if (Array.isArray(klineData)) {
        // 按日期升序排序，确保数据顺序正确
        klineData.sort((a, b) => a[0] - b[0]);
        AppState.setKlineData(stockName, klineData);
    }
    
    // 转换分时图数据格式：将对象数组转换为二维数组[[时间, 价格, 成交量], ...]
    let timeSharingData = [];
    let timeSharingDate = dateStr; // 默认使用当前日期
    
    if (Array.isArray(rawTimeSharingData) && rawTimeSharingData.length > 0) {
        timeSharingData = rawTimeSharingData.map(item => {
            // 处理不同的数据结构
            if (Array.isArray(item)) {
                // 如果已经是数组格式，直接返回
                return item;
            } else if (typeof item === 'object' && item !== null) {
                // 如果是对象格式，转换为数组
                return [
                    item['时间'] || item['time'] || '',
                    parseFloat(item['收盘'] || item['close'] || 0),
                    parseFloat(item['成交量'] || item['volume'] || 0)
                ];
            }
            return null;
        }).filter(item => item !== null);
        
        // 尝试从分时图数据中获取日期
        if (rawTimeSharingData.length > 0) {
            const firstItem = rawTimeSharingData[0];
            if (typeof firstItem === 'object' && firstItem !== null) {
                const timeStr = firstItem['时间'] || firstItem['time'] || '';
                if (timeStr) {
                    const date = new Date(timeStr);
                    if (!isNaN(date.getTime())) {
                        timeSharingDate = `${date.getMonth() + 1}.${date.getDate()}`;
                    }
                }
            }
        }
    }

        // 尝试从分时图数据中获取日期
        if (rawTimeSharingData.length > 0) {
            const firstItem = rawTimeSharingData[0];
            if (typeof firstItem === 'object' && firstItem !== null) {
                const timeStr = firstItem['时间'] || firstItem['time'] || '';
                if (timeStr) {
                    const date = new Date(timeStr);
                    if (!isNaN(date.getTime())) {
                        timeSharingDate = `${date.getMonth() + 1}.${date.getDate()}`;
                    }
                }
            }
        }
        
        // 更新分时图标题
        if (timeSharingTitle) {
            timeSharingTitle.textContent = `${timeSharingDate}日分时`;
        }
        
        // 获取昨日收盘价用于分时图计算
        let yesterdayClose = 0;
        // 优先使用stockInfo中的昨收价
        if (stockInfo) {
            const prevCloseValue = stockInfo['昨收'] || stockInfo['prev_close'];
            yesterdayClose = parseFloat(prevCloseValue)/100 || 0;
            console.log("prevCloseValue::", prevCloseValue)
        }
        // 如果stockInfo中没有，则从K线数据中获取
        if (yesterdayClose === 0 && Array.isArray(klineData) && klineData.length >= 2) {
            const lastSecondItem = klineData[klineData.length - 2];
            yesterdayClose = parseFloat(lastSecondItem[2]) || 0;
        }
        
        // 更新分时图和K线图
        await Promise.all([
            updateTimeSharingChartToDrawer(timeSharingData, timeSharingContainerId, yesterdayClose),
            updateKlineChartToDrawer(klineData, klineContainerId)
        ]);
        
        // 更新股票详情
        updateStockDetail(detailDataWrapper, stockInfo);
    } catch (err) {
        // 详情加载失败处理
        detailDataWrapper.innerHTML = '';
        const detailError = createElement('div', {
            class: 'text-center text-red-500 py-1 flex items-center justify-center text-xs',
            text: `详情加载失败：${err.message}`
        });
        detailDataWrapper.appendChild(detailError);
        
        // 分时图加载失败处理
        timeSharingContainer.innerHTML = '';
        const timeSharingError = createElement('div', {
            class: 'w-full h-full flex items-center justify-center text-gray-500 text-xs'
        });
        const timeSharingErrorIcon = createElement('i', { class: 'fa fa-exclamation-circle mr-2' });
        const timeSharingErrorText = createElement('span', { text: '分时图加载失败' });
        timeSharingError.appendChild(timeSharingErrorIcon);
        timeSharingError.appendChild(timeSharingErrorText);
        timeSharingContainer.appendChild(timeSharingError);
        
        // K线图加载失败处理
        klineContainer.innerHTML = '';
        const klineError = createElement('div', {
            class: 'w-full h-full flex items-center justify-center text-gray-500 text-xs'
        });
        const klineErrorIcon = createElement('i', { class: 'fa fa-exclamation-circle mr-2' });
        const klineErrorText = createElement('span', { text: 'K线图加载失败' });
        klineError.appendChild(klineErrorIcon);
        klineError.appendChild(klineErrorText);
        klineContainer.appendChild(klineError);
        
        console.error(`加载股票${stockCode}数据失败：`, err);
    }
}

/**
 * 更新单个股票的详情内容（紧凑布局）
 */
function updateStockDetail(detailDataWrapper, stockInfo) {
    detailDataWrapper.innerHTML = '';

    // 提取所需的字段值，支持不同的数据结构
    const getFieldValue = (fields, defaultValue = 0) => {
        for (const field of fields) {
            if (stockInfo[field] !== undefined && stockInfo[field] !== null) {
                return stockInfo[field];
            }
        }
        return defaultValue;
    };

    // 格式化数值，处理精度
    const formatValue = (value, precision = 2) => {
        if (typeof value === 'number') {
            return (value/100).toFixed(precision);
        }
        if (typeof value === 'string') {
            const num = parseFloat(value);
            if (!isNaN(num)) {
                return (num/100).toFixed(precision);
            }
        }
        return value;
    };

    // 格式化市值和成交额，转换为亿（原始值为元）
    const formatMarketCap = (value) => {
        if (typeof value === 'number') {
            // 原始值为元，÷100000000转为亿
            return (value / 100000000).toFixed(2);
        }
        if (typeof value === 'string') {
            const num = parseFloat(value);
            if (!isNaN(num)) {
                return (num / 100000000).toFixed(2);
            }
        }
        return value;
    };

    // 格式化成交量，转换为万手（原始值为手数）
    const formatAmount = (value) => {
        if (typeof value === 'number') {
            // 原始值为手数，÷10000转为万手
            return (value / 10000).toFixed(2);
        }
        if (typeof value === 'string') {
            const num = parseFloat(value);
            if (!isNaN(num)) {
                return (num / 10000).toFixed(2);
            }
        }
        return value;
    };

    const stockCode = getFieldValue(['股票代码', 'gp_no', 'code']);
    const stockName = getFieldValue(['股票名称', 'gp_name', 'name']);
    const latestPrice = formatValue(getFieldValue(['最新价', '现价', 'curr_price', 'close']));
    const changePercent = formatValue(getFieldValue(['涨跌幅(%)', '涨跌幅', 'change_percent']));
    const changeAmount = formatValue(getFieldValue(['涨跌额', 'change_amount']));
    const amplitude = formatValue(getFieldValue(['振幅', 'amplitude']));
    const volumeRatio = formatValue(getFieldValue(['量比', 'volume_ratio']));
    const lowPrice = formatValue(getFieldValue(['最低价', 'low']));
    const highPrice = formatValue(getFieldValue(['最高价', 'high']));
    const openPrice = formatValue(getFieldValue(['今开', 'open']));
    const prevClose = formatValue(getFieldValue(['昨收', 'prev_close']));
    const volume = formatAmount(getFieldValue(['成交量(万手)', '成交量', 'volume']));
    const amount = formatMarketCap(getFieldValue(['成交额(亿元)', '成交额', 'amount']));
    const turnoverRate = formatValue(getFieldValue(['换手率(%)', '换手率', 'turnover_rate']));
    const peTtm = formatValue(getFieldValue(['动态市盈率(TTM)', '市盈率', 'pe_ttm']));
    const pb = formatValue(getFieldValue(['市净率(%)', '市净率', 'pb']));
    const totalMarketCap = formatMarketCap(getFieldValue(['总市值(亿)', '总市值', 'total_market_cap']));
    const floatMarketCap = formatMarketCap(getFieldValue(['流通市值(亿)', '流通市值', 'float_market_cap']));

    // 创建横向排列的布局
    const detailFlex = createElement('div', {
        class: 'flex flex-wrap items-center gap-2 w-full'
    });

    // 所有字段
    const allFields = [
        { label: '现价', value: `${latestPrice}元` },
        { label: '换手率', value: `${turnoverRate}%` },
        { label: '涨跌幅', value: `${changePercent}%` },
        // { label: '涨跌额', value: `${changeAmount}` },
        { label: '振幅', value: `${amplitude}%` },
        { label: '量比', value: `${volumeRatio}` },
        // { label: '最低价', value: `${lowPrice}元` },
        // { label: '最高价', value: `${highPrice}元` },
        // { label: '今开', value: `${openPrice}元` },
        // { label: '昨收', value: `${prevClose}元` },
        { label: '成交量', value: `${volume}万手` },
        { label: '成交额', value: `${amount}亿` },
        { label: '动态市盈率', value: `${peTtm}` },
        { label: '市净率', value: `${pb}` },
        { label: '总市值', value: `${totalMarketCap}亿` },
        { label: '流通市值', value: `${floatMarketCap}亿` }
    ];

    // 添加所有字段
    allFields.forEach((field, index) => {
        const item = createElement('span', { class: 'flex items-center gap-1 whitespace-nowrap text-xs' });
        const label = createElement('span', { class: 'text-gray-500', text: field.label });
        
        // 为换手率和流通市值添加颜色
        let valueClass = 'font-medium';
        let valueStyle = {};
        
        if (field.label === '换手率') {
            const rate = parseFloat(turnoverRate);
            if (!isNaN(rate)) {
                // 由于数据已经除以100，所以阈值也要相应调整
                if (rate > 10) { // 相当于原始值>10%
                    valueStyle.color = '#ef4444'; // 高换手率红色
                } else if (rate > 5) { // 相当于原始值>5%
                    valueStyle.color = '#f97316'; // 中等换手率橙色
                } else {
                    valueStyle.color = '#22c55e'; // 低换手率绿色
                }
            }
        } else if (field.label === '流通市值') {
            const cap = parseFloat(floatMarketCap);
            if (!isNaN(cap)) {
                // 使用格式化后的值进行判断
                if (cap > 1000) {
                    valueStyle.color = '#ef4444'; // 大市值红色
                } else if (cap > 100) {
                    valueStyle.color = '#f97316'; // 中等市值橙色
                } else {
                    valueStyle.color = '#22c55e'; // 小市值绿色
                }
            }
        }
        
        const value = createElement('span', { 
            class: valueClass, 
            text: field.value,
            style: valueStyle
        });
        item.appendChild(label);
        item.appendChild(value);
        detailFlex.appendChild(item);
        
        // 添加分隔线（最后一个不添加）
        if (index < allFields.length - 1) {
            const separator = createElement('span', { class: 'text-gray-300', text: '|' });
            detailFlex.appendChild(separator);
        }
    });

    detailDataWrapper.appendChild(detailFlex);
}

/**
 * 初始化K线图基础配置
 */
async function initKlineChart() {
    try {
        const echarts = await loadECharts();
        state.klineChart = echarts.init(document.createElement('div'));
    } catch (error) {
        console.error('Failed to initialize Kline Chart:', error);
    }
}

/**
 * 计算移动平均线（MA）
 */
function calculateMA(data, period) {
    const result = [];
    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            result.push('-');
        } else {
            let sum = 0;
            for (let j = 0; j < period; j++) {
                sum += parseFloat(data[i - j][2]) || 0;
            }
            result.push((sum / period).toFixed(2));
        }
    }
    return result;
}

/**
 * 更新指定K线容器的图表数据（保持原有顺序：最新在右侧）
 */
async function updateKlineChartToDrawer(klineData, containerId) {
    // 增加重试机制，最多尝试3次
    let container = null;
    for (let i = 0; i < 3; i++) {
        container = document.getElementById(containerId);
        if (container) break;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (!container) {
        console.error(`K线容器${containerId}未找到`);
        return;
    }
    if (window[`klineInstance_${containerId}`]) {
        window[`klineInstance_${containerId}`].dispose();
    }
    try {
        const echarts = await loadECharts();
        const klineChart = echarts.init(container);
        window[`klineInstance_${containerId}`] = klineChart;

    const option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            textStyle: { fontSize: 10 },
            formatter: function (params) {
                let tooltipHtml = `<div>${params[0].axisValue}</div>`;
                params.forEach(item => {
                    if (item.seriesType === 'candlestick') {
                        tooltipHtml += `<div>${item.seriesName}：${item.value[0]} / ${item.value[1]} / ${item.value[2]} / ${item.value[3]}</div>`;
                    } else if (item.seriesType === 'line') {
                        tooltipHtml += `<div>${item.seriesName}：${item.value}</div>`;
                    } else if (item.seriesType === 'bar') {
                        tooltipHtml += `<div>${item.seriesName}：${formatVolume(item.value)}</div>`;
                    }
                });
                return tooltipHtml;
            }
        },
        grid: [
            {
                left: '4%',
                right: '2%',
                top: '8%',
                bottom: '30%',
                containLabel: true
            },
            {
                left: '4%',
                right: '2%',
                top: '72%',
                bottom: '8%',
                containLabel: true
            }
        ],
        xAxis: [
            {
                type: 'category',
                data: [],
                axisLabel: { fontSize: 9, interval: 3 },
                axisLine: { lineStyle: { color: '#111' } },
                gridIndex: 0
            },
            {
                type: 'category',
                data: [],
                axisLabel: { show: false },
                axisLine: { show: false },
                gridIndex: 1
            }
        ],
        yAxis: [
            {
                type: 'value',
                scale: true,
                axisLabel: { fontSize: 9, formatter: '{value}' },
                axisLine: { lineStyle: { color: '#111' } },
                splitLine: { lineStyle: { color: '#f5f5f5' } },
                gridIndex: 0
            },
            {
                type: 'value',
                scale: true,
                axisLabel: { show: true,  formatter: '  '},
                axisLine: { lineStyle: { color: '#111' } },
                splitLine: { show: false },
                gridIndex: 1
            }
        ],
        series: [
            {
                name: 'K线',
                type: 'candlestick',
                data: [],
                itemStyle: {
                    color: '#ef4444',
                    color0: '#22c55e',
                    borderColor: '#ef4444',
                    borderColor0: '#22c55e'
                },
                barWidth: '60%',
                xAxisIndex: 0,
                yAxisIndex: 0
            },
            {
                name: '5日均线',
                type: 'line',
                data: [],
                lineStyle: { color: '#f59e0b', width: 1.5 },
                symbol: 'none',
                smooth: true,
                xAxisIndex: 0,
                yAxisIndex: 0
            },
            {
                name: '10日均线',
                type: 'line',
                data: [],
                lineStyle: { color: '#3b82f6', width: 1.5 },
                symbol: 'none',
                smooth: true,
                xAxisIndex: 0,
                yAxisIndex: 0
            },
            {
                name: '成交量',
                type: 'bar',
                data: [],
                itemStyle: {
                    color: function (params) {
                        const klineData = option.series[0].data[params.dataIndex];
                        if (klineData) {
                            return klineData[0] < klineData[1] ? '#ef4444' : '#22c55e';
                        }
                        return '#9ca3af';
                    }
                },
                barWidth: '60%',
                xAxisIndex: 1,
                yAxisIndex: 1
            }
        ]
    };

    if (!klineData || !Array.isArray(klineData) || klineData.length === 0) {
        klineChart.setOption(option);
        return;
    }

    // 保持原有逻辑：取最近40条，不反转（最新数据在右侧）
    const recentKlineData = klineData.slice(-100);
    const dates = recentKlineData.map(item => item[0] || '').map(date => {
        const d = new Date(date);
        return `${d.getMonth() + 1}/${d.getDate()}`;
    });

    const candlestickData = recentKlineData.map(item => [
        parseFloat(item[1]) || 0,
        parseFloat(item[2]) || 0,
        parseFloat(item[3]) || 0,
        parseFloat(item[4]) || 0
    ]);

    const ma5Data = calculateMA(recentKlineData, 5);
    const ma10Data = calculateMA(recentKlineData, 10);

    const volumeData = recentKlineData.map(item => {
        return parseFloat(item[5]) || 0;
    });

    option.xAxis[0].data = dates;
    option.xAxis[1].data = dates;
    option.series[0].data = candlestickData;
    option.series[1].data = ma5Data;
    option.series[2].data = ma10Data;
    option.series[3].data = volumeData;

    klineChart.setOption(option);

    window.addEventListener('resize', () => {
        klineChart.resize();
    });
    } catch (error) {
        console.error('Failed to update Kline Chart:', error);
    }
}

/**
 * 渲染日内分时图（自动适配涨幅+15分钟刻度+价格一位小数）
 * @param {array} timeSharingData - 分时数据（格式：[[时间, 价格, 成交量], ...]）
 * @param {string} containerId - 容器ID
 * @param {number} yesterdayClose - 昨日收盘价（必填，用于计算涨幅和绘制中轴线）
 */
async function updateTimeSharingChartToDrawer(timeSharingData, containerId, yesterdayClose) {
    // 增加重试机制，最多尝试3次
    let container = null;
    for (let i = 0; i < 3; i++) {
        container = document.getElementById(containerId);
        if (container) break;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (!container) {
        console.error(`分时图容器${containerId}未找到`);
        return;
    }
    
    // 确保容器有明确的高度设置，解决高度为0的问题
    if (container.style.height === '' || container.offsetHeight === 0) {
        console.log('updateTimeSharingChartToDrawer: 容器高度为0，设置默认高度');
        container.style.height = '200px'; // 设置明确的高度
    }
    
    // 检查图表容器尺寸
    const rect = container.getBoundingClientRect();
    console.log('updateTimeSharingChartToDrawer: 容器尺寸 - 宽度:', rect.width, '高度:', rect.height);

    // 销毁原有ECharts实例
    if (window[`klineInstance_${containerId}`]) {
        window[`klineInstance_${containerId}`].dispose();
    }
    
    try {
        const echarts = await loadECharts();
        const timeSharingChart = echarts.init(container);
        window[`klineInstance_${containerId}`] = timeSharingChart;

        // 容错：昨日收盘价未提供时默认取第一个有效价格
        // 注意：如果yesterdayClose为0，仍使用0作为基准（虽然实际情况很少见）
        const validClose = yesterdayClose !== undefined && yesterdayClose !== null ? yesterdayClose : (timeSharingData.length > 0 ? parseFloat(timeSharingData[0][1]) || 0 : 0);

        // 计算涨幅数据（基于昨日收盘价）
        const calculateIncrease = (price) => {
            if (yesterdayClose === 0) return 0;
            return ((price - yesterdayClose) / yesterdayClose * 100); // 先不toFixed，保留原始值用于计算极值
        };

        // ========== 核心1：自动计算涨幅范围（适配10%/20%） ==========
        let increaseRange = 10; // 默认主板±10%
        if (validClose > 0 && timeSharingData.length > 0) {
            // 计算所有数据的涨幅极值
            const allIncreases = timeSharingData.map(item => calculateIncrease(parseFloat(item[1]) || 0));
            const maxInc = Math.max(...allIncreases);
            const minInc = Math.min(...allIncreases);
            // 取绝对值最大的涨幅，判断是否需要扩展到20%（双创板）
            const maxAbsInc = Math.max(Math.abs(maxInc), Math.abs(minInc));
            if (maxAbsInc > 11) {
                increaseRange = 20; // 涨幅超过10%，自动适配±20%
            }
        }

        // ========== 核心2：计算价格范围（昨收±涨幅范围，保证居中） ==========
        let priceMin = 0, priceMax = 0;
        if (validClose > 0) {
            priceMin = validClose * (1 - increaseRange / 100); // 价格下限
            priceMax = validClose * (1 + increaseRange / 100); // 价格上限
        } else {
            // 昨收为0时，取数据极值扩展对称区间
            const prices = timeSharingData.map(item => parseFloat(item[1]) || 0);
            const maxPrice = Math.max(...prices, 1);
            const minPrice = Math.min(...prices, 0);
            const midPrice = (maxPrice + minPrice) / 2;
            const range = Math.max(maxPrice - midPrice, midPrice - minPrice, 0.1);
            priceMin = midPrice - range;
            priceMax = midPrice + range;
        }

        // ========== 工具函数：时间转分钟数（用于15分钟刻度计算） ==========
        const timeToMinutes = (timeStr) => {
            if (!timeStr || !timeStr.includes(':')) return 0;
            const [hour, minute] = timeStr.split(':').map(Number);
            return hour * 60 + minute;
        };

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' },
                textStyle: { fontSize: 10 },
                formatter: function (params) {
                    const time = params[0].axisValue;
                    let price = 0, increase = 0, volume = 0;

                    params.forEach(item => {
                        if (item.seriesName === '价格') {
                            price = item.value;
                            increase = calculateIncrease(price).toFixed(2); // 保留2位小数
                        } else if (item.seriesName === '成交量') {
                            volume = item.value;
                        }
                    });

                    return `
                        <div>${time}</div>
                        <div>价格：${price.toFixed(1)}元</div> <!-- 价格显示1位小数 -->
                        <div>涨幅：${increase > 0 ? '+' : ''}${increase}%</div>
                    `;
                }
            },
            grid: [
                { left: '5%', right: '8%', top: '5%', bottom: '35%', containLabel: true },
                { left: '5%', right: '8%', top: '70%', bottom: '5%', containLabel: true }
            ],
            xAxis: [
                {
                    type: 'category',
                    data: [],
                    axisLabel: {
                        fontSize: 8,
                        margin: 5,
                        // 确保时间格式为hh:mm
                        formatter: function (value) {
                            let time = String(value);
                            // 再次确保只显示时分部分
                            if (time.includes(' ')) {
                                time = time.split(' ')[1];
                            }
                            if (time.includes('T')) {
                                time = time.split('T')[1];
                            }
                            if (time.includes(':')) {
                                const parts = time.split(':');
                                if (parts.length >= 2) {
                                    time = `${parts[0]}:${parts[1]}`;
                                }
                            }
                            return time;
                        },
                        // 核心：将4小时交易时间分成4个时间段显示
                        interval: function (index, value) {
                            if (timeSharingData.length === 0) return false;
                            
                            // 总点数
                            const totalPoints = timeSharingData.length;
                            
                            // 必显示的点：第一个点(9:30), 1/4处(10:30), 1/2处(11:30/13:00), 3/4处(14:00), 最后一个点(15:00)
                            const quarterPoint = Math.floor(totalPoints / 4);
                            const halfPoint = Math.floor(totalPoints / 2);
                            const threeQuarterPoint = Math.floor(totalPoints * 3 / 4);
                            
                            return index === 0 || index === quarterPoint || index === halfPoint || index === threeQuarterPoint || index === totalPoints - 1;
                        }
                    },
                    axisLine: { lineStyle: { color: '#a25555ff', type: 'solid' } },
                    axisTick: { show: true },
                    gridIndex: 0
                },
                {
                    type: 'category',
                    data: [],
                    axisLabel: { show: false },
                    axisLine: { lineStyle: { color: '#333', type: 'solid' } },
                    axisTick: { show: false },
                    gridIndex: 1
                }
            ],
            yAxis: [
                {
                    // 左侧价格Y轴：强制1位小数
                    type: 'value',
                    scale: false,
                    position: 'left',
                    min: priceMin,
                    max: priceMax,
                    splitNumber: 8,
                    axisLabel: {
                        fontSize: 8,
                        formatter: (value) => value.toFixed(1) // 价格刻度只保留1位小数
                    },
                    axisLine: { lineStyle: { color: '#333' } },
                    splitLine: { lineStyle: { color: '#f9fafb' }, show: true },
                    gridIndex: 0
                },
                {
                    // 右侧涨幅Y轴：自动适配±10%/±20%
                    type: 'value',
                    scale: false,
                    position: 'right',
                    min: -increaseRange,
                    max: increaseRange,
                    splitNumber: 8,
                    axisLabel: {
                        fontSize: 8,
                        formatter: '{value}%',
                        color: (value) => {
                            const num = parseFloat(value);
                            return num > 0 ? '#ef4444' : num < 0 ? '#22c55e' : '#333';
                        }
                    },
                    axisLine: { lineStyle: { color: '#ef4444' } },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    gridIndex: 0
                },
                {
                    // 左侧成交量Y轴
                    type: 'value',
                    position: 'left',
                    scale: true,
                    axisLabel: { 
                        show: true,
                        fontSize: 8,
                        formatter: function() {
                            return '   ';
                        }
                    },
                    splitLine: { show: false },
                    gridIndex: 1
                },
                {
                    // 右侧成交量Y轴（用于对齐）
                    type: 'value',
                    position: 'right',
                    scale: true,
                    axisLabel: { 
                        show: true,
                        fontSize: 8,
                        formatter: function() {
                            return '    ';
                        }
                    },
                    axisTick: { show: false },
                    splitLine: { show: false },
                    gridIndex: 1
                }
            ],
            series: [
                {
                    name: '价格',
                    type: 'line',
                    data: [],
                    lineStyle: { color: '#3b82f6', width: 1.8 },
                    symbol: 'none',
                    smooth: true,
                    xAxisIndex: 0,
                    yAxisIndex: 0,
                    markLine: {
                        silent: true,
                        lineStyle: { color: '#888', type: 'dashed', width: 1.5 },
                        symbol: 'none', // 隐藏箭头
                        data: validClose > 0 ? [{
                            yAxis: validClose,
                            name: '昨日收盘价',
                            label: {
                                show: false // 隐藏标签
                            }
                        }] : []
                    }
                },
                {
                    name: '涨幅',
                    type: 'line',
                    data: [],
                    lineStyle: { show: false },
                    symbol: 'none',
                    xAxisIndex: 0,
                    yAxisIndex: 1,
                    itemStyle: { color: 'transparent' }
                },
                {
                    name: '成交量',
                    type: 'bar',
                    data: [],
                    itemStyle: {
                        color: (params) => {
                            const price = params.seriesIndex === 0 ? params.value : timeSharingData[params.dataIndex][1];
                            const inc = calculateIncrease(parseFloat(price));
                            return inc > 0 ? '#ef4444' : inc < 0 ? '#22c55e' : '#9ca3af';
                        }
                    },
                    barWidth: '80%',
                    xAxisIndex: 1,
                    yAxisIndex: 2
                },
                {
                    name: '成交量(右)',
                    type: 'bar',
                    data: [],
                    itemStyle: {
                        color: (params) => {
                            const price = params.seriesIndex === 0 ? params.value : timeSharingData[params.dataIndex][1];
                            const inc = calculateIncrease(parseFloat(price));
                            return inc > 0 ? '#ef4444' : inc < 0 ? '#22c55e' : '#9ca3af';
                        }
                    },
                    barWidth: '80%',
                    xAxisIndex: 1,
                    yAxisIndex: 3
                }
            ],
            legend: { show: false },
            animationDuration: 500,
            animationEasing: 'cubicOut'
        };
        
        if (!timeSharingData || !Array.isArray(timeSharingData) || timeSharingData.length === 0) {
            console.error('分时图数据为空或格式错误');
            // 更新图表显示无数据提示
            timeSharingChart.setOption({
                ...option,
                title: {
                    text: '分时图加载失败',
                    textStyle: { fontSize: 12, color: '#ff6b6b' },
                    left: 'center',
                    top: 'center'
                }
            });
            return;
        }

        const times = [];
        const priceData = [];
        const increaseData = [];
        const volumeData = [];

        timeSharingData.forEach((item, index) => {
            let time = item[0] || '';
            // 提取纯时分部分（只显示hh:mm）
            if (time) {
                // 处理各种可能的时间格式
                
                // 处理格式如 "2023-12-20 09:30:00" 的时间
                if (time.includes(' ')) {
                    time = time.split(' ')[1];
                }
                
                // 处理格式如 "2023-12-20T09:30:00" 的时间
                if (time.includes('T')) {
                    time = time.split('T')[1];
                }
                
                // 处理格式如 "2023/12/20 09:30:00" 的时间
                if (time.includes('/') && time.length > 10) {
                    time = time.substring(time.indexOf(' ') + 1);
                }
                
                // 无论原始格式如何，只保留时:分部分
                if (time.includes(':')) {
                    const parts = time.split(':');
                    if (parts.length >= 2) {
                        time = `${parts[0]}:${parts[1]}`;
                    }
                } else if (time.length === 14) {
                    // 纯数字格式如 20231220093000，转换为 HH:MM
                    const hour = time.substring(8, 10);
                    const minute = time.substring(10, 12);
                    time = `${hour}:${minute}`;
                } else if (time.length === 12) {
                    // 纯数字格式如 202312200930，转换为 HH:MM
                    const hour = time.substring(8, 10);
                    const minute = time.substring(10, 12);
                    time = `${hour}:${minute}`;
                }
            }
            const price = parseFloat(item[1]) || 0;
            const volume = parseFloat(item[2]) || 0;

            times.push(time);
            priceData.push(price);
            increaseData.push(calculateIncrease(price));
            volumeData.push(volume);
        });
        
        // 赋值渲染
        option.xAxis[0].data = times;
        option.xAxis[1].data = times;
        option.series[0].data = priceData;
        option.series[1].data = increaseData;
        option.series[2].data = volumeData;
        option.series[3].data = volumeData;

        timeSharingChart.setOption(option);

        // 自适应缩放
        window.addEventListener('resize', () => timeSharingChart.resize());
        timeSharingChart.on('click', (params) => console.log('分时图点击：', params));
    } catch (error) {
        console.error('Failed to update Time Sharing Chart:', error);
    }
}

/**
 * 工具函数：格式化资金（万元/亿元）
 */
function formatMoney(money) {
    if (money >= 100000000) return (money / 100000000).toFixed(2) + '亿';
    if (money >= 10000) return (money / 10000).toFixed(2) + '万';
    return money.toFixed(2) + '元';
}

/**
 * 工具函数：格式化成交量（手/万手）
 */
function formatVolume(volume) {
    if (volume >= 10000) return (volume / 10000).toFixed(2) + '万手';
    return volume.toFixed(0) + '手';
}

/**
 * 显示加载遮罩
 */
function showLoading() {
    const loadingMask = document.getElementById('loadingMask');
    if (loadingMask) loadingMask.classList.remove('hidden');
}

/**
 * 隐藏加载遮罩
 */
function hideLoading() {
    const loadingMask = document.getElementById('loadingMask');
    if (loadingMask) loadingMask.classList.add('hidden');
}

/**
 * 绘制板块直方图
 */
async function drawSectorHistogram(startDate = '', endDate = '') {
    try {
        console.log('drawSectorHistogram: 开始绘制板块直方图');
        console.log('drawSectorHistogram: getSectorCount函数是否存在:', typeof getSectorCount);
        
        const echarts = await loadECharts();
        // 调用getSectorCount获取板块统计数据，传入日期范围参数
        console.log('drawSectorHistogram: 准备调用getSectorCount函数，日期范围:', startDate, '-', endDate);
        const sectorCountData = await getSectorCount(startDate, endDate);
        console.log('drawSectorHistogram: 返回数据长度:', sectorCountData.length);
        console.log('drawSectorHistogram: 返回数据前3项:', sectorCountData.slice(0, 3));
        
        const chartDom = document.getElementById('sectorHistogram');
        if (!chartDom) {
            console.error('直方图容器未找到');
            return;
        }
        
        // 确保容器有明确的高度设置，解决高度为0的问题
        if (chartDom.style.height === '' || chartDom.offsetHeight === 0) {
            console.log('drawSectorHistogram: 容器高度为0，设置默认高度');
            chartDom.style.height = '350px'; // 设置明确的高度
        }
        
        // 检查图表容器尺寸
        const rect = chartDom.getBoundingClientRect();
        console.log('drawSectorHistogram: 容器尺寸 - 宽度:', rect.width, '高度:', rect.height);
        
        const myChart = echarts.init(chartDom);
        
        // 检查API返回数据
        if (!sectorCountData || sectorCountData.length === 0) {
            console.log('板块统计数据为空，显示空图表');
            // 设置空数据的默认配置
            myChart.setOption({
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'shadow'
                    }
                },
                legend: {
                    data: [],
                    bottom: 10,
                    textStyle: {
                        fontSize: 12
                    }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '9%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: [],
                    axisLabel: {
                        fontSize: 11,
                        rotate: 45,
                        interval: 0
                    },
                    axisTick: {
                        alignWithLabel: true
                    }
                },
                yAxis: {
                    type: 'value',
                    axisLabel: {
                        fontSize: 11
                    }
                },
                series: []
            });
            return;
        }
        
        // 处理数据：按日期和板块组织
        const dateMap = new Map();
        const sectorSet = new Set();
        
        // 将用户选择的日期转换为Date对象，用于比较
        const startDateObj = startDate ? new Date(startDate) : null;
        const endDateObj = endDate ? new Date(endDate) : null;
        
        // 统计每个日期每个板块的股票数量
        sectorCountData.forEach(item => {
            try {
                // 数据验证
                if (!item || !item.date || !item.sector || item.stock_count == null) {
                    console.warn('无效的板块统计数据:', item);
                    return;
                }
                
                const { date, sector, stock_count } = item;
                
                // 将API返回的日期转换为Date对象，用于比较
                const itemDateObj = new Date(date);
                
                // 日期范围过滤：如果设置了日期范围，只保留范围内的数据
                if ((startDateObj && itemDateObj < startDateObj) || (endDateObj && itemDateObj > endDateObj)) {
                    return; // 跳过不在范围内的日期
                }
                
                // 确保sector是字符串类型且不是"undefined"
                const sectorName = String(sector).trim();
                if (!sectorName || sectorName === 'undefined') {
                    console.warn('板块名称为空或无效:', item);
                    return;
                }
                
                sectorSet.add(sectorName);
                
                if (!dateMap.has(date)) {
                    dateMap.set(date, new Map());
                }
                dateMap.get(date).set(sectorName, parseInt(stock_count) || 0);
            } catch (err) {
                console.error('处理板块数据出错:', err, item);
            }
        });
        
        // 验证日期数据
        const validDates = Array.from(dateMap.keys()).filter(date => {
            const isValidDate = !isNaN(new Date(date).getTime());
            if (!isValidDate) {
                console.warn('无效的日期格式:', date);
            }
            return isValidDate;
        });
        
        // 按日期排序并格式化（去掉年份只显示月日）
        const sortedDates = validDates.sort((a, b) => new Date(a) - new Date(b));
        
        // 根据是否有日期范围选择来决定显示数据量
        let recentDates;
        if (startDate || endDate) {
            // 如果用户选择了日期范围，显示完整的日期范围数据
            recentDates = sortedDates;
            console.log('显示完整日期范围数据，数据长度:', recentDates.length);
        } else {
            // 如果没有选择日期范围，只显示最近的35个数据
            recentDates = sortedDates.slice(-35);
            console.log('只显示最近的35个数据，原始数据长度:', sortedDates.length, '，保留后数据长度:', recentDates.length);
        }
        
        // 格式化后的日期用于显示
        const formattedDates = recentDates.map(date => {
            const d = new Date(date);
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${month}-${day}`;
        });
        
        // 计算每个板块的总股票数（用于排序）
        const sectorTotalMap = new Map();
        sectorSet.forEach(sector => {
            // 确保板块名称有效
            if (!sector || typeof sector !== 'string' || sector.trim() === '') {
                return;
            }
            
            const sectorName = sector.trim();
            let total = 0;
            dateMap.forEach((sectorMap) => {
                if (sectorMap.has(sectorName)) {
                    total += sectorMap.get(sectorName);
                }
            });
            sectorTotalMap.set(sectorName, total);
        });
        
        // 按总股票数降序排序板块
        const sortedSectors = Array.from(sectorTotalMap.keys()).sort((a, b) => sectorTotalMap.get(b) - sectorTotalMap.get(a));
        // 数据有效性检查
        if (sortedDates.length === 0) {
            console.warn('没有有效的日期数据');
            // 设置空数据的默认配置
            myChart.setOption({
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'shadow'
                    }
                },
                legend: {
                    data: [],
                    bottom: 10,
                    textStyle: {
                        fontSize: 12
                    }
                },
                grid: {
                    left: '3%',
                    right: '4%',
                    bottom: '5%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: [],
                    axisLabel: {
                        fontSize: 11,
                        rotate: 45,
                        interval: 0
                    },
                    axisTick: {
                        alignWithLabel: true
                    }
                },
                yAxis: {
                    type: 'value',
                    axisLabel: {
                        fontSize: 11
                    }
                },
                series: []
            });
            return;
        }
        
        // 实现每个日期独立排序堆叠的核心逻辑
        // 采用层级series方案：为每个堆叠层级创建一个series，而不是为每个板块创建series
        // 这样每个日期可以独立排序板块，最大的板块在每个柱子的最上面
        
        const sectorColors = new Map(); // 存储板块颜色映射
        
        // 首先为所有板块分配颜色
        sectorSet.forEach(sectorName => {
            if (sectorName && sectorName.trim() !== '') {
                const trimmedName = sectorName.trim();
                sectorColors.set(trimmedName, getColorBySector(trimmedName));
            }
        });
                // 计算最大的堆叠层级数量（任何日期的最大板块数量）
        let maxStackLevels = 0;
        recentDates.forEach(date => {
            const sectorMap = dateMap.get(date);
            if (sectorMap) {
                const sectorCount = Array.from(sectorMap.entries())
                    .filter(([sectorName]) => sectorName && sectorName.trim() !== '')
                    .length;
                maxStackLevels = Math.max(maxStackLevels, sectorCount);
            }
        });        
        console.log('最大堆叠层级数:', maxStackLevels);
        
        // 创建层级数据结构：存储每个日期每个层级的板块名称和数量
        const levelData = [];
        for (let level = 0; level < maxStackLevels; level++) {
            levelData.push(new Array(recentDates.length).fill(null));
        }
        
        // 存储每个层级series的名称映射
        const levelNamesMap = new Map();
        
        // 为每个日期处理数据和堆叠顺序
        recentDates.forEach((date, dateIndex) => {
            const sectorMap = dateMap.get(date);
            if (!sectorMap) return;
            
            // 将当前日期的所有板块按stock_count降序排序
            const sortedSectorsForDate = Array.from(sectorMap.entries())
                .filter(([sectorName]) => sectorName && sectorName.trim() !== '')
                .sort((a, b) => b[1] - a[1]);

            // 将排序后的板块分配到各个层级
            sortedSectorsForDate.forEach(([sectorName, stockCount], sectorIndex) => {
                const trimmedName = sectorName.trim();
                // 再次验证板块名称的有效性
                if (!trimmedName || trimmedName === 'undefined') {
                    console.warn('无效的板块名称在层级分配时:', trimmedName);
                    return;
                }
                // 确保stockCount是有效的数字
                const validStockCount = parseFloat(stockCount) || 0;
                levelData[sectorIndex][dateIndex] = { name: trimmedName, value: validStockCount };
                
                // 记录该层级包含的所有板块名称
                if (!levelNamesMap.has(sectorIndex)) {
                    levelNamesMap.set(sectorIndex, new Set());
                }
                levelNamesMap.get(sectorIndex).add(trimmedName);
            });
        });
        
        // 为每个层级创建一个series
        const series = [];
        
        // 从最高层级到最低层级创建series，这样最大的板块会显示在最上面
        for (let levelIndex = levelData.length - 1; levelIndex >= 0; levelIndex--) {
            const level = levelData[levelIndex];
            
            // 为该层级创建一个series
            const levelSeries = {
                name: `Level ${levelIndex + 1}`, // 层级名称，不显示在图例中
                type: 'bar',
                stack: 'total', // 所有层级使用相同的stack名称
                data: [],
                barWidth: '60%',
                // 使用自定义的itemStyle来设置颜色
                itemStyle: {
                    color: function(params) {
                        const item = level[params.dataIndex];
                        if (item) {
                            return sectorColors.get(item.name);
                        }
                        return '#ccc'; // 默认颜色
                    }
                }
            };
            
            // 为该层级的每个日期填充数据
            level.forEach((item, dateIndex) => {
                if (item) {
                    // 直接存储包含名称和值的对象，这样tooltip可以直接访问
                    levelSeries.data.push(item);
                } else {
                    levelSeries.data.push(0);
                }
            });
            
            series.push(levelSeries);
        }
        
        console.log('层级series数量:', series.length);
        console.log('层级series示例数据:', series.slice(0, 2).map(s => ({name: s.name, data: s.data.slice(0, 5)})));
        
        // 按总股票数降序排序板块，用于图例显示（使用已计算的sectorTotalMap）
        const sortedSectorsForLegend = Array.from(sectorTotalMap.keys())
            .sort((a, b) => sectorTotalMap.get(b) - sectorTotalMap.get(a));
        
        // 提取有效的图例数据
        const legendData = sortedSectorsForLegend;
        
        // 配置选项
        const option = {
            title: {
                text: '题材/板块接力',
                left: 'left',
                textStyle: {
                    fontSize: 18
                }
            },
            tooltip: {
                trigger: 'item',
                axisPointer: {
                    type: 'shadow'
                },
                formatter: function(params) {
                    // 数据安全检查
                    if (!params || !params.marker || !params.data) {
                        return '';
                    }
                    
                    // 安全获取轴值
                    const axisValue = params.axisValue || '';
                    let result = axisValue + '<br/>';
                    
                    // 处理数据对象，获取实际的板块名称和值
                    const data = params.data;
                    if (typeof data === 'object' && data !== null) {
                        const name = data.name || '未知板块';
                        const value = data.value || 0;
                        result += params.marker + name + ': ' + value;
                    } else {
                        const seriesName = params.seriesName || '未知系列';
                        const value = data || 0;
                        result += params.marker + seriesName + ': ' + value;
                    }
                    
                    return result;
                }
            },
            legend: {
                data: legendData,
                bottom: 10,
                textStyle: {
                    fontSize: 12
                },
                type: 'scroll', // 图例过多时显示滚动条
                orient: 'horizontal'
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '5%', // 增加底部空间以容纳图例
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: formattedDates,
                axisLabel: {
                    fontSize: 11,
                    rotate: 45,
                    interval: 0
                },
                axisTick: {
                    alignWithLabel: true
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: {
                    fontSize: 11
                }
            },
            series: series
        };
        
        // 最终数据验证
        console.log('最终图表配置 - 日期数量:', sortedDates.length);
        console.log('最终图表配置 - 板块数量:', series.length);
        console.log('最终图表配置 - 图例数量:', legendData.length);
        console.log('最终图表配置 - series示例:', series.slice(0, 2));
        
        myChart.setOption(option);
        
        // 创建并定位日期范围选择器到图表内部，传递当前日期范围参数
        createDateRangeSelector(myChart, chartDom, startDate, endDate);
        
        // 窗口大小变化时重绘
        window.addEventListener('resize', () => {
            myChart.resize();
        });
        
    } catch (error) {
        console.error('绘制板块直方图失败：', error);
    }
}

/**
 * 在图表内部创建并定位日期范围选择器
 * @param {Object} chart - ECharts实例
 * @param {HTMLElement} chartDom - 图表容器DOM元素
 */
function createDateRangeSelector(chart, chartDom, startDate = '', endDate = '') {
    // 移除已存在的日期选择器容器，避免重复创建
    const existingSelector = chartDom.querySelector('.chart-date-selector-container');
    if (existingSelector) {
        existingSelector.remove();
    }
    
    // 创建日期选择器容器
    const selectorContainer = document.createElement('div');
    selectorContainer.className = 'chart-date-selector-container';
    selectorContainer.style.cssText = `
        position: absolute;
        top: 2px;
        right: 10px;
        z-index: 100;
        display: flex;
        align-items: center;
        gap: 10px;
        background-color: white;
        padding: 8px 12px;
        border-radius: 4px;
        // box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    `;
    
    // 创建开始日期选择
    const startDateWrapper = document.createElement('div');
    startDateWrapper.className = 'date-input-wrapper';
    startDateWrapper.style.cssText = `
        display: flex;
        align-items: center;
        gap: 5px;
    `;
    
    const startDateLabel = document.createElement('label');
    startDateLabel.textContent = '开始日期：';
    startDateLabel.style.cssText = `
        font-size: 12px;
        color: #666;
    `;
    
    const startDateInput = document.createElement('input');
    startDateInput.type = 'date';
    startDateInput.id = 'startDate';
    startDateInput.value = startDate;
    startDateInput.style.cssText = `
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
    `;
    
    // 设置最大日期为今天
    const today = new Date().toISOString().split('T')[0];
    startDateInput.max = today;
    
    startDateWrapper.appendChild(startDateLabel);
    startDateWrapper.appendChild(startDateInput);
    
    // 创建结束日期选择
    const endDateWrapper = document.createElement('div');
    endDateWrapper.className = 'date-input-wrapper';
    endDateWrapper.style.cssText = `
        display: flex;
        align-items: center;
        gap: 5px;
    `;
    
    const endDateLabel = document.createElement('label');
    endDateLabel.textContent = '结束日期：';
    endDateLabel.style.cssText = `
        font-size: 12px;
        color: #666;
    `;
    
    const endDateInput = document.createElement('input');
    endDateInput.type = 'date';
    endDateInput.id = 'endDate';
    endDateInput.value = endDate;
    endDateInput.style.cssText = `
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
    `;
    endDateInput.max = today;
    
    endDateWrapper.appendChild(endDateLabel);
    endDateWrapper.appendChild(endDateInput);
    
    // 创建应用按钮
    const applyBtn = document.createElement('button');
    applyBtn.className = 'apply-date-btn';
    applyBtn.innerHTML = '<i class="fa fa-filter mr-1"></i> 应用';
    applyBtn.style.cssText = `
        padding: 6px 12px;
        background-color: #3b82f6;
        color: white;
        border: none;
        border-radius: 4px;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
    `;
    
    // 创建重置按钮
    const resetBtn = document.createElement('button');
    resetBtn.className = 'reset-date-btn';
    resetBtn.innerHTML = '<i class="fa fa-refresh mr-1"></i> 重置';
    resetBtn.style.cssText = `
        padding: 6px 12px;
        background-color: #9ca3af;
        color: white;
        border: none;
        border-radius: 4px;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
    `;
    
    // 添加到容器
    selectorContainer.appendChild(startDateWrapper);
    selectorContainer.appendChild(endDateWrapper);
    selectorContainer.appendChild(applyBtn);
    selectorContainer.appendChild(resetBtn);
    
    // 将日期选择器容器添加到图表容器
    chartDom.style.position = 'relative';
    chartDom.appendChild(selectorContainer);
    
    // 应用按钮点击事件
    applyBtn.addEventListener('click', async () => {
        const startDate = startDateInput.value || '';
        const endDate = endDateInput.value || '';
        
        // 显示加载遮罩
        showLoading();
        try {
            await drawSectorHistogram(startDate, endDate);
        } finally {
            hideLoading();
        }
    });
    
    // 重置按钮点击事件
    resetBtn.addEventListener('click', async () => {
        startDateInput.value = '';
        endDateInput.value = '';
        
        // 显示加载遮罩
        showLoading();
        try {
            await drawSectorHistogram('', '');
        } finally {
            hideLoading();
        }
    });
}

// 全局CSS样式（保持原样）
const style = document.createElement('style');
style.textContent = `
    /* 基础样式重置 */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* 抽屉样式 */
    .drawer-header {
        cursor: pointer;
        transition: background-color 0.2s;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .drawer-header:hover {
        background-color: #f9fafb;
    }
    .drawer-content {
        display: none;
        scrollbar-width: thin;
        scroll-behavior: smooth;
    }
    .drawer-content::-webkit-scrollbar {
        width: 6px;
    }
    .drawer-content::-webkit-scrollbar-thumb {
        background-color: #d1d5db;
        border-radius: 3px;
    }
    .drawer-content::-webkit-scrollbar-track {
        background-color: #f9fafb;
    }
    .drawer-expanded .drawer-content {
        display: block;
    }
    .drawer-arrow {
        transition: transform 0.2s ease;
    }

    /* 股票项样式 */
    .stock-item-hover:hover {
        border-color: #3b82f6;
        background-color: #f0f9ff;
    }
    .stock-item-active {
        border-color: #22c55e;
        background-color: #ecfdf5;
        font-weight: 600;
    }

    /* 股票卡片样式 */
    .stock-card {
        border-color: #e5e7eb;
        transition: all 0.2s ease;
        min-height: 200px;
    }
    .stock-card-active {
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
    }
    .stock-detail {
        overflow: hidden;
    }
    .kline-wrapper {
        overflow: hidden;
    }

    /* 滚动容器优化 */
    .overflow-x-auto {
        overflow-x: auto;
        overflow-y: auto;
        scrollbar-width: thin;
        scroll-behavior: smooth;
    }
    .overflow-x-auto::-webkit-scrollbar {
        height: 6px;
        width: 6px;
    }
    .overflow-x-auto::-webkit-scrollbar-thumb {
        background-color: #d1d5db;
        border-radius: 3px;
    }
    .overflow-x-auto::-webkit-scrollbar-track {
        background-color: #f9fafb;
    }

    /* 表格样式核心 */
    .border-collapse {
        border-collapse: collapse !important;
    }
    .table th, .table td {
        border: 1px solid #e5e7eb !important;
    }
    .bg-white {
        background-color: #ffffff !important;
    }
    .bg-gray-50 {
        background-color: #f9fafb !important;
    }
    .vertical-align-top {
        vertical-align: top !important;
    }
    .min-h-[36px] {
        min-height: 36px !important;
    }
    .w-[60px] {
        width: 60px !important;
    }
    .w-[50px] {
        width: 50px !important;
    }

    /* 1板行显示/隐藏控制 */
    tr[data-hidden="true"] {
        display: none !important;
    }
    tr[data-hidden="false"] {
        display: table-row !important;
    }

    /* 展开/收起按钮样式 */
    .justify-end {
        justify-content: flex-end !important;
    }
    .mt-2 {
        margin-top: 0.5rem !important;
    }
    .px-3 {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    .py-1 {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .rounded {
        border-radius: 0.375rem !important;
    }
    .text-xs {
        font-size: 0.75rem !important;
    }
    .flex {
        display: flex !important;
    }
    .items-center {
        align-items: center !important;
    }
    .gap-1 {
        gap: 0.25rem !important;
    }
    .transition-colors {
        transition-property: color, background-color, border-color !important;
        transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1) !important;
        transition-duration: 150ms !important;
    }
    .bg-gray-100 {
        background-color: #f3f4f6 !important;
    }
    .hover\\:bg-gray-200:hover {
        background-color: #e5e7eb !important;
    }
    .text-gray-700 {
        color: #374151 !important;
    }

    /* 边框样式统一 */
    .border-r {
        border-right: 1px solid #e5e7eb !important;
    }
    .border-b {
        border-bottom: 1px solid #e5e7eb !important;
    }
    .border-t {
        border-top: 1px solid #e5e7eb !important;
    }
    .border {
        border: 1px solid #e5e7eb !important;
    }

    /* 尺寸样式 */
    .w-full {
        width: 100% !important;
    }
    .h-full {
        height: 100% !important;
    }
    .flex-grow {
        flex-grow: 1 !important;
    }

    /* 间距样式 */
    .mb-4 {
        margin-bottom: 1rem !important;
    }
    .mb-3 {
        margin-bottom: 0.75rem !important;
    }
    .mb-2 {
        margin-bottom: 0.5rem !important;
    }
    .mb-0.5 {
        margin-bottom: 0.125rem !important;
    }
    .mt-4 {
        margin-top: 1rem !important;
    }
    .mt-[-1px] {
        margin-top: -1px !important;
    }
    .ml-2 {
        margin-left: 0.5rem !important;
    }
    .ml-0.5 {
        margin-left: 0.125rem !important;
    }
    .p-4 {
        padding: 1rem !important;
    }
    .p-3 {
        padding: 0.75rem !important;
    }
    .p-2 {
        padding: 0.5rem !important;
    }
    .p-1 {
        padding: 0.25rem !important;
    }
    .p-0.5 {
        padding: 0.125rem !important;
    }
    .px-4 {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    .py-3 {
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
    }
    .py-2 {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }
    .py-1.5 {
        padding-top: 0.375rem !important;
        padding-bottom: 0.375rem !important;
    }
    .py-1 {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
    }
    .py-0.5 {
        padding-top: 0.125rem !important;
        padding-bottom: 0.125rem !important;
    }
    .px-2 {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    .px-1.5 {
        padding-left: 0.375rem !important;
        padding-right: 0.375rem !important;
    }
    .gap-4 {
        gap: 1rem !important;
    }
    .gap-3 {
        gap: 0.75rem !important;
    }

    /* 文本样式 */
    .text-center {
        text-align: center !important;
    }
    .text-gray-800 {
        color: #1f2937 !important;
    }
    .text-gray-500 {
        color: #6b7280 !important;
    }
    .text-gray-300 {
        color: #d1d5db !important;
    }
    .text-red-500 {
        color: #ef4444 !important;
    }
    .text-blue-700 {
        color: #1d4ed8 !important;
    }
    .text-[9px] {
        font-size: 9px !important;
    }
    .text-[10px] {
        font-size: 10px !important;
    }
    .text-[11px] {
        font-size: 11px !important;
    }
    .text-sm {
        font-size: 0.875rem !important;
    }
    .text-base {
        font-size: 1rem !important;
    }
    .text-lg {
        font-size: 1.125rem !important;
    }
    .font-bold {
        font-weight: 700 !important;
    }
    .font-medium {
        font-weight: 500 !important;
    }

    /* 布局样式 */
    .flex-col {
        flex-direction: column !important;
    }
    .justify-center {
        justify-content: center !important;
    }
    .justify-between {
        justify-content: space-between !important;
    }
    .grid {
        display: grid !important;
    }
    .grid-cols-2 {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    }
    .grid-rows-3 {
        grid-template-rows: repeat(3, minmax(0, 1fr)) !important;
    }
    .space-y-6 > * + * {
        margin-top: 1.5rem !important;
    }
    .relative {
        position: relative !important;
    }

    /* 圆角样式 */
    .rounded-lg {
        border-radius: 0.5rem !important;
    }
    .rounded-full {
        border-radius: 9999px !important;
    }

    /* 阴影样式 */
    .shadow-sm {
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    }

    /* 隐藏/显示 */
    .hidden {
        display: none !important;
    }

    /* 加载动画 */
    .fa-spin {
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* 过渡效果 */
    .transition-all {
        transition-property: all !important;
        transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1) !important;
        transition-duration: 150ms !important;
    }

    /* 响应式调整 */
    @media (max-width: 1024px) {
        .stock-card {
            flex-direction: column !important;
            min-height: auto !important;
        }
        .stock-detail {
            width: 100% !important;
            margin-bottom: 1rem !important;
        }
        .kline-wrapper {
            width: 100% !important;
            height: 400px !important;
        }
    }
    @media (max-width: 768px) {
        .grid-cols-2 {
            grid-template-columns: 1fr !important;
        }
        .drawer-content {
            max-height: 70vh !important;
        }
        .kline-wrapper {
            height: 350px !important;
        }
        .text-[10px] {
            font-size: 9px !important;
        }
        .text-[9px] {
            font-size: 8px !important;
        }
    }
`;
document.head.appendChild(style);