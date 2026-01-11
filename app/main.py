import argparse
import asyncio
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

# 尽早加载 .env，避免后续误报“未设置API KEY”
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import yaml


def load_config() -> dict:
    local_cfg = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    if local_cfg.exists():
        cfg_path = local_cfg
    else:
        cfg_path = Path("/app/config/config.yaml")

    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_date(s: str) -> date:
    if s == "today":
        return datetime.now().date()
    return datetime.strptime(s, "%Y-%m-%d").date()


async def run_sources_for_column(column_cfg: dict, global_cfg: dict) -> list:
    """抓取单个栏目的 sources（按栏目配置的source列表）。"""
    from app.sources.registry import create_source

    articles = []
    source_names = [s["name"] for s in column_cfg.get("sources", [])]

    for source_name in source_names:
        src_cfg = next((s for s in column_cfg["sources"] if s["name"] == source_name), None)
        if not src_cfg:
            continue

        try:
            src = create_source(source_name, weight=src_cfg.get("weight", 1.0), enabled=True)
        except Exception as e:
            print(f"WARN: source {source_name} init failed: {e}")
            continue

        try:
            max_items = column_cfg.get("max_items_considered") or global_cfg.get("ranking", {}).get(
                "max_items_considered", 40
            )
            # arXiv 需要更长的超时时间（因为要访问多个 abs 页面）
            timeout_seconds = float(global_cfg.get("timeouts", {}).get("per_source_seconds", 25))
            if source_name == "arxiv_cs_ai":
                timeout_seconds = float(global_cfg.get("timeouts", {}).get("arxiv_source_seconds", 120))
            fetched = await asyncio.wait_for(
                src.fetch_articles(max_items=max_items),
                timeout=timeout_seconds,
            )
            articles.extend(fetched)
            print(f"[INFO ] column='{column_cfg['name']}' source='{source_name}' fetched={len(fetched)}")
        except asyncio.TimeoutError:
            print(f"WARN: source {source_name} timeout, skip")
        except Exception as e:
            print(f"WARN: source {source_name} failed: {e}")
        finally:
            try:
                await src.close()
            except Exception as e:
                print(f"WARN: source {source_name} close failed: {e}")

    return articles


def main():
    from app.utils.progress import step

    parser = argparse.ArgumentParser(description="AI新闻聚合并生成微信公众号HTML")
    parser.add_argument("--date", default="today", help="YYYY-MM-DD or today")
    args = parser.parse_args()

    with step("加载配置"):
        cfg = load_config()

    run_date = parse_date(args.date)
    weekday = run_date.weekday()

    out_base = Path(cfg["output"]["base_dir"]).resolve()
    day_dir = out_base / run_date.isoformat()
    
    # 清空当天目录，避免多次运行触发去重
    if day_dir.exists():
        import shutil
        shutil.rmtree(day_dir)
        print(f"[INFO] 已清空当天输出目录: {day_dir}")
    day_dir.mkdir(parents=True, exist_ok=True)

    # DB
    db_path = Path("./db/articles.sqlite3").resolve()
    from app.storage.db import ArticleDB

    db = ArticleDB(db_path)

    # LLM
    from app.llm.deepseek_client import DeepSeekClient

    client = None
    if os.getenv("DEEPSEEK_API_KEY"):
        client = DeepSeekClient(
            base_url=cfg.get("llm", {}).get("base_url") or "https://api.deepseek.com",
            model=os.getenv(cfg.get("llm", {}).get("model_env", "DEEPSEEK_MODEL")),
        )
    else:
        print("[WARN ] 未设置DEEPSEEK_API_KEY，将跳过LLM写作")

    all_columns_data: List[Dict[str, Any]] = []
    all_source_urls: set[str] = set()

    try:
        for column_cfg in cfg.get("columns", []):
            column_name = column_cfg.get("name", "")

            # 按工作日启用
            enabled_days = column_cfg.get("enabled_weekdays")
            if enabled_days is not None and weekday not in enabled_days:
                print(f"[INFO ] 跳过栏目：{column_name}（weekday={weekday}）")
                continue

            min_items = int(column_cfg.get("min_items", 5))
            max_items = int(column_cfg.get("max_items", 10))

            with step(f"处理栏目：{column_name}"):
                # Step A: 抓取
                articles = asyncio.run(run_sources_for_column(column_cfg, cfg))

                # 记录sources_preview（便于回填）
                try:
                    preview_path = day_dir / f"sources_preview_{column_name}.json"
                    preview_path.write_text(
                        json.dumps([a.to_dict() for a in articles[:200]], ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass

                if not articles:
                    print(f"[WARN ] 栏目 {column_name} 抓取为空")
                    continue

                # Step B: 关键词过滤
                from app.pipeline.filtering import keyword_filter

                filt_cfg = cfg.get("filter", {})
                # 科创热点和学术动态不进行关键词过滤，因为内容都是科技相关的
                if "科创热点" in column_name or "科创头条" in column_name or "学术动态" in column_name:
                    filtered = articles
                    print(f"[INFO] {column_name}跳过关键词过滤，保留 {len(filtered)} 篇")
                else:
                    filtered = keyword_filter(articles, filt_cfg.get("keywords_any", []), filt_cfg.get("keywords_not", []))

                # Step C: 去重
                from app.pipeline.dedup import dedup_by_url, dedup_by_title_simhash

                r1 = dedup_by_url(filtered)
                print(f"[INFO] URL去重后: {len(r1.kept)} 篇（丢弃 {len(r1.dropped)} 篇）")
                # 科创热点标题去重放宽，避免误删
                if "科创热点" in column_name or "科创头条" in column_name:
                    r2 = dedup_by_title_simhash(r1.kept, max_hamming=5)  # 放宽到5
                else:
                    r2 = dedup_by_title_simhash(r1.kept, max_hamming=3)
                print(f"[INFO] 标题去重后: {len(r2.kept)} 篇（丢弃 {len(r2.dropped)} 篇）")

                # Step D: 入库+历史去重
                from app.pipeline.persist import persist_new_articles

                # 每次运行都清空当天数据，所以禁用历史去重（避免把当天的文章过滤掉）
                new_articles, seen_articles = persist_new_articles(db, r2.kept, enable_history_dedup=False)
                articles_for_ranking = r2.kept  # 直接使用去重后的，不依赖new_articles
                print(f"[INFO] {column_name}跳过历史去重（已清空当天数据），保留 {len(articles_for_ranking)} 篇")

                # Step E: 排序+选题
                from app.pipeline.ranking import score_articles

                source_weights = {s["name"]: float(s.get("weight", 1.0)) for s in column_cfg.get("sources", [])}
                scored = score_articles(articles_for_ranking, source_weights)
                selected = [x.article for x in scored[:max_items]]
                print(f"[INFO] 排序后选择: {len(selected)} 篇")

                selected_dicts: List[Dict[str, Any]] = [a.to_dict() for a in selected]

                # Step F: 不足回填
                # 科创热点有自己的补充机制（从 /telegraph 补充），不使用前一天的 fallback
                if len(selected_dicts) < min_items and "科创热点" not in column_name and "科创头条" not in column_name:
                    with step(f"栏目 {column_name} 不足{min_items}条：从前一天回填"):
                        from app.pipeline.fallback import fill_with_previous_day

                        selected_dicts = fill_with_previous_day(
                            db_path=db_path,
                            selected_today=selected_dicts,
                            min_items=min_items,
                            max_items=max_items,
                            run_date=run_date,
                        )

                if len(selected_dicts) < min_items:
                    print(f"[WARN ] 栏目 {column_name} 回填后仍不足{min_items}条，将跳过LLM写作")

                # 记录来源 URL（仅记录有 url 的）
                for a in selected_dicts:
                    u = a.get("url")
                    if u:
                        all_source_urls.add(u)

                # Step G: LLM写作
                draft = None
                if client and selected_dicts and len(selected_dicts) >= min_items:
                    from app.pipeline.writing import generate_column_content

                    draft = generate_column_content(
                        column_name,
                        selected_dicts,
                        run_date.isoformat(),
                        client,
                        min_items=min_items,
                        max_items=max_items,
                    )
                else:
                    # 无LLM时，保底输出一个简单markdown（仍可渲染）
                    md = "\n".join([f"- {a.get('title','')}" for a in selected_dicts[:max_items]])
                    draft = {
                        "type": "raw_list",
                        "name": column_name,
                        "date": run_date.isoformat(),
                        "markdown": md,
                    }
                
                # 保存 markdown 到文件
                if draft and draft.get("markdown"):
                    md_file = day_dir / f"{column_name}_markdown.md"
                    md_file.write_text(draft["markdown"], encoding="utf-8")
                    print(f"[INFO] 已保存 {column_name} 的 markdown: {md_file}")

                # Step H: 图片（每条文章尝试下载原图；封面会生成一次即可）
                cover_rel = None
                images_rel: Dict[str, str] = {}
                if draft and selected_dicts:
                    with step(f"栏目 {column_name} 下载/生成图片"):
                        try:
                            from app.images.pipeline import prepare_images

                            cover_rel, images_rel = prepare_images(
                                day_dir=day_dir,
                                selected=selected_dicts,
                                draft_type=draft.get("type", "raw_list"),
                                cover_cfg=cfg.get("images", {}).get("cover", {}),
                            )
                        except Exception as e:
                            print(f"WARN: prepare_images failed: {e}")

                all_columns_data.append(
                    {
                        "draft": draft,
                        "items": selected_dicts,
                        "cover_rel": cover_rel,
                        "images_rel": images_rel,
                    }
                )

        # aggregated：便于排查
        with step("写入 aggregated.json"):
            aggregated = {
                "date": run_date.isoformat(),
                "columns": [
                    {
                        "name": c.get("draft", {}).get("name"),
                        "type": c.get("draft", {}).get("type"),
                        "items": len(c.get("items") or []),
                    }
                    for c in all_columns_data
                ],
                "source_urls": sorted(all_source_urls),
            }
            (day_dir / "aggregated.json").write_text(json.dumps(aggregated, ensure_ascii=False, indent=2), encoding="utf-8")

    finally:
        try:
            if client:
                client.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

    # 渲染 wechat.html（单页多栏目）
    if all_columns_data:
        with step("渲染 wechat.html"):
            from app.render.wechat_html import render_wechat_html

            final_html = render_wechat_html(
                columns_data=all_columns_data,
                source_urls=sorted(all_source_urls),
                run_date=run_date,
            )
            (day_dir / "wechat.html").write_text(final_html, encoding="utf-8")

        print(f"[DONE ] 生成完成：{day_dir / 'wechat.html'}")
        print("[NOTE ] 微信编辑器粘贴不会带本地图片，请到微信后台上传图片后按位置插入。")
    else:
        with step("写入 wechat.html(空)"):
            (day_dir / "wechat.html").write_text("<html><body><h1>今日无可用内容</h1></body></html>", encoding="utf-8")

    print(f"Done. All files saved in: {day_dir}")


if __name__ == "__main__":
    main()
