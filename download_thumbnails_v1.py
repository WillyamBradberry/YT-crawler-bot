import os
import json
import sys
from datetime import datetime
import yt_dlp

def download_channel_thumbnails(channel_url: str, num_videos: int = 12):
    if '@' in channel_url:
        channel_name = channel_url.strip('/').split('@')[-1].split('/')[0]
    else:
        channel_name = "youtube_channel"
    
    output_folder = f"{channel_name}_thumbnails"
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"📺 Канал: {channel_url}")
    print(f"🎯 Обрабатываем первые {num_videos} видео...\n")
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'playlist_items': f'1-{num_videos}',
        'extractor_retries': 3,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
        
        videos = [entry for entry in info.get('entries', []) if entry is not None]
        print(f"✅ Получено {len(videos)} видео\n")
        
        md_content = []
        md_content.append(f"# Thumbnails — {channel_name}\n")
        md_content.append(f"**Канал:** {channel_url}")
        md_content.append(f"**Дата выгрузки:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        md_content.append(f"**Всего видео:** {len(videos)}\n")
        md_content.append("---\n")
        
        for i, video in enumerate(videos, 1):
            title = video.get('title', 'Без названия')
            video_id = video.get('id')
            description = video.get('description', 'Описание отсутствует')
            duration = video.get('duration_string', '—')
            views = video.get('view_count', 0)
            upload_date = video.get('upload_date', '')
            
            if not video_id:
                continue
                
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:65]
            image_filename = f"{i:02d}_{safe_title}.jpg"
            
            # Скачиваем thumbnail
            print(f"{i:02d}. {title[:75]}")
            
            thumb_opts = {
                'outtmpl': os.path.join(output_folder, f"{i:02d}_{safe_title}"),
                'quiet': True,
                'writethumbnail': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(thumb_opts) as ydl_thumb:
                ydl_thumb.download([f"https://www.youtube.com/watch?v={video_id}"])
            
            # Запись в info.md
            md_content.append(f"## {i:02d}. {title}")
            md_content.append(f"**Файл:** `{image_filename}`")
            md_content.append(f"**Ссылка:** https://www.youtube.com/watch?v={video_id}")
            md_content.append(f"**Длительность:** {duration} | **Просмотры:** {views:,}")
            if upload_date:
                md_content.append(f"**Опубликовано:** {upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}")
            md_content.append("\n**Оригинальное описание:**")
            md_content.append(description if description != 'Описание отсутствует' else "_Описание не указано_")
            md_content.append("\n---\n")
        
        # Сохраняем info.md
        md_path = os.path.join(output_folder, "info.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
        
        print(f"\n🎉 Готово!")
        print(f"📁 Папка: {output_folder}")
        print(f"   • {len(videos)} thumbnails (.jpg)")
        print(f"   • info.md — готовый файл для анализа агентом")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

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
        except:
            pass
    
    download_channel_thumbnails(url, num)