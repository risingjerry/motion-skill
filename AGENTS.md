# AGENTS.md — 给 AI 助手的说明

这个仓库本身就是一个 Agent Skill（入口 `SKILL.md`）：用代码做动效短片（产品发布片、App 宣传片、logo 动画、3D 产品镜头、讲解动效、接实拍的转场），渲染成 4K。
做片子时按 `SKILL.md` 的流程走；改这个仓库的代码时按下面的规矩。

## 安装

```bash
npm install                                   # 只装 playwright-core（不下载浏览器，默认用本机 Chrome）
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows：.venv\Scripts\pip
.venv/bin/python scripts/doctor.py            # 检查依赖；--json 给机器读
```

有 `.venv` 时，Python 脚本一律用 `.venv/bin/python`（Windows：`.venv\Scripts\python`）运行。

## 测试

```bash
node --test tests/render.test.mjs             # 渲染脚本（没有 Chrome 时自动跳过）
.venv/bin/python -m unittest discover -s tests -v   # 声音、检查脚本、Blender（没有 blender 时跳过）、仓库卫生
.venv/bin/python examples/minimal/build.py --scale 1   # 端到端快速跑一遍示例（1080p）
```

## 脚本的约定

- 检查类脚本（`layout_check.py`、`seam_check.py`、`blender/motion_check.py`）：最后一行打印 `XXX GREEN` 或 `XXX RED`，退出码 0 = 绿、1 = 红、2 = 用法错误。
- `render.mjs` 出片时同时写 `<片名>.beats.json`（节拍表），`audio/mix.py` 用 `beat:名字` 引用。
- `doctor.py --json` 输出 `{"ready": bool, "checks": [...]}`。
- 所有路径都从命令行传入，不写死任何本机路径；可选依赖缺失时给出安装提示并以非 0 退出，不抛堆栈。

## 不要做

- 不要往仓库里放有版权的素材：品牌 logo、商店截图、厂商 3D 模型、音效库/音乐文件、真人照片或视频。示例只用自己画的 SVG 和代码合成的声音。
- 不要在代码、文档、测试里写本机绝对路径、账号、密钥（`tests/test_repo_hygiene.py` 会查）。
- 不要同时跑多个 4K 渲染或 Blender 渲染。
- 不要替用户调用付费服务（配音、AI 音乐等），除非用户明确要求。
