import { POPUP_STYLES } from '../constants/styleConstants.js';

/**
 * 下载按钮组件（单例）
 */
class DownloadButton {
  constructor() {
    this.button = null;
    this.init();
  }

  // 初始化下载按钮
  init() {
    this.button = document.getElementById('download-image-btn');
    if (this.button) return;

    this.button = document.createElement('button');
    this.button.id = 'download-image-btn';
    this.button.style.cssText = `
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 4px;
      padding: 4px 8px;
      cursor: pointer;
      color: white;
      font-size: 14px;
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    `;
    this.button.innerHTML = '<i class="fa fa-download"></i>';
    this.button.title = '保存右侧栏为图片';
    this._bindClickEvent();

    // 将按钮添加到右侧容器的header中
    const rightContainer = document.getElementById('right-container');
    if (rightContainer) {
      const header = rightContainer.querySelector('.header');
      if (header) {
        // 修改header的样式，使其支持flex布局
        header.style.position = 'relative';
        
        // 将标题和按钮放入header中
        const title = header.querySelector('h3');
        if (title) {
          title.style.margin = '0';
        }
        
        // 设置按钮样式，使其绝对定位在右侧
        this.button.style.position = 'absolute';
        this.button.style.right = '30px';
        this.button.style.top = '50%';
        this.button.style.transform = 'translateY(-50%)';
        header.appendChild(this.button);
      }
    }
  }

  /**
   * 绑定点击事件（调用下载逻辑）
   */
  _bindClickEvent() {
    this.button.addEventListener('click', this.saveAsImage.bind(this));
  }

  /**
   * 等待ECharts图表渲染完成（确保Canvas有内容）
   * @param {HTMLElement} container 包含图表的容器
   * @returns {Promise} 渲染完成的Promise
   */
  _waitEchartsRender(container) {
    return new Promise((resolve) => {
      // 检查所有图表Canvas是否已渲染
      const checkCanvas = () => {
        const chartCanvases = container.querySelectorAll('.kline-area canvas');
        const allRendered = Array.from(chartCanvases).every(canvas => {
          return canvas.width > 0 && canvas.height > 0;
        });

        if (allRendered) {
          resolve();
        } else {
          // 未渲染完成则延迟重试（最多等待3秒）
          setTimeout(checkCanvas, 100);
        }
      };

      checkCanvas();
    });
  }

  /**
   * 计算有效内容区域的宽高（仅包含header + 统计栏 + 表格区域，无多余空白）
   * @param {HTMLElement} container 右侧容器
   * @returns {Object} 有效宽高 {width, height}
   */
  _calcEffectiveContentSize(container) {
    const headerEl = container.querySelector('.header');
    const statsBarEl = container.querySelector('.daily-stats-bar');
    const tableWrapperEl = container.querySelector('div[style*="overflow-x: auto"]');

    // 各部分高度求和（包含间距）
    const headerHeight = headerEl ? headerEl.offsetHeight : 0;
    const statsBarHeight = statsBarEl ? statsBarEl.offsetHeight + 2 : 0; // +8是margin
    const tableWrapperHeight = tableWrapperEl ? tableWrapperEl.offsetHeight : 0;

    // 有效高度 = 所有核心内容高度之和
    const effectiveHeight = headerHeight + statsBarHeight + tableWrapperHeight;
    // 有效宽度 = 内容实际滚动宽度（避免截断）
    const effectiveWidth = container.scrollWidth || container.offsetWidth;

    return { width: effectiveWidth, height: effectiveHeight };
  }

  /**
   * 下载右侧栏为图片（保留图表，精准截取有效区域）
   */
  async saveAsImage() {
    const targetElement = document.getElementById('right-container');
    if (!targetElement) {
      alert('未找到右侧栏容器，下载失败！');
      return;
    }

    // 等待图表渲染完成（关键：确保Canvas有内容）
    await this._waitEchartsRender(targetElement);

    // 保存原有样式
    const originalStyles = {
      overflow: targetElement.style.overflow,
      minWidth: targetElement.style.minWidth,
      height: targetElement.style.height,
      position: targetElement.style.position,
      left: targetElement.style.left,
      top: targetElement.style.top,
      zIndex: targetElement.style.zIndex
    };

    try {
      // 计算有效内容区域（核心：只截取需要的部分，剔除空白）
      const { width: effectiveWidth, height: effectiveHeight } = this._calcEffectiveContentSize(targetElement);

      // 临时配置：强制容器展开，仅显示有效内容区域
      targetElement.style.overflow = 'visible';
      targetElement.style.minWidth = `${effectiveWidth}px`;
      targetElement.style.height = `${effectiveHeight}px`; // 固定高度为有效内容高度，剔除空白
      targetElement.style.position = 'absolute'; // 临时绝对定位，避免页面布局干扰
      targetElement.style.left = '0';
      targetElement.style.top = '0';
      targetElement.style.zIndex = '9999';

      // 处理滚动偏移（确保内容不偏移）
      const scrollY = targetElement.scrollTop || 0;
      const scrollX = targetElement.scrollLeft || 0;

      // 生成文件名
      const dateStr = this._generateFileName();

      // 调用html2canvas生成图片（关键配置：确保捕获ECharts Canvas）
      const canvas = await html2canvas(targetElement, {
        scale: 2, // 2倍分辨率，保证图片清晰
        useCORS: true, // 允许跨域图片
        allowTaint: true, // 允许捕获Canvas（关键：ECharts图表需要）
        logging: false,
        backgroundColor: '#fff',
        scrollX: -scrollX,
        scrollY: -scrollY,
        windowWidth: effectiveWidth, // 仅渲染有效宽度
        windowHeight: effectiveHeight, // 仅渲染有效高度（无空白）
        ignoreElements: (element) => element.id === 'download-image-btn',
        // 强制包含所有Canvas元素（ECharts图表）
        includeAllElements: true
      });

      // 下载图片
      const link = document.createElement('a');
      link.download = `${dateStr}_连板天梯.png`;
      canvas.toBlob(blob => {
        link.href = URL.createObjectURL(blob);
        link.click();
        URL.revokeObjectURL(link.href);
      }, 'image/png', 1.0);

    } catch (error) {
      alert('图片生成失败：' + error.message);
      console.error('图片转换错误:', error);
    } finally {
      // 恢复原有样式
      Object.keys(originalStyles).forEach(key => {
        targetElement.style[key] = originalStyles[key] || '';
      });
    }
  }

  /**
   * 生成文件名（日期部分）
   * @returns {string} 日期字符串（YYYY_MMDD）
   */
  _generateFileName() {
    const rightTitle = document.getElementById('right-title').textContent;
    const rightDateMatch = rightTitle.match(/(\d+)\.(\d+)/);

    if (rightDateMatch) {
      const year = new Date().getFullYear();
      const month = rightDateMatch[1].padStart(2, '0');
      const day = rightDateMatch[2].padStart(2, '0');
      return `${year}_${month}${day}`;
    } else {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      return `${year}${month}${day}`;
    }
  }
}

// 单例导出
export const downloadButton = new DownloadButton();