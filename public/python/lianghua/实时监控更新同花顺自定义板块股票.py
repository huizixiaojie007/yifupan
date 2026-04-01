#实时监控更新同花顺自定义板块股票

"""
同花顺自定义板块提取器
用于解析同花顺StockBlock.ini文件，提取板块和股票信息
"""

import re
import os
import time
import threading
import pandas as pd

# ==== 可配置项（请按需修改） ====
INI_PATH = r"D:\THS\同花顺\边塞牧童\StockBlock.ini"
TARGET_BLOCK = "固态电池"
POLLING_INTERVAL = 0.2          # 轮询间隔（秒），未安装 watchdog 时生效
DEBOUNCE_SECONDS = 0.05         # 去抖时间（秒）
STABILIZE_WINDOW = 0.6          # 稳定窗（秒）：合并同一轮多个写入，减少误报
USE_POLLING = False             # 强制使用轮询（True）或优先 watchdog（False）

# 尝试导入chardet，如果没有则使用默认编码
try:
    import chardet

    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False
    print("警告: 未安装chardet包，将使用默认编码gb2312读取文件")

# 尝试导入watchdog（可选，用于实时文件监听）
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except Exception:
    HAS_WATCHDOG = False
    print("提示: 未安装watchdog，将使用轮询方式监听文件变化（pip install watchdog 可启用文件系统监听）")


class TongHuaShunStockExtractor:
    """同花顺自定义板块股票提取器"""

    def __init__(self, ini_file_path):
        """
        初始化提取器

        Args:
            ini_file_path (str): 同花顺StockBlock.ini文件路径
        """
        self.ini_file_path = ini_file_path
        self.content = None
        self.block_map = {}  # 板块名称到ID的映射
        self.stock_data = {}  # 板块ID到股票代码的映射

    def load_file(self):
        """
        加载并读取文件内容

        Returns:
            bool: 是否成功加载文件
        """
        if not os.path.exists(self.ini_file_path):
            print(f"错误：文件不存在 - {self.ini_file_path}")
            return False

        # 检测文件编码
        try:
            with open(self.ini_file_path, 'rb') as f:
                raw_data = f.read()

                if HAS_CHARDET:
                    detection = chardet.detect(raw_data)
                    encoding = detection['encoding'] or 'gb2312'
                else:
                    encoding = 'gb2312'  # 默认编码

                self.content = raw_data.decode(encoding, errors='replace')
            # print(f"成功读取文件 (编码: {encoding})")  # 静默处理
            return True
        except Exception as e:
            print(f"读取文件失败: {str(e)}")
            return False

    def parse_block_mapping(self):
        """
        解析板块名称与ID的映射关系

        Returns:
            bool: 是否成功解析映射关系
        """
        if not self.content:
            return False

        # 提取[BLOCK_NAME_MAP_TABLE]部分
        # 提取[BLOCK_NAME_MAP_TABLE]部分（到下一个段落头或文件末尾），兼容CRLF
        map_pattern = re.compile(r'\[BLOCK_NAME_MAP_TABLE\](.*?)(?=\r?\n\[|$)', re.DOTALL)
        match = map_pattern.search(self.content)
        if not match:
            print("未找到板块映射表")
            return False

        # 解析每个板块的ID和名称
        for line in match.group(1).split('\n'):
            line = line.strip()
            if '=' in line and line.split('=')[0].strip():
                block_id, block_name = line.split('=', 1)
                block_id = block_id.strip()
                block_name = block_name.strip()
                if block_id and block_name:
                    self.block_map[block_name] = block_id

        return True

    def parse_stock_data(self):
        """
        解析所有板块的股票数据

        Returns:
            bool: 是否成功解析股票数据
        """
        if not self.content:
            return False

        # 提取[BLOCK_STOCK_CONTEXT]部分
        # 提取[BLOCK_STOCK_CONTEXT]部分（到下一个段落头或文件末尾），兼容CRLF
        context_pattern = re.compile(r'\[BLOCK_STOCK_CONTEXT\](.*?)(?=\r?\n\[|$)', re.DOTALL)
        match = context_pattern.search(self.content)
        if not match:
            print("未找到股票数据区域")
            return False

        # 解析每个板块的股票代码
        context_content = match.group(1)
        # 以“下一行出现新的 block_id=”或到文件结尾作为分隔，兼容不以',,'结尾的情况
        block_iter = re.finditer(r'(?m)^(\w+)\s*=(.*?)(?=\n\w+\s*=|\Z)', context_content, re.S)

        for block_match in block_iter:
            block_id = block_match.group(1).strip()
            stock_str = block_match.group(2)

            # 抓取所有6位数字代码（兼容冒号、逗号、空白等任意分隔）
            codes = re.findall(r'(?<!\d)(\d{6})(?!\d)', stock_str or '')

            if codes:
                self.stock_data[block_id] = list(set(codes))  # 去重

        return True

    def get_block_stocks(self, block_name):
        """
        获取指定板块的股票代码

        Args:
            block_name (str): 板块名称

        Returns:
            list: 股票代码列表
        """
        if block_name not in self.block_map:
            # 尝试模糊匹配
            similar_blocks = [name for name in self.block_map.keys()
                              if block_name in name]
            if similar_blocks:
                # 静默返回相似板块，可在上层处理
                return []
            else:
                # 静默：未找到该板块
                return []

        block_id = self.block_map[block_name]
        if block_id not in self.stock_data:
            # 静默：该板块暂无股票数据
            return []

        return self.stock_data[block_id]

    def get_block_stocks_with_market(self, block_name):
        """
        获取指定板块的股票代码并添加市场后缀

        Args:
            block_name (str): 板块名称

        Returns:
            list: 带市场后缀的股票代码列表
        """
        stock_codes = self.get_block_stocks(block_name)
        formatted_stocks = []

        for code in stock_codes:
            fcode = code[:2]
            if fcode in ['00', '30']:
                formatted_stocks.append(code + '.SZ')
            elif fcode in ['60', '68']:
                formatted_stocks.append(code + '.SH')

        return formatted_stocks

    def get_block_stocks_dataframe(self, block_name):
        """
        获取指定板块的股票代码并返回DataFrame格式

        Args:
            block_name (str): 板块名称

        Returns:
            pd.DataFrame: 包含证券代码的DataFrame
        """
        stock_codes = self.get_block_stocks(block_name)
        if not stock_codes:
            return pd.DataFrame()

        df = pd.DataFrame()
        df['证券代码'] = stock_codes
        return df

    def list_all_blocks(self, limit=10):
        """
        列出所有板块

        Args:
            limit (int): 显示的板块数量限制
        """
        block_names = list(self.block_map.keys())
        for i, name in enumerate(block_names[:limit]):
            pass
        if len(block_names) > limit:
            pass

    def get_all_blocks(self):
        """
        获取所有板块名称列表

        Returns:
            list: 所有板块名称列表
        """
        return list(self.block_map.keys())


class StockBlockMonitor:
    """实时监听 StockBlock.ini 和 custom_block/<block_id> 的变化并在目标板块股票发生增删时回调"""
    def __init__(self, ini_path, block_name, on_update, interval=0.2, debounce=0.05, stabilize_window=0.6, use_polling=False):
        self.ini_path = ini_path
        self.block_name = block_name
        self.on_update = on_update  # 回调: on_update(codes, added, removed)
        self.interval = float(interval)
        self.debounce = float(debounce)
        self.use_polling = use_polling
        self._stabilize_window = float(stabilize_window)
        self._timer = None
        self._pending_sources = set()
        self._last_custom_change_path = None
        self._stop = False
        self._observer = None
        self._last_codes = None

        # 归一化路径（大小写不敏感）
        self._abs_path = os.path.abspath(self.ini_path)
        self._norm_ini = os.path.normcase(self._abs_path)

        # 目标 custom_block 文件（启动后解析 block_id 再确定）
        self._custom_block_path = None
        self._norm_custom = None
        self._block_id = None  # 记录当前板块的ID

        # 轮询签名 (mtime_ns, size)
        self._sig_ini = None
        self._sig_custom = None

        self._extractor = TongHuaShunStockExtractor(self.ini_path)

    def _file_signature(self, path):
        try:
            st = os.stat(path)
            return (st.st_mtime_ns, st.st_size)
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def _format_with_market(self, codes):
        formatted = []
        for code in codes:
            f = code[:2]
            if f in ("00", "30"):
                formatted.append(code + ".SZ")
            elif f in ("60", "68"):
                formatted.append(code + ".SH")
        return sorted(set(formatted))

    def _update_block_id_and_custom_path(self):
        """解析 block_id，并更新 custom_block/<block_id> 路径"""
        try:
            self._block_id = self._extractor.block_map.get(self.block_name)
            if not self._block_id:
                return
            base_dir = os.path.dirname(self._abs_path) or "."
            candidate = os.path.join(base_dir, "custom_block", str(self._block_id))
            self._custom_block_path = candidate
            self._norm_custom = os.path.normcase(os.path.abspath(candidate))
        except Exception:
            pass

    def _get_codes_from_extractor_silent(self):
        """从 extractor 的内部数据结构静默读取（不触发打印）"""
        try:
            if not self._block_id:
                self._block_id = self._extractor.block_map.get(self.block_name)
            if not self._block_id:
                return []
            codes = self._extractor.stock_data.get(self._block_id, []) or []
            codes = [c for c in codes if isinstance(c, str) and len(c) == 6 and c.isdigit()]
            return self._format_with_market(codes)
        except Exception:
            return []

    def _try_parse_ini(self, retries=3, sleep_sec=0.05):
        """对 ini 的解析做短时重试，避免半写入"""
        for _ in range(max(1, int(retries))):
            ok = (self._extractor.load_file() and
                  self._extractor.parse_block_mapping() and
                  self._extractor.parse_stock_data())
            if ok:
                return True
            time.sleep(sleep_sec)
        return False

    def _parse_custom_codes(self, path):
        """尝试直接解析 custom_block/<block_id> 文件里的6位代码"""
        try:
            with open(path, "rb") as f:
                raw = f.read()
            if HAS_CHARDET:
                enc = (chardet.detect(raw).get("encoding") or "gbk")
            else:
                enc = "gbk"
            text = raw.decode(enc, errors="replace")
            # 抓取所有6位数字代码
            import re as _re
            codes = _re.findall(r'(?<!\d)(\d{6})(?!\d)', text)
            codes = list({c for c in codes if len(c) == 6 and c.isdigit()})
            return self._format_with_market(codes)
        except Exception:
            return []

    def _try_parse_custom_codes(self, path, retries=5, sleep_sec=0.05):
        for _ in range(max(1, int(retries))):
            codes = self._parse_custom_codes(path)
            if codes:
                return codes
            time.sleep(sleep_sec)
        return []

    def _classify_path(self, path):
        """返回 'ini' | 'custom' | None"""
        try:
            n = os.path.normcase(os.path.abspath(path))
            if n == self._norm_ini:
                return "ini"
            # 直接命中已知 custom 文件
            if self._norm_custom and n == self._norm_custom:
                return "custom"
            # 尝试基于路径推断 custom_block/<digits>
            base_dir = os.path.dirname(self._abs_path) or "."
            custom_dir = os.path.normcase(os.path.abspath(os.path.join(base_dir, "custom_block")))
            if n.startswith(custom_dir):
                # 末尾文件名若是纯数字，则也视为目标（同名说明是同一 block）
                name = os.path.basename(n)
                if name.isdigit():
                    # 若未建立映射，记录下来作为候选
                    self._custom_block_path = os.path.join(custom_dir, name)
                    self._norm_custom = os.path.normcase(self._custom_block_path)
                    self._block_id = name
                    return "custom"
        except Exception:
            pass
        return None

    def _consolidated_refresh(self):
        """稳定窗后合并数据源，减少一次操作被拆分为多次新增/删除的误报"""
        try:
            # 1) 解析 ini（权威来源）
            codes_ini = []
            if self._try_parse_ini(retries=4, sleep_sec=0.05):
                self._update_block_id_and_custom_path()
                codes_ini = self._get_codes_from_extractor_silent()

            # 2) 解析 custom（备用来源）
            codes_custom = []
            target_custom = self._last_custom_change_path or self._custom_block_path
            if target_custom:
                codes_custom = self._try_parse_custom_codes(target_custom)

            # 3) 选择最终列表：优先 ini，ini 为空则用 custom
            codes = codes_ini if codes_ini else codes_custom

            prev = self._last_codes or []
            if self._last_codes is None or codes != self._last_codes:
                added = sorted(set(codes) - set(prev))
                removed = sorted(set(prev) - set(codes))
                self._last_codes = codes
                try:
                    self.on_update(codes, added, removed)
                except Exception as e:
                    print(f"回调异常: {e}")
        except Exception as e:
            print(f"刷新失败: {e}")
        finally:
            self._pending_sources.clear()
            self._last_custom_change_path = None
            self._timer = None

    def _schedule_refresh(self):
        """在稳定窗后合并处理，避免抖动"""
        try:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._stabilize_window, self._consolidated_refresh)
            self._timer.daemon = True
            self._timer.start()
        except Exception:
            # 退化为立即刷新
            self._consolidated_refresh()

    def _mark_changed(self, source, change_path=None):
        """记录变化来源并启动稳定窗合并"""
        if source:
            self._pending_sources.add(source)
        if source == "custom" and change_path:
            self._last_custom_change_path = change_path
        self._schedule_refresh()

    def start(self):
        # 启动时尽力先获取一次列表并回调，然后进入监听
        codes = []
        for _ in range(30):
            try:
                ok = (self._extractor.load_file() and
                      self._extractor.parse_block_mapping() and
                      self._extractor.parse_stock_data())
                if ok:
                    self._update_block_id_and_custom_path()
                    codes = self._get_codes_from_extractor_silent()
                    if not codes and self._custom_block_path:
                        # 解析 custom_block 作为兜底
                        codes = self._try_parse_custom_codes(self._custom_block_path)
            except Exception:
                pass
            if codes:
                break
            time.sleep(0.1)

        prev = self._last_codes or []
        if self._last_codes is None or codes != self._last_codes:
            added = sorted(set(codes) - set(prev))
            removed = sorted(set(prev) - set(codes))
            self._last_codes = codes
            try:
                self.on_update(codes, added, removed)
            except Exception as e:
                print(f"回调异常: {e}")

        # 初始化签名（避免启动就触发一次无意义更新）
        self._sig_ini = self._file_signature(self._abs_path)
        if self._custom_block_path:
            self._sig_custom = self._file_signature(self._custom_block_path)

        # 进入监听
        if HAS_WATCHDOG and not self.use_polling:
            self._start_watchdog()
        else:
            self._start_polling()

    def stop(self):
        self._stop = True
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2)
            except Exception:
                pass

    def _start_polling(self):
        def loop():
            while not self._stop:
                try:
                    changed = False
                    src = None
                    sig_ini = self._file_signature(self._abs_path)
                    if sig_ini != self._sig_ini:
                        changed = True
                        src = "ini"
                        self._sig_ini = sig_ini

                    if self._custom_block_path:
                        sig_custom = self._file_signature(self._custom_block_path)
                        if sig_custom != self._sig_custom:
                            changed = True
                            src = "custom"
                            self._sig_custom = sig_custom

                    if changed:
                        self._mark_changed(src, change_path=(self._custom_block_path if src == "custom" else None))
                except Exception:
                    pass
                time.sleep(self.interval)
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _start_watchdog(self):
        class _Handler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer
                self._last = 0.0

            def _maybe(self, path):
                try:
                    src = self.outer._classify_path(path)
                    if src in ("ini", "custom"):
                        now = time.time()
                        if now - self._last >= self.outer.debounce:
                            self._last = now
                            self.outer._mark_changed(source=src, change_path=path if src == "custom" else None)
                except Exception:
                    pass

            def on_modified(self, event):
                self._maybe(event.src_path)

            def on_created(self, event):
                self._maybe(event.src_path)

            def on_moved(self, event):
                # 写临时文件后替换的模式
                self._maybe(getattr(event, "dest_path", event.src_path))
                self._maybe(event.src_path)

        # 监听 ini 所在目录，递归处理（以捕获 custom_block 下的变化）
        base = os.path.dirname(self._abs_path) or "."
        handler = _Handler(self)
        self._observer = Observer()
        self._observer.schedule(handler, base, recursive=True)
        self._observer.start()
if __name__ == "__main__":
    # 监听示例（Ctrl+C 退出）
    ini_path = INI_PATH  # 可在文件顶部配置
    target_block = TARGET_BLOCK  # 可在文件顶部配置

    def on_update(codes, added, removed):
        ts = time.strftime("%H:%M:%S")
        #if added:
            #print(f"[{ts}] 新增: " + "、".join(added))
        #if removed:
            #print(f"[{ts}] 移除: " + "、".join(removed))
        if codes:
            formatted = "、".join(codes)
            print(f"[{ts}] {target_block}板块更新为：{formatted}")

    # interval=0.2, debounce=0.05 可按需再调小/调大
    monitor = StockBlockMonitor(
        ini_path,
        target_block,
        on_update,
        interval=POLLING_INTERVAL,
        debounce=DEBOUNCE_SECONDS,
        stabilize_window=STABILIZE_WINDOW,
        use_polling=USE_POLLING,
    )
    monitor.start()
    print("开始监听，按 Ctrl+C 退出。")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        monitor.stop()
        print("已停止监听。")
