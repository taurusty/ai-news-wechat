# HTML修复说明

## 问题1：标题混乱

**现象**：HTML中除了三个栏目标题（每日资讯、科创头条、学术动态），还有其他多余的标题

**原因**：LLM生成的markdown中包含 `#` 和 `##` 标题，被渲染成了额外的 h1 和 h2 标签

**解决方案**：
修改 `app/render/wechat_html.py` 中的 `_render_paragraphs()` 函数：
- 跳过所有 `# ` 和 `## ` 开头的行
- 只保留栏目标题（每日资讯、科创头条、学术动态）

```python
# 跳过 markdown 中的标题（# 和 ##），只保留栏目标题
if line.startswith("# ") or line.startswith("## "):
    # 不渲染，直接跳过
    continue
```

---

## 问题2：学术动态编号全是1

**现象**：10条论文的编号显示为：1, 1, 1, ... 而不是 1, 2, 3, ...

**根本原因**：
1. LLM生成的markdown在列表项之间插入了其他段落
2. 这导致HTML中生成了多个独立的 `<ol>` 标签
3. 每个新的 `<ol>` 都会重置编号为1

**示例问题markdown**：
```markdown
1. 第一条
2. 第二条
3. 第三条

这是中间的段落（问题！）

4. 第四条（这会重新开始一个<ol>，编号变回1）
5. 第五条（显示为2）
```

**解决方案**：
修改 `app/llm/prompts.py` 中的三个提示词，强制要求：
1. **列表必须连续**：所有列表项之间不能插入任何其他段落、标题或分隔内容
2. **明确递增编号**：1. 2. 3. 4. 5. 6. 7. 8. 9. 10.
3. **不要在列表中间插入总结**

**修改位置**：
- `build_arxiv_prompt()` - 学术动态
- `build_daily_summary_prompt()` - 每日资讯
- `build_starmarket_prompt()` - 科创头条

---

## 修改的文件

1. **app/render/wechat_html.py**
   - `_render_paragraphs()` 函数：跳过 # 和 ## 标题

2. **app/llm/prompts.py**
   - `build_arxiv_prompt()`：强制连续列表
   - `build_daily_summary_prompt()`：强制连续列表
   - `build_starmarket_prompt()`：强制连续列表

---

## 测试

修复后，再次运行生成器：

```powershell
python -m app.main --date today
```

检查生成的HTML：
1. ✅ 只有三个栏目标题（每日资讯、科创头条、学术动态）
2. ✅ 学术动态的10条编号为 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

---

**修复完成时间**：2026-01-13  
**状态**：✅ 已修复
