// 引入所需模块
const express = require('express');
const path = require('path');

// 创建Express应用
const app = express();

// 设置端口号
const PORT = process.env.PORT || 3000;

// 配置静态文件服务
app.use(express.static(path.join(__dirname, 'public')));

// 设置路由
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 处理404错误
app.use((req, res) => {
  res.status(404).send('页面未找到');
});

// 启动服务器  node server.js
app.listen(PORT, () => {
  console.log(`服务器运行在 http://localhost:${PORT}`);
});