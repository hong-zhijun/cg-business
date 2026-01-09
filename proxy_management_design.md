# 代理地址管理功能开发流程设计

本设计旨在为现有系统增加代理地址管理功能，方便管理员维护和管理代理地址列表。

## 1. 数据库设计与创建

第一步是在数据库中创建用于存储代理地址的表。

**目标**: 创建 `proxy_addresses` 表。

**字段设计**:

| 字段名        | 类型      | 说明                       |
| :------------ | :-------- | :------------------------- |
| `id`          | INTEGER   | 主键，自增                 |
| `protocol`    | TEXT      | 协议 (如 `http`, `socks5`) |
| `ip`          | TEXT      | IP 地址                    |
| `port`        | INTEGER   | 端口号                     |
| `username`    | TEXT      | 用户名 (可选)              |
| `password`    | TEXT      | 密码 (可选)                |
| `description` | TEXT      | 备注说明                   |
| `created_at`  | TIMESTAMP | 创建时间，默认为当前时间   |
| `updated_at`  | TIMESTAMP | 更新时间，默认为当前时间   |

**实施步骤**:

1.  修改 `database.py` 文件中的 `init_db` 函数，添加创建 `proxy_addresses` 表的 SQL 语句。
2.  在 `database.py` 中新增 `ProxyAddress` 类，封装数据库操作方法：
    -   `get_all()`: 获取所有代理地址。
    -   `add(protocol, ip, port, username, password, description)`: 新增代理地址。
    -   `update(id, protocol, ip, port, username, password, description)`: 更新代理地址。
    -   `delete(id)`: 删除代理地址。

---

## 2. 后端接口开发

第二步是编写后端 API 接口，供前端调用以实现增删改查功能。

**目标**: 在 `app_new.py` 中添加相关路由和处理逻辑。

**接口列表**:

1.  **获取代理列表**

    -   **方法**: `GET`
    -   **路径**: `/api/admin/proxy-addresses`
    -   **权限**: 管理员 (`@admin_required`)
    -   **返回**: `{ "success": True, "data":List[Proxy] }`

2.  **新增代理**

    -   **方法**: `POST`
    -   **路径**: `/api/admin/proxy-addresses`
    -   **参数**: `{ "protocol": "http", "ip": "127.0.0.1", "port": 7890, "username": "", "password": "", "description": "..." }`
    -   **权限**: 管理员 (`@admin_required`)
    -   **逻辑**: 校验必填项 (protocol, ip, port)，调用 `ProxyAddress.add`。

3.  **修改代理**

    -   **方法**: `PUT`
    -   **路径**: `/api/admin/proxy-addresses/<int:id>`
    -   **参数**: `{ "protocol": "...", "ip": "...", "port": ..., "username": "...", "password": "...", "description": "..." }`
    -   **权限**: 管理员 (`@admin_required`)
    -   **逻辑**: 调用 `ProxyAddress.update`。

4.  **删除代理**
    -   **方法**: `DELETE`
    -   **路径**: `/api/admin/proxy-addresses/<int:id>`
    -   **权限**: 管理员 (`@admin_required`)
    -   **逻辑**: 调用 `ProxyAddress.delete`。

---

## 3. 前端页面功能汇总新增代理管理

第三步是在 Admin 页面的“功能汇总”中添加入口，并实现管理界面。

**目标**: 修改 `templates/admin_new.html`。

**实施步骤**:

1.  **添加入口按钮**:

    -   在 `featureSummaryModal` (功能汇总模态框) 的内容区域中，新增一个“代理管理”的按钮或卡片。
    -   点击该按钮触发打开新的“代理管理模态框” (`proxyManagementModal`)。

2.  **创建代理管理模态框 (`proxyManagementModal`)**:

    -   **布局**:
        -   **头部**: 标题“代理地址管理”和关闭按钮。
        -   **工具栏**: “新增代理”按钮。
        -   **列表区**: 表格展示 ID、协议、IP、端口、用户名、密码(脱敏显示)、备注、创建时间、操作（编辑/删除）。
    -   **新增/编辑弹窗**:
        -   表单字段：
            -   协议 (下拉选择: http/https/socks5)
            -   IP (输入框)
            -   端口 (数字输入框)
            -   用户名 (输入框, 可选)
            -   密码 (输入框, 可选)
            -   备注 (文本域)

3.  **编写前端 JavaScript 逻辑**:
    -   `loadProxyAddresses()`: 调用 GET 接口渲染列表。
    -   `addProxyAddress()`: 弹出表单模态框，收集数据调用 POST 接口。
    -   `editProxyAddress(id)`: 弹出表单模态框回显数据，调用 PUT 接口。
    -   `deleteProxyAddress(id)`: 确认后调用 DELETE 接口。

---

## 总结

按照 **数据库 -> 后端 API -> 前端 UI** 的顺序进行开发，可以确保逻辑清晰，依赖关系顺畅。
