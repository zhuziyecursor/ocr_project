"""
OpenDataLoader封装层

根据CLAUDE.md规定：所有对OpenDataLoader的调用必须通过此文件进行封装
禁止直接修改opendataloader-pdf-main目录下的任何文件

调用方式：OpenDataLoader Hybrid Server（REST API）
启动命令：opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "zh,en"
"""

import requests
from typing import Optional


class OpenDataLoaderWrapper:
    """
    OpenDataLoader封装类（HTTP 调用方式）

    使用方式：
    wrapper = OpenDataLoaderWrapper()
    result = wrapper.convert("/path/to/file.pdf")
    """

    def __init__(self, host: str = "host.docker.internal", port: int = 5002):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    def convert(
        self,
        file_path: str,
        format: str = "json",
        table_method: str = "cluster",
        image_output: str = "embedded",
        hybrid: str = "docling-fast",
        hybrid_mode: str = "full",
        sanitize: bool = True,
        force_ocr: bool = True,
        ocr_lang: str = "zh,en",
    ):
        """
        调用OpenDataLoader Hybrid Server进行文档识别

        参数：
            file_path: 文件路径
            format: 输出格式，默认json
            table_method: 表格识别方法
            image_output: 图片输出方式
            hybrid: 混合模式
            hybrid_mode: full 才能获取图表 AI 描述
            sanitize: 安全要求，必须 True
            force_ocr: 扫描件必须加
            ocr_lang: OCR 语言

        返回：
            dict: OpenDataLoader的JSON输出
        """
        with open(file_path, 'rb') as f:
            files = {'files': (file_path, f, 'application/octet-stream')}
            data = {}
            if force_ocr:
                data['force_ocr'] = 'true'
            response = requests.post(
                f"{self.base_url}/v1/convert/file",
                files=files,
                data=data,
                timeout=3600
            )
            response.raise_for_status()
            return response.json()

    def convert_chunk(
        self,
        file_path: str,
        start_page: int,
        end_page: int,
        **kwargs
    ):
        """
        分块转换（每次50页）

        根据CLAUDE.md规定，大文件分块处理，每块固定50页
        """
        # Hybrid Server 支持 pages 参数
        kwargs['pages'] = f"{start_page}-{end_page}"
        return self.convert(file_path, **kwargs)
