-- stock_list_info 表结构创建SQL
CREATE TABLE IF NOT EXISTS `stock_list_info` (
   `id` int unsigned NOT NULL AUTO_INCREMENT,
   `gp_code` varchar(10) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT '股票代码',
   `gp_name` varchar(11) DEFAULT NULL COMMENT '股票名称',
   `curr_price` varchar(11) DEFAULT NULL COMMENT '现价',
   `change_percent` varchar(11) DEFAULT NULL COMMENT '涨跌幅',
   `change_amount` varchar(11) DEFAULT NULL COMMENT '涨跌额',
   `amplitude` varchar(11) DEFAULT NULL COMMENT '振幅',
   `volume_ratio` varchar(11) DEFAULT NULL COMMENT '量比',
   `low` varchar(11) DEFAULT NULL COMMENT '最低价',
   `high` varchar(11) DEFAULT NULL COMMENT '最高价',
   `open` varchar(13) DEFAULT NULL COMMENT '今开',
   `prev_close` varchar(11) DEFAULT NULL COMMENT '昨收',
   `volume` varchar(11) DEFAULT NULL COMMENT '成交量',
   `amount` varchar(11) DEFAULT NULL COMMENT '成交额',
   `turnover_rate` varchar(11) DEFAULT NULL COMMENT '换手率',
   `pe_ttm` varchar(11) DEFAULT NULL COMMENT '市盈率',
   `pb` varchar(11) DEFAULT NULL COMMENT '市净率',
   `total_market_cap` varchar(11) DEFAULT NULL COMMENT '总市值',
   `float_market_cap` varchar(11) DEFAULT NULL COMMENT '流通市值',
   `create_time` datetime DEFAULT NULL,
   `update_time` datetime DEFAULT NULL,
   PRIMARY KEY (`id`),
   KEY `idx_gp_code` (`gp_code`),
   KEY `idx_gp_name` (`gp_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COMMENT='股票列表信息表';

-- 添加索引（如果表已存在）
ALTER TABLE IF EXISTS `stock_list_info` ADD INDEX IF NOT EXISTS `idx_gp_code` (`gp_code`);
ALTER TABLE IF EXISTS `stock_list_info` ADD INDEX IF NOT EXISTS `idx_gp_name` (`gp_name`);
