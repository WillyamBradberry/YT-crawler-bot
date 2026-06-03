"""
YouTube channel thumbnail downloader and metadata generator.
Produces Obsidian and LM Studio compatible info.md and analysis-prompt.md.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime
from typing import Any

import yt_dlp

# Попытка импорта Pillow для конвертации изображений
try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DESCRIPTION_CLEAN_PATTERNS: list[tuple[str, str]] = [
    (r"https?://\S+", ""),
    (r"\[www[^]]*\]\([^)]+\)", ""),
    (r"(?mi)^.*patron\.com.*$\n?", ""),
    (r"(?mi)^.*discord\.gg.*$\n?", ""),
    (r"(?mi)^.*discordapp\.com.*$\n?", ""),
    (r"(?mi)^.*telegram\.me.*$\n?", ""),
    (r"(?mi)^.*t\.me/.*$\n?", ""),
    (r"(?mi)^\*?[-*]?\s*patron\.com\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*discord\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*telegram\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*sponsor(?:ed)?\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*affiliate\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*merch\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*store\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*instagram\s*[-*]?\n?", ""),
    (r"(?mi)^\*?[-*]?\s*twitter\.com.*$\n?", ""),
    (r"(?mi)^\*?[-*]?\s*x\.com.*$\n?", ""),
    (r"(?mi)^\*?[-*]?\s*facebook(?:\.com)?.*\n?", ""),
    (r"(?mi)^\*?[-*]?\s*tiktok\s*[-*]?\n?", ""),
]

_LINK_SECTION_HEADERS: list[str] = [
    "Links:", "Link:", "Follow me:", "Follow us:", "Support the channel:",
    "Support the Channel:", "My socials:", "My Socials:", "Socials:",
    "Connect:", "Connect with me:", "Join me:", "Subscribe:", "Watch more:",
    "More videos:",
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _is_node_available() -> bool:
    """Check whether Node.js runtime is available on the system."""
    return shutil.which("node") is not None


def get_yt_dlp_options(**extra: Any) -> dict[str, Any]:
    """Return a configuration dictionary for yt-dlp."""
    opts: dict[str, Any] = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "playlist_items": None,
        "extractor_retries": 3,
    }

    if _is_node_available():
        opts["js_runtimes"] = {"node": {}}
    else:
        opts["compat_options"] = ["no-live-chat-compact"]
        opts["quiet"] = True
        opts["no_warnings"] = True

    opts.update(extra)
    return opts


def clean_description(description: str) -> str:
    """Clean a YouTube video description from social links and ads."""
    if not description:
        return ""

    text = description
    for pattern, replacement in _DESCRIPTION_CLEAN_PATTERNS:
        text = re.sub(pattern, replacement, text)

    lines = text.splitlines()
    keep_lines: list[str] = []
    skip_remaining = False

    for line in lines:
        if skip_remaining:
            continue
        stripped = line.strip().lower()
        if stripped.rstrip(":") == "" or stripped.endswith(":"):
            is_header = False
            for header in _LINK_SECTION_HEADERS:
                if stripped.startswith(header.lower()):
                    is_header = True
                    skip_remaining = True
                    break
            if not is_header:
                keep_lines.append(line)
        else:
            keep_lines.append(line)

    text = "\n".join(keep_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _safe_filename_base(title: str, index: int) -> str:
    """Create a filesystem-safe base filename without extension."""
    safe = re.sub(r"[^\w\-. ]", "", title).strip()[:65]
    safe = re.sub(r"\s+", "_", safe)
    return f"{index:02d}_{safe}"


def _channel_name_from_url(url: str) -> str:
    """Extract a channel name slug from a YouTube URL."""
    if "@" in url:
        part = url.strip("/").split("@")[-1].split("/")[0]
        return re.sub(r"[^\w]+", "_", part).strip("_") or "youtube_channel"
    return "youtube_channel"


def _convert_webp_to_jpg(folder: str, filename_base: str) -> str:
    """Find downloaded thumbnail, convert it to .jpg if it is webp/other, and return final filename."""
    final_jpg_name = f"{filename_base}.jpg"
    final_jpg_path = os.path.join(folder, final_jpg_name)

    # Ищем, какой файл скачал yt-dlp для этой базовой основы
    downloaded_file = None
    if os.path.exists(folder):
        for file in os.listdir(folder):
            if file.startswith(filename_base) and not file.endswith(".md"):
                downloaded_file = file
                break

    if not downloaded_file:
        return final_jpg_name

    downloaded_path = os.path.join(folder, downloaded_file)

    # Если скачался файл не .jpg формата (например .webp) — конвертируем его
    if not downloaded_file.lower().endswith(".jpg"):
        if Image is not None:
            try:
                with Image.open(downloaded_path) as img:
                    # Преобразуем в RGB режим (обязательно для сохранения в JPEG)
                    rgb_img = img.convert("RGB")
                    rgb_img.save(final_jpg_path, "JPEG", quality=95)
                os.remove(downloaded_path)  # Удаляем оригинальный .webp файл
                # print(f"   [Converted] {downloaded_file} -> {final_jpg_name}")
            except Exception as e:
                print(f"   [ERROR] Не удалось конвертировать {downloaded_file}: {e}")
        else:
            print("[WARNING] Библиотека Pillow не установлена. Конвертация в .jpg пропущена.")
            return downloaded_file

    return final_jpg_name


# ---------------------------------------------------------------------------
# High-level builders
# ---------------------------------------------------------------------------

def build_info_md(channel_name: str, videos: list[dict[str, Any]]) -> str:
    """Build an Obsidian-compatible *info.md* markdown string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        "---",
        f"channel: {channel_name}",
        f"generated: {now}",
        f"videos: {len(videos)}",
        "---",
        "",
        "# Channel Source Data",
        "",
    ]

    for idx, v in enumerate(videos, start=1):
        title = v["title"]
        filename = v["filename"]
        video_url = v["video_url"]
        description = v["cleaned_description"]

        lines.append(f"## {idx:02d}. {title}")
        lines.append("")
        lines.append(f"![[{filename}]]")
        lines.append("")
        lines.append("### Metadata")
        lines.append("")
        lines.append("| Field     | Value                             |")
        lines.append("| --------- | --------------------------------- |")
        lines.append(f"| File      | `{filename}`                      |")
        lines.append(f"| Video URL | [{video_url}]({video_url})         |")
        lines.append("")
        lines.append("### Description")
        lines.append("")
        if description:
            lines.append(description)
        else:
            lines.append("—")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_analysis_prompt(channel_name: str, videos: list[dict[str, Any]]) -> str:
    """Build an *analysis-prompt.md* file template."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        "---",
        f"channel: {channel_name}",
        f"generated: {now}",
        "---",
        "",
        "# Thumbnail Analysis Prompt",
        "",
        "Ты — умный агент-помощник по работе с YouTube-каналами.",
        "",
        f"**Канал:** `{channel_name}`",
        f"**Количество видео:** {len(videos)}",
        "",
        "Выполни анализ каждого thumbnail строго по порядку (01 → 02 → …).",
        "",
    ]

    for idx, v in enumerate(videos, start=1):
        lines.append(f"## {idx:02d}. {v['title']}")
        lines.append("")
        lines.append(f"**Файл:** `{v['filename']}`")
        lines.append(f"**Ссылка:** [{v['video_url']}]({v['video_url']})")
        if v["cleaned_description"]:
            lines.append("")
            lines.append("**Описание:**")
            lines.append(v["cleaned_description"])
        lines.append("")

    lines.extend([
        "---",
        "",
        "Для каждого видео укажи:",
        "",
        "- **Thumbnail анализ:** что изображено, цветовая гамма, стиль, эмоция, главный визуальный хук",
        "- **Выводы:** основная тема, целевая аудитория, сильные/слабые стороны thumbnail",
        "",
        "### Финальный общий анализ:",
        "",
        "- Общий стиль канала по thumbnails",
        "- Самые частые приёмы",
        "- Что работает лучше всего",
        "- Рекомендации по улучшению",
        "",
        "---",
        "",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core download logic
# ---------------------------------------------------------------------------

def _fetch_video_infos(channel_url: str, num_videos: int) -> list[dict[str, Any]]:
    """Fetch video metadata and handle thumbnail downloads and conversions."""
    safe_channel = _channel_name_from_url(channel_url)
    output_folder = f"{safe_channel}_thumbnails"
    os.makedirs(output_folder, exist_ok=True)

    ydl_opts = get_yt_dlp_options(
        playlist_items=f"1-{num_videos}",
    )

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    entries = info.get("entries") or []
    videos_raw = [e for e in entries if e is not None]

    result: list[dict[str, Any]] = []

    for i, video in enumerate(videos_raw, start=1):
        title: str = video.get("title") or f"Video_{i}"
        video_id: str | None = video.get("id")
        if not video_id:
            continue

        filename_base = _safe_filename_base(title, i)
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Download thumbnail using flat structure
        thumb_opts = get_yt_dlp_options(
            outtmpl=os.path.join(output_folder, filename_base),
            skip_download=True,
            writethumbnail=True,
        )
        with yt_dlp.YoutubeDL(thumb_opts) as ydl_thumb:
            ydl_thumb.download([video_url])

        # НАДЁЖНАЯ КОНВЕРТАЦИЯ В JPG: файлы сохраняются строго как .jpg
        filename = _convert_webp_to_jpg(output_folder, filename_base)

        # Re-fetch full description if flat format left it empty
        description: str = video.get("description") or ""
        if not description:
            try:
                desc_opts = get_yt_dlp_options()
                with yt_dlp.YoutubeDL(desc_opts) as ydl_desc:
                    full_info = ydl_desc.extract_info(video_url, download=False)
                    description = full_info.get("description") or ""
            except Exception:
                description = "Описание не удалось загрузить."

        cleaned = clean_description(description)

        result.append({
            "title": title,
            "filename": filename,  # Теперь гарантированно расширение .jpg
            "video_url": video_url,
            "cleaned_description": cleaned,
        })

    return result


def download_channel_thumbnails(channel_url: str, num_videos: int = 12) -> None:
    """Download thumbnails for a YouTube channel and produce formatted outputs."""
    if not _is_node_available():
        print("[WARNING] Node.js not found. Some YouTube metadata may be incomplete.")

    safe_channel = _channel_name_from_url(channel_url)
    output_folder = f"{safe_channel}_thumbnails"
    os.makedirs(output_folder, exist_ok=True)

    print(f"📺 Канал: {channel_url}")
    print(f"🎯 Скачиваем первые {num_videos} видео...\n")

    videos = _fetch_video_infos(channel_url, num_videos)

    if not videos:
        print("⚠️  Не удалось получить информацию о видео.")
        return

    print(f"✅ Получено и обработано {len(videos)} видео\n")

    info_md = build_info_md(safe_channel, videos)
    info_path = os.path.join(output_folder, "info.md")
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(info_md)
    print(f"📄 info.md сохранён в {info_path}")

    prompt_md = build_analysis_prompt(safe_channel, videos)
    prompt_path = os.path.join(output_folder, "analysis-prompt.md")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_md)
    print(f"📄 analysis-prompt.md сохранён в {prompt_path}")

    print(f"\n🎉 Готово!")
    print(f"📁 Папка: {output_folder}")
    print(f"   • Thumbnails: {len(videos)} шт. (Все сконвертированы в .jpg для LM Studio)")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Введите ссылку на YouTube-канал: ").strip()

    if not url:
        url = "https://www.youtube.com/@perepolox/videos"

    num = 12
    if len(sys.argv) > 2:
        try:
            num = int(sys.argv[2])
        except ValueError:
            pass

    download_channel_thumbnails(url, num)