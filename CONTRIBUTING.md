# 参与贡献

欢迎提 Issue 和改进。

## 本地开发

```bash
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py
```

## 提交前

```bash
node --test tests/render.test.mjs
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python examples/minimal/build.py --scale 1     # 端到端快速跑一遍
```

- 新脚本：路径从命令行传入，不写死本机路径；检查类脚本最后一行打印 `GREEN` / `RED`，退出码 0 / 1。
- 不提交任何音频、视频、3D 模型文件，也不提交品牌 logo、商店截图、真人照片（`tests/test_repo_hygiene.py` 会查一部分）。
- 文档用简体中文，句子短、少术语。
