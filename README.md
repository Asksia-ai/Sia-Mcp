# AskSia MCP plugin

本仓库向 Claude 和 ChatGPT 提供 AskSia 插件：三个学习 skills、MCP 接入配置、图标及安装包。题库、词卡、判分和复习进度由已有 AskSia 后端提供。

**当前是 preview 初步交付，用于同事安装和验收；生产发布与官方市场上架尚未包含在本次交付中。** 网页／桌面聊天卡片等已暂停的工作不随本插件恢复。

原文 D 的交付形式是 **Claude 仓库插件市场入口 + ChatGPT portable ZIP + 两端共用的三个 skills**。本次新增的 Claude preview ZIP 用于省去测试同事手改服务地址；ChatGPT 的 `-install.zip` 是适配桌面本地市场的辅助外壳，二者不改变原文交付范围，也不代表所有用户只有这一种安装方式。

## 1. 先选对环境和安装包

| 用途 | MCP 服务 | 使用方式 |
| --- | --- | --- |
| 本次测试 | `https://api1.asksia.ai/mcp` | 使用名称含 `preview` 的安装包 |
| 正式发布 | `https://api.asksia.ai/mcp` | 待生产服务、授权页和数据准备完成并放行后使用 |

本次 preview 浏览器登录授权页位于 `https://needsitereview.asksia.ai/mcp/authorize`，应由客户端发起授权后自动跳转，不手工拼接授权参数。

| 交付文件 | 给谁使用 | 内容 |
| --- | --- | --- |
| `asksia-claude-preview.zip` | Claude Code 使用者 | 已配置 api1 的 Claude 插件市场、插件、三个 skills 和 `INSTALL.txt` |
| `asksia-chatgpt-preview-install.zip` | ChatGPT 桌面端安装验收 | 本地插件市场、完整插件、三个 skills 和 `INSTALL.txt` |
| `asksia-chatgpt-preview.zip` | 已有兼容导入流程的接收方 | 原始 portable 插件文件；不含本地市场外壳 |

从交付附件领取 ZIP，或按第 7 节从源码构建。`dist/` 是本地产物目录，ZIP 不随 Git 源码提交。**源码中的两份 MCP 配置保留正式地址；仅克隆 `preview` 分支并不会自动把服务切到 api1。** 打包脚本会为测试包预置正确地址，测试同事无需编辑 JSON。

准备一个团队安排的 AskSia 测试账号。当前六个工具都要求 credits 余额大于 0；读取存量题目／词卡、判分和复习不调用 AskSia 模型，也不扣模型 credits。可用考试与内容以该账号的后端返回为准。

## 2. Claude Code 安装

需要支持插件和 OAuth 的 Claude Code。安装包使用 `.claude-plugin/`、`.mcp.json` 及共享的 `skills/`，与 ChatGPT 的安装入口不同。

1. 把 `asksia-claude-preview.zip` 解压到运行 Claude Code 的电脑，得到 `asksia-claude-preview` 目录；安装期间保留这个目录。
2. 在 **Claude Code 交互会话**中执行下面的命令，将示例路径替换成实际解压目录：

   ```text
   /plugin marketplace add "/absolute/path/asksia-claude-preview"
   /plugin install asksia@asksia-preview
   ```

3. 按客户端提示重新加载插件或新开会话。运行 `/mcp`，找到插件提供的 AskSia 服务；若提示认证，选择 Authenticate 并在浏览器登录、同意授权。
4. 确认服务使用 `https://api1.asksia.ai/mcp`，再按第 5 节开始测试。

看到三个 skills 只说明插件已加载；看到工具实际调用成功，才说明服务连接可用。若之前手动添加过同一个测试 MCP，完整插件验收时先停用重复连接，避免模型调用到另一套入口。

## 3. ChatGPT 桌面端安装

这是一条已准备好的**本地市场安装路径**，不是所有 ChatGPT 账号都能直接上传 ZIP 的承诺，也不是要求所有正式用户必须安装 Codex CLI。

该路径需要兼容的 ChatGPT 桌面客户端，以及支持 `codex plugin marketplace add` 的 Codex CLI。命令只用于注册插件来源，之后仍在 ChatGPT 桌面端安装和使用。

1. 将 `asksia-chatgpt-preview-install.zip` 解压到运行 ChatGPT 的 **Mac 本机**，得到 `asksia-chatgpt-preview-install` 目录；不要把本次 Mac 安装命令运行在 SSH 开发服务器上。
2. 在 Mac 终端进入该目录，执行：

   ```bash
   codex plugin marketplace add .
   ```

3. 重启 ChatGPT 桌面端，在 Plugins 中选择 **AskSia Preview** 来源，安装 **AskSia**（标识为 `asksia@asksia-preview`）。
4. 如果客户端提示连接或认证，在浏览器完成 AskSia 登录授权。保持客户端开启，成功后返回客户端新建对话并启用插件。
5. 完整插件验收时，先停用之前手动添加的重复 AskSia MCP 连接，然后按第 5 节测试。

注册期间保留解压目录。若 `codex` 命令不存在，或没有 `plugin marketplace add` 子命令，先由安装负责人按客户端官方说明准备对应 CLI；不要把安装包里的配置手动粘到其他应用配置文件中。

### 更新已经安装的测试包

先在客户端卸载 **`asksia-preview` 来源内的 AskSia 插件**，再用新包替换原解压目录的文件并重新安装。路径不变时可沿用已注册来源；路径改变时，先移除旧的 `asksia-preview` 来源，再按上面的步骤添加新目录。只处理本次测试来源，不改其他已安装插件或正式来源。重新安装后核对版本和服务地址；单纯替换 ZIP 或重启客户端不等于已更新安装缓存。

## 4. 网页端及只测 MCP 服务

原需求还列了 claude.ai 自定义连接器、ChatGPT 网页的自定义 MCP／开发者入口。这些入口需使用有相应权限的账号，按客户端当前界面添加 `https://api1.asksia.ai/mcp`，选择 OAuth／自动发现并完成授权。

手动添加 MCP 可以测试六个工具，**不会自动安装本仓库的三个 skills**。网页入口的工具验收和完整插件安装验收应分别记录，不把桌面连接成功当成所有端均已通过。正式目录搜索、上架审核和各平台专属卡片 UI 不属于本次初步交付。

## 5. 如何测试

### 六个工具的最小验收

在 preview 上进行；提交答案和记录复习会写入该测试账号的学习记录。每一步查看客户端展开的真实工具调用、参数与返回值，不能只看模型说“已完成”。

下面用 `sat`、`toefl` 举例；按测试账号实际开放的考试调整。空计划不代表不能练题，空题库／空词卡也不能由模型编造补齐。

| 步骤 | 可以发送给模型的请求 | 应看到的结果 |
| --- | --- | --- |
| 1. 查计划 | `请调用 AskSia 的 get_my_exams 查询我的考试计划；没有计划就如实说明，不创建新计划。` | 调用 `get_my_exams`；返回已有计划或空列表 |
| 2. 取一道题 | `请调用 AskSia 的 get_practice_questions，exam=sat、count=1，等我回答后再判分，不提前给答案。` | 调用 `get_practice_questions`，`exam=sat`、`count=1`；保留题目的 handle |
| 3. 提交答案 | 根据实际题型作答；选择题可以说 `我选 B，请提交这道题的答案。` | 调用 `submit_answer`，使用同一 handle；显示服务端的正误、分数及解析 |
| 4. 记录复习前进度 | `请调用 get_vocab_progress 查看我的托福词汇进度。` | `exam=toefl`；记录 `mastered`、`reviewing`、`due_today` |
| 5. 取一张词卡 | `请调用 AskSia 的 get_vocab_cards，exam=toefl、count=1，先让我回忆意思。` | 调用 `get_vocab_cards`，`count=1`；先展示词、词性及音标，等待回忆，再按请求展示背面 |
| 6. 保存并回查 | 明确说 `这张记住了，请记录。` 或 `这张没记住，请记录。`，然后再次查询词汇进度 | `record_vocab_review` 使用本张 handle 和对应布尔值；随后 `get_vocab_progress` 与记录结果中的进度一致 |

选择题答案的工具参数是从 0 开始的选项索引，由模型按实际选项顺序转换。其他题型使用接口声明的答案结构，不强行转换成单选题。复习采用 FSRS，“记住一次”不一定立即增加 `mastered`，按服务端结果核对即可。

### 三个 skills 的行为验收

完整插件安装后，再通过客户端的插件／skill 入口选择 AskSia 并做下面的检查。只添加 MCP 服务的网页测试不包含此项。

| Skill | 可以发送的请求 | 观察点 |
| --- | --- | --- |
| `getting-started` | `请使用 AskSia 的 getting-started，介绍能做什么，并带我开始。` | 能介绍可做的学习活动；需要认证时引导客户端登录，不让用户在聊天中输入密码或令牌 |
| `exam-practice` | `请使用 AskSia 的 exam-practice 带我练一道 SAT 题。` | 一次一题，等待作答，调用服务端判分后再讲解；不自行充当已保存的判分结果 |
| `vocab-review` | `请使用 AskSia 的 vocab-review 带我复习一个托福单词。` | 先回忆再翻卡；依据用户明确的“记住／没记住”反馈记录，不擅自替用户评分 |

图片为空时继续展示文字卡；整词一段、同义词为空均是允许内容。整卡图为空时不提供该图的保存／分享入口。

再做三个边界检查：

- 首次连接时取消授权，本次未批准的请求不能被报告为连接成功；取消新请求不等于撤销已有连接。请求过期后可从客户端重新发起。
- 网络异常需要重试提交时，使用同一 handle 和原答案／反馈；同一 handle 不应重复判分或重复推进复习。
- 余额不足或被限流时显示服务返回的说明，暂停自动重试；不自动切换账号、环境或编造内容。

### 反馈格式

请记录：**客户端及版本、安装包名称、测试时间（含时区）、使用的考试、复现步骤、实际工具名／参数、预期结果和实际结果**。附工具返回或错误截图；账号由团队内部单独标识。

共享记录中删去密码、Cookie、访问／刷新令牌，以及完整授权／回调 URL 中的 `code`、`state` 等参数。不要把截图里的旧授权链接转给别人继续使用。

## 6. 常见问题

| 现象 | 处理方式 |
| --- | --- |
| 插件来源或 AskSia 不显示 | Claude 使用 `asksia-claude-preview.zip`，ChatGPT 桌面使用 `asksia-chatgpt-preview-install.zip`；核对解压目录是否保留、CLI 是否支持相应命令，重新加载客户端后查看来源 |
| 已看到 skills，但没有可用工具 | 检查 AskSia 服务是否完成授权、是否连接 api1；实际调用 `get_my_exams` 确认 |
| 授权页报 `invalid_client`／`invalid_request` | 从客户端重新生成链接，并提供去除敏感参数的错误截图给开发；不要手动修改 client_id 或回跳地址 |
| 回到 `127.0.0.1`／`localhost` 时连接被拒绝 | 这是桌面／CLI 的本机回调地址；保持客户端开启，关闭旧标签页，从客户端重新发起授权 |
| 返回空计划、空题目或空词卡 | 区分账号无计划、考试未开放、素材未齐或可用题已耗尽；保留返回结果给内容／开发负责人核对 |
| 返回余额不足或 `RATE_LIMITED` | 按返回说明处理。当前按账号每分钟最多 30 次调用、每小时最多取 60 道练习题；不要自动循环重试 |

## 7. 从源码自检与构建（开发者）

以下命令从**仓库 checkout 根目录**运行。安装包不包含构建脚本；拿到 ZIP 的测试同事不需要执行本节。

```bash
git clone --branch preview https://github.com/Asksia-ai/Sia-Mcp.git
cd Sia-Mcp
python3 scripts/validate-package.py
python3 -m unittest discover -s tests -p 'test_*.py'
bash scripts/build-chatgpt-zip.sh
```

沿用原需求中的脚本入口名称；现在默认生成第 1 节的三个 preview ZIP。脚本只打包明确列出的文件，不包含 `.env`、Git 历史、上传凭据或本地客户端配置，也不修改源码中的正式服务地址。

Claude 清单还需用支持当前插件字段的 CLI 校验：

```bash
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

较旧 CLI 若不识别当前清单字段，先核对其支持范围，不通过删掉必需字段或改写用户全局配置来绕过。

**只有生产发布放行后**才构建和分发正式包：

```bash
bash scripts/build-chatgpt-zip.sh --env production
```

生成的本地市场正式包使用 `asksia-production` 来源，与 `asksia-preview` 分开。正式服务发布后，Claude 还可直接从仓库市场安装：

```text
/plugin marketplace add Asksia-ai/Sia-Mcp
/plugin install asksia@asksia
```

这条仓库安装入口使用源码中的生产地址；本轮 preview 测试使用前面的测试包。

## 8. 已验证与待验收

截至 2026-11-20，已记录以下验证：

| 验证项 | 结果与范围 |
| --- | --- |
| 安装包自检 | 9 项检查通过，覆盖产物结构、preview／production 地址、文件选择、重复构建及输出保护 |
| Claude Code 2.1.329 | 使用临时配置，对实际 preview 包完成清单校验、添加市场、安装、列表和详情检查；发现三个 skills 与一个 api1 MCP 服务，未改用户全局配置 |
| Codex CLI 0.153.4 | 只读识别实际 ChatGPT 安装包中的 `asksia@asksia-preview` 和认证策略；这不是用户 Mac 上的完整安装或 OAuth 验收 |
| 后端 | 170 项 MCP 隔离测试通过；隔离环境中完成真实 Django 登录、Cookie／CSRF、PKCE 换令牌及六工具发现 |
| 前端 | 17 个浏览器场景通过，包括自动填充、验证码注册和取消／同意防重复处理 |
| preview 线上入口 | Claude 授权请求正常 302 跳转，前端页面及请求信息接口返回 200；本次入口检查未输入账号密码或批准授权 |
| 已有人工记录 | ChatGPT 桌面手动 MCP 连接已有一次真实授权成功记录 |

完整插件仍需要接收方在目标客户端完成安装、授权、六工具与三个 skills 的业务验收。Claude CLI、ChatGPT 桌面完整插件、claude.ai 网页入口、ChatGPT 网页入口分别记录；本地 CLI 能发现一个包、显示三个 skills、自动化检查通过，都不代表所有客户端已通过验收。

Google、Microsoft、Apple 三种现有第三方登录的真实账号流程也需由同事完成验收；不要将入口参数或模拟回跳检查当成真实第三方登录已通过。

生产发布、生产内容回读和官方市场上架不因本次 ZIP 交付自动完成。首发考试／词卡范围由内容交付和实际可用数据确认。

## 9. 数据与隐私

OAuth 授权对应用户的 AskSia 账号和 `progress.read`、`practice`、`vocab` 权限。用户在 AskSia 浏览器页面登录，客户端管理授权回跳与令牌；安装包不含用户密码、API key 或 client secret。

外部 AI 客户端会收到所请求的考试／进度、题目／词卡及提交结果。AskSia 保存练习作答、词汇复习和必要的工具活动；工具输出使用不透明 handle 关联提交，不暴露数据库数字 ID 和时间戳。练习工具不创建或推进学习计划。外部客户端还可能按其自身设置保留聊天内容。

插件不安装 hooks、后台上传器或本地文件采集脚本。可在客户端停用／移除连接；停用不等同于删除既有学习记录。

- [AskSia 隐私政策](https://www.asksia.ai/policies/privacy)
- [使用条款](https://www.asksia.ai/policies/termofuse)
- [支持渠道](https://www.asksia.ai/contact-us)

图标复用 AskSia 现有品牌素材；本仓库未授予开源许可，见 `LICENSE`。

## 官方接入说明

- [Claude 插件市场](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude MCP 认证](https://code.claude.com/docs/en/mcp#authenticate-with-remote-mcp-servers)
- [OpenAI 插件打包与本地安装](https://developers.openai.com/plugins/build/plugins)
- [OpenAI OAuth](https://developers.openai.com/plugins/build/auth)
- [OpenAI 连接与插件测试](https://developers.openai.com/plugins/deploy/connect-chatgpt)
