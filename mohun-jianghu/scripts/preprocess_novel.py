#!/usr/bin/env python3
"""
小说预处理脚本：把 TXT 小说按章回切分，方便上传到 Dify 知识库。
用法：python preprocess_novel.py <input.txt> <output_dir>

输出：在 output_dir 下生成多个小文件，每个文件对应一个章回。
      Dify 知识库上传时选择"按文件分块"，每个文件即一个 chunk。
"""

import os
import re
import sys


def split_by_chapter(input_path: str, output_dir: str):
    """按章回正则切分小说"""
    # 章回标题正则：第X回/章/节/卷
    chapter_pattern = re.compile(
        r"^(第[一二三四五六七八九十百千万零\d]+[回章节卷][\s\S]*?)$",
        re.MULTILINE
    )
    
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 查找所有章回标题位置
    matches = list(chapter_pattern.finditer(content))
    
    if len(matches) < 2:
        print(f"[警告] 仅找到 {len(matches)} 个章回标记，可能不是章回体小说。")
        print("       将按固定长度（2000字）切分。")
        return split_by_length(content, output_dir, 2000)
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[信息] 共找到 {len(matches)} 个章回，开始切分...")
    
    for i, match in enumerate(matches):
        title = match.group(1).strip().replace("\n", " ")[:50]
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        chapter_content = content[start:end].strip()
        
        # 生成文件名（章回序号+标题前20字）
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:20]
        filename = f"{i+1:04d}_{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(chapter_content)
    
    print(f"[完成] 已切分为 {len(matches)} 个文件，保存到 {output_dir}/")
    print(f"       上传到 Dify 知识库时选择'按文件分块'策略。")


def split_by_length(content: str, output_dir: str, chunk_size: int = 2000):
    """按固定长度切分（非章回体小说的兜底方案）"""
    os.makedirs(output_dir, exist_ok=True)
    
    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
    
    for i, chunk in enumerate(chunks):
        filename = f"{i+1:04d}_part.txt"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(chunk)
    
    print(f"[完成] 已按 {chunk_size} 字切分为 {len(chunks)} 个文件，保存到 {output_dir}/")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python preprocess_novel.py <input.txt> <output_dir>")
        print("示例: python preprocess_novel.py 射雕英雄传.txt chapters/")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(input_path):
        print(f"[错误] 文件不存在: {input_path}")
        sys.exit(1)
    
    split_by_chapter(input_path, output_dir)
