# API 接口测试文档

## 注册接口检查清单

### 1. 接口路径
- **完整路径**: `POST /api/auth/register`
- **路由前缀**: `/api/auth` (定义在 `api/auth_api.py` 第23行)
- **路由方法**: `@router.post("/register")` (定义在第45行)

### 2. 接口功能
- 用户注册
- 验证用户名和密码格式
- 检查用户名和邮箱是否已存在
- 密码加密存储

### 3. 请求格式
```json
{
  "username": "testuser",
  "password": "123456",
  "email": "test@example.com"  // 可选
}
```

### 4. 响应格式
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "is_active": true,
  "is_superuser": false,
  "create_time": "2025-01-01T00:00:00",
  "update_time": "2025-01-01T00:00:00"
}
```

### 5. 测试方法

#### 使用 curl 测试:
```bash
curl -X POST "http://localhost:3000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "123456",
    "email": "test@example.com"
  }'
```

#### 使用浏览器测试:
1. 打开 `http://localhost:3000/docs` (FastAPI 自动生成的 API 文档)
2. 找到 `POST /api/auth/register` 接口
3. 点击 "Try it out"
4. 输入测试数据并执行

#### 使用前端页面测试:
1. 访问 `http://localhost:3000/login`
2. 切换到"注册"标签
3. 填写注册信息并提交

### 6. 常见问题排查

#### 问题1: 404 Not Found
**可能原因**:
- 服务器未启动
- 路由未正确注册
- 静态文件挂载顺序问题

**解决方法**:
1. 确认服务器已启动: `python main.py`
2. 检查路由注册顺序（main.py 中 API 路由应在静态文件之前）
3. 访问 `http://localhost:3000/docs` 查看所有注册的路由

#### 问题2: 500 Internal Server Error
**可能原因**:
- 数据库连接失败
- 缺少依赖包
- 代码逻辑错误

**解决方法**:
1. 检查数据库配置 (`config.py`)
2. 安装依赖: `pip install -r requirements.txt`
3. 查看服务器日志获取详细错误信息

#### 问题3: 400 Bad Request
**可能原因**:
- 用户名已存在
- 邮箱已被注册
- 输入格式不符合要求

**解决方法**:
- 查看返回的错误信息
- 检查用户名和密码长度要求

### 7. 代码文件位置
- **路由定义**: `api/auth_api.py` (第45-73行)
- **业务逻辑**: `services/user_service.py` (第18-35行)
- **数据访问**: `repositories/user_repo.py` (第27-43行)
- **路由注册**: `main.py` (第40行)

### 8. 验证路由是否注册成功
启动服务器后，访问以下URL查看所有路由:
- API文档: `http://localhost:3000/docs`
- OpenAPI JSON: `http://localhost:3000/openapi.json`

在 OpenAPI JSON 中搜索 `"/api/auth/register"` 确认路由存在。

