"""
OpenDataLoader封装层

根据CLAUDE.md规定：所有对OpenDataLoader的调用必须经过此文件进行封装
禁止直接修改opendataloader-pdf-main目录下的任何文件

调用方式：opendataloader_pdf.convert() 直接调用 Java CLI
"""

import os
import json
import shutil
import uuid
from typing import Optional, List


class OpenDataLoaderWrapper:
    """
    OpenDataLoader封装类

    使用方式：
    wrapper = OpenDataLoaderWrapper()
    result = wrapper.convert("/path/to/file.pdf")
    """

    def __init__(self, host: str = "localhost", port: int = 5002):
        self.host = host
        self.port = port
        self.base_url = f"http://{self.host}:{self.port}"

    def _read_kids_result(self, json_path: str) -> Optional[dict]:
        """读取 kids 格式的 JSON 结果文件"""
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'kids' in data:
                return data
        except Exception:
            pass
        return None

    def convert(
        self,
        file_path: str,
        format: str = "json",
        table_method: str = "cluster",
        image_output: str = "external",
        hybrid: str = "docling-fast",
        hybrid_mode: str = "full",
        sanitize: bool = True,
        force_ocr: bool = True,
        ocr_lang: str = "zh,en",
    ) -> dict:
        """
        调用OpenDataLoader进行文档识别

        参数：
            file_path: 文件路径
            format: 输出格式，默认json
            table_method: 表格识别方法
            image_output: 图片输出方式，external 才能获取提取的图片
            hybrid: 混合模式
            hybrid_mode: full 才能获取图表 AI 描述
            sanitize: 安全要求，必须 True
            force_ocr: 扫描件必须加
            ocr_lang: OCR 语言

        返回：
            dict: kids 格式的 JSON 输出（包含 _images_dir 字段指向图片目录）
        """
        import opendataloader_pdf

        # 使用确定性的临时目录（不在 temp 下，可用于传递图片）
        output_dir = os.path.join("/tmp", f"odl_{uuid.uuid4().hex}")
        os.makedirs(output_dir, exist_ok=True)

        try:
            opendataloader_pdf.convert(
                input_path=[file_path],
                output_dir=output_dir,
                format="json",
                quiet=True,
                table_method=table_method,
                image_output=image_output,
                hybrid=hybrid,
                hybrid_mode=hybrid_mode,
                hybrid_ocr="force" if force_ocr else "auto",
                hybrid_url=f"http://{self.host}:{self.port}" if hybrid != "off" else None,
            )

            # 读取生成的 JSON 文件
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            json_path = os.path.join(output_dir, f"{base_name}.json")

            result = self._read_kids_result(json_path)
            if result is not None:
                # 附加图片目录路径（供调用方复制使用）
                images_dir = os.path.join(output_dir, f"{base_name}_images")
                if os.path.exists(images_dir):
                    result["_images_dir"] = images_dir
                return result

            # 如果没找到 JSON 文件，尝试其他可能的文件名模式
            for filename in os.listdir(output_dir):
                if filename.endswith('.json'):
                    json_path = os.path.join(output_dir, filename)
                    result = self._read_kids_result(json_path)
                    if result is not None:
                        images_dir = os.path.join(output_dir, filename.replace('.json', '_images'))
                        if os.path.exists(images_dir):
                            result["_images_dir"] = images_dir
                        return result

            raise ValueError(f"无法从 {output_dir} 读取 kids 格式结果")
        finally:
            # 注意：不清理临时目录，由调用方负责清理（或在 convert 后主动删除）
            pass

    def convert_with_images(
        self,
        file_path: str,
        target_images_dir: str,
        **kwargs
    ) -> dict:
        """
        调用 OpenDataLoader 并将提取的图片复制到指定目录。

        参数：
            file_path: 文件路径
            target_images_dir: 目标图片目录（会被创建）
            **kwargs: 传递给 convert 的其他参数

        返回：
            dict: kids 格式的 JSON 输出
        """
        result = self.convert(file_path, **kwargs)

        # 复制图片到目标目录
        src_images_dir = result.pop("_images_dir", None)
        if src_images_dir and os.path.exists(src_images_dir):
            os.makedirs(target_images_dir, exist_ok=True)
            for fname in os.listdir(src_images_dir):
                src_path = os.path.join(src_images_dir, fname)
                dst_path = os.path.join(target_images_dir, fname)
                shutil.copy2(src_path, dst_path)

        return result

    def convert_chunk(
        self,
        file_path: str,
        start_page: int,
        end_page: int,
        **kwargs
    ) -> dict:
        """
        分块转换（每次50页）

        根据CLAUDE.md规定，大文件分块处理，每块固定50页
        """
        import opendataloader_pdf

        output_dir = os.path.join("/tmp", f"odl_{uuid.uuid4().hex}")
        os.makedirs(output_dir, exist_ok=True)

        try:
            opendataloader_pdf.convert(
                input_path=[file_path],
                output_dir=output_dir,
                format="json",
                quiet=True,
                pages=f"{start_page}-{end_page}",
                **kwargs
            )

            # 读取生成的 JSON 文件
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            json_path = os.path.join(output_dir, f"{base_name}.json")

            result = self._read_kids_result(json_path)
            if result is not None:
                images_dir = os.path.join(output_dir, f"{base_name}_images")
                if os.path.exists(images_dir):
                    result["_images_dir"] = images_dir
                return result

            for filename in os.listdir(output_dir):
                if filename.endswith('.json'):
                    json_path = os.path.join(output_dir, filename)
                    result = self._read_kids_result(json_path)
                    if result is not None:
                        images_dir = os.path.join(output_dir, filename.replace('.json', '_images'))
                        if os.path.exists(images_dir):
                            result["_images_dir"] = images_dir
                        return result

            raise ValueError(f"无法从 {output_dir} 读取 kids 格式结果")
        finally:
            pass
