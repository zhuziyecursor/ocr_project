import os
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List

router = APIRouter(prefix="/ocr-files", tags=["ocr-files"])

# 本地 OCR 结果目录
OCR_RESULT_DIR = "/Users/apple/Documents/work_project/OCR_PROJECT/ccr_result"


def get_images_dir(json_filename):
    """获取 JSON 文件对应的图片目录"""
    # JSON 文件名如 "Claude Code从入门到精通-v2.0.0.json"
    # 图片目录名如 "Claude Code从入门到精通-v2.0.0_images"
    images_dir = json_filename.replace('.json', '') + '_images'
    return os.path.join(OCR_RESULT_DIR, images_dir)


@router.get("/")
async def list_ocr_files():
    """列出本地 OCR 结果文件"""
    if not os.path.exists(OCR_RESULT_DIR):
        raise HTTPException(status_code=404, detail="OCR result directory not found")

    files = []
    for filename in os.listdir(OCR_RESULT_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(OCR_RESULT_DIR, filename)
            file_stat = os.stat(filepath)
            images_dir = get_images_dir(filename)
            images = []
            if os.path.exists(images_dir):
                for img in os.listdir(images_dir):
                    if img.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        images.append(img)
            files.append({
                "name": filename,
                "size": file_stat.st_size,
                "images": images
            })

    return {"files": files}


@router.get("/{filename}")
async def get_ocr_file(filename: str):
    """获取指定 OCR 结果文件"""
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = os.path.join(OCR_RESULT_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data


@router.get("/{filename}/images/{image_name}")
async def get_ocr_image(filename: str, image_name: str):
    """获取 OCR 结果中的图片文件"""
    if ".." in filename or ".." in image_name or filename.startswith("/") or image_name.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")

    images_dir = get_images_dir(filename)
    image_path = os.path.join(images_dir, image_name)

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path)
