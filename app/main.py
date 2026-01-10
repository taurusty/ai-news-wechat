import argparse
import os
from datetime import datetime, date
from pathlib import Path
import asyncio

# 尽早加载 .env，避免后续误报“未设置API KEY”
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import yaml


def load_config():
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


async def run_sources(cfg: dict) -> list:
    """抓取所有启用的sources，单一事件循环内完成，避免Windows下loop关闭问题"""
    from app.sources.registry import create_source

    articles = []
    sources_cfg = {s["name"]: s for s in cfg.get("sources", []) if s.get("enabled", True)}

    for source_name, scfg in sources_cfg.items():
        try:
            src = create_source(source_name, weight=scfg.get("weight", 1.0), enabled=scfg.get("enabled", True))
        except Exception as e:
            print(f"WARN: source {source_name} init failed: {e}")
            continue

        try:
            # 单个source整体超时保护：避免某个站点卡住导致整体阻塞
            fetched = await asyncio.wait_for(
                src.fetch_articles(max_items=cfg.get("ranking", {}).get("max_items_considered", 40)),
                timeout=float(cfg.get("timeouts", {}).get("per_source_seconds", 25)),
            )
            articles.extend(fetched)
            print(f"[INFO ] source={source_name} fetched={len(fetched)}")
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

    out_base = Path(cfg["output"]["base_dir"]).resolve()
    day_dir = out_base / run_date.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: 抓取
    with step("抓取来源站点"):
        articles = asyncio.run(run_sources(cfg))

    import json

    with step("写入 sources_preview.json"):
        (day_dir / "sources_preview.json").write_text(
            json.dumps([a.to_dict() for a in articles[:200]], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Step 2: 关键词过滤
    from app.pipeline.filtering import keyword_filter

    with step("关键词过滤"):
        filt_cfg = cfg.get("filter", {})
        filtered = keyword_filter(articles, filt_cfg.get("keywords_any", []), filt_cfg.get("keywords_not", []))
        print(f"[INFO ] filtered={len(filtered)}")

    # Step 3: 去重
    from app.pipeline.dedup import dedup_by_url, dedup_by_title_simhash

    with step("去重（URL+标题相似）"):
        r1 = dedup_by_url(filtered)
        r2 = dedup_by_title_simhash(r1.kept, max_hamming=3)
        print(f"[INFO ] dedup_url_dropped={len(r1.dropped)} dedup_title_dropped={len(r2.dropped)}")

    # Step 4: SQLite
    from app.pipeline.persist import persist_new_articles
    from app.storage.db import ArticleDB

    db_path = Path("./db/articles.sqlite3").resolve()
    with step("历史去重入库（SQLite）"):
        db = ArticleDB(db_path)
        try:
            new_articles, seen_articles = persist_new_articles(db, r2.kept, enable_history_dedup=True)
        finally:
            db.close()
        print(f"[INFO ] new={len(new_articles)} seen={len(seen_articles)}")

    articles_for_ranking = new_articles or r2.kept

    # Step 5: 排序+选题
    from app.pipeline.ranking import score_articles

    min_items, max_items = 5, 10
    with step("热度排序"):
        source_weights = {s["name"]: float(s.get("weight", 1.0)) for s in cfg.get("sources", [])}
        scored = score_articles(articles_for_ranking, source_weights)

    with step("选择Top新闻"):
        selected = [x.article for x in scored[:max_items]]
        print(f"[INFO ] selected_today={len(selected)}")

    # 不足5条则从前一天 output 回填（真实来源，不编造）
    selected_dicts: list[dict] = [a.to_dict() for a in selected]
    if len(selected_dicts) < min_items:
        with step("不足5条：从前一天回填"):
            try:
                from app.pipeline.fallback import fill_with_previous_day

                selected_dicts = fill_with_previous_day(
                    db_path=db_path,
                    selected_today=selected_dicts,
                    min_items=min_items,
                    max_items=max_items,
                    run_date=run_date,
                )
                print(f"[INFO ] selected_after_fallback={len(selected_dicts)}")
            except Exception as e:
                print(f"WARN: fallback fill failed: {e}")

    with step("写入 aggregated.json"):
        aggregated = {
            "date": run_date.isoformat(),
            "counts": {
                "fetched": len(articles),
                "keyword_filtered": len(filtered),
                "deduped": len(r2.kept),
                "seen_in_history": len(seen_articles),
                "new": len(new_articles),
                "selected": len(selected_dicts),
            },
            "selected": selected_dicts,
        }
        (day_dir / "aggregated.json").write_text(
            json.dumps(aggregated, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Step 6: LLM 写作
    from app.pipeline.writing import generate_daily_article, generate_deep_dive, is_deep_dive_day
    from app.llm.deepseek_client import DeepSeekClient

    draft = None
    if not selected_dicts:
        print("[WARN ] 无可用新闻，跳过生成")
    elif not os.getenv("DEEPSEEK_API_KEY"):
        print("[WARN ] 未设置DEEPSEEK_API_KEY，跳过LLM写作")
    else:
        with step("调用LLM生成正文"):
            client = DeepSeekClient(
                base_url=cfg.get("llm", {}).get("base_url") or "https://api.deepseek.com",
                model=os.getenv(cfg.get("llm", {}).get("model_env", "DEEPSEEK_MODEL")),
            )
            try:
                if is_deep_dive_day(run_date, cfg.get("schedule", {}).get("deep_dive_weekday", 0)):
                    print("[INFO ] 周一：深度解读")
                    draft = generate_deep_dive(selected_dicts[0], run_date.isoformat(), client)
                else:
                    print("[INFO ] 干货总结")
                    draft = generate_daily_article(
                        selected_dicts,
                        run_date.isoformat(),
                        client,
                        min_items=min_items,
                        max_items=max_items,
                    )
            finally:
                client.close()

    # Step 7: 生成图片
    cover_rel = None
    images_rel = {}
    if draft:
        with step("下载/生成图片"):
            try:
                from app.images.pipeline import prepare_images

                cover_rel, images_rel = prepare_images(
                    day_dir=day_dir,
                    selected=selected_dicts,
                    draft_type=draft.get("type", "daily_summary"),
                    cover_cfg=cfg.get("images", {}).get("cover", {}),
                )
                print(f"[INFO ] cover={bool(cover_rel)} images={len(images_rel)}")
            except Exception as e:
                print(f"WARN: prepare_images failed: {e}")

    # Step 8: 渲染与写文件（仅微信平台用）
    if draft:
        with step("写入 wechat_draft.json"):
            (day_dir / "wechat_draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")

        with step("渲染 wechat.html"):
            from app.render.simple_html import render_final_html

            final_html = render_final_html(
                draft,
                cover_rel=cover_rel,
                items=selected_dicts,
                images_rel=images_rel,
            )
            (day_dir / "wechat.html").write_text(final_html, encoding="utf-8")

        print(f"[DONE ] 生成完成：{day_dir / 'wechat.html'}")
        print("[NOTE ] 微信编辑器粘贴不会带本地图片，请到微信后台上传图片后按位置插入。")
    else:
        with step("写入 wechat.html(空)"):
            (day_dir / "wechat.html").write_text("<html><body><h1>今日无新AI热点</h1></body></html>", encoding="utf-8")

    print(f"Done. All files saved in: {day_dir}")


if __name__ == "__main__":
    main()
