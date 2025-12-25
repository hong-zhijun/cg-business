# ChatGPT Team 账号池自动管理系统 - Public 管理权限开发任务清单

## 1. 数据库变更 (database.py)

-   [x] **Teams 表结构变更**
    -   [x] 在 `init_db()` 中为 `teams` 表添加 `allow_public_manage` 字段 (BOOLEAN, 默认 0/False)
-   [x] **Team 类方法更新**
    -   [x] 更新 `update_team_info()` 方法，支持更新 `allow_public_manage` 字段
    -   [x] 更新 `create` 方法，支持初始化 `allow_public_manage` 字段
    -   [x] 更新 `get_all` / `get_by_id` 等查询方法，确保返回 `allow_public_manage` 字段

## 2. 后端接口开发 (app_new.py)

-   [x] **新增 Public 端操作接口**
    -   [x] `POST /api/public/team/kick`: 踢出成员 (需校验 `team_access_auth` 和 `allow_public_manage`)
    -   [x] `POST /api/public/team/revoke`: 撤销邀请 (需校验 `team_access_auth` 和 `allow_public_manage`)
-   [x] **更新现有接口**
    -   [x] `GET /api/public/teams`: 返回数据中包含 `allow_public_manage` 字段
    -   [x] `POST /api/admin/team/update`: 支持接收并更新 `allow_public_manage` 字段

## 3. 前端开发 (Templates & TailwindCSS)

-   [x] **Admin 端 (templates/modals/team_details.html)**
    -   [x] 在 Team 详情/编辑弹窗中增加 "开放管理权限" Toggle 开关
    -   [x] 保存操作适配后端接口，提交开关状态
-   [x] **Public 端 (templates/public_teams.html)**
    -   [x] **列表展示**: 可选增加小图标提示 "可管理"
    -   [x] **成员弹窗 (membersModal)**:
        -   [x] 根据 `allow_public_manage` 字段判断是否显示操作按钮
        -   [x] 若 `True`:
            -   [x] 已加入成员行末显示红色 "踢出" 按钮
            -   [x] 邀请中成员行末显示橙色 "撤销" 按钮
        -   [x] 按钮点击事件处理: 弹出 Confirm 确认框，确认后调用对应 Public 接口

## 4. 验证与测试

-   [ ] **功能测试**
    -   [ ] Admin 端开启/关闭权限，数据库正确更新
    -   [ ] Public 端未开启权限时，无法看到按钮，API 拒绝请求
    -   [ ] Public 端开启权限时，可以看到按钮，并成功执行踢人/撤销操作
-   [ ] **安全测试**
    -   [ ] 尝试在未开启权限的 Team 上直接调用 Public 踢人接口 (应返回 403)
