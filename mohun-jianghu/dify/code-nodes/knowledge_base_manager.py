"""
Dify Code 节点：动态知识库管理（开局/换书）
============================================
用途：调用 Dify API 创建知识库、上传小说 TXT、轮询索引状态。
      支持"换书"时清理旧知识库。

注意：本节点需要在 Dify 的 HTTP 请求节点中调用 Dify 自身 API，
      或在 Code 节点中使用 requests 库（需 Dify 开启网络访问权限）。

输入参数：
  - action: str           "create" | "delete" | "status"
  - novel_name: str       小说名（create 时使用）
  - dataset_id: str       知识库 ID（delete/status 时使用）
  - api_key: str          Dify API Key（知识库 API）
  - base_url: str         Dify 基础 URL，如 http://localhost/v1

输出参数：
  - dataset_id: str       创建/操作的知识库 ID
  - status: str           操作状态
  - message: str          提示信息
"""

import json


def main(action: str, novel_name: str, dataset_id: str,
         api_key: str, base_url: str) -> dict:
    """主入口：动态知识库管理"""
    
    # 注意：Dify Code 节点中无法直接 import requests
    # 实际部署时应在 Dify "HTTP 请求节点" 中配置这些 API 调用
    # 此处提供完整的调用逻辑作为参考
    
    if action == "create":
        # 创建知识库
        create_payload = {
            "name": f"{novel_name}-{__import__('time').strftime('%Y%m%d-%H%M%S')}",
            "permission": "only_me",
            "description": f"墨魂江湖-{novel_name}小说原文库"
        }
        # 实际调用（伪代码，需在 HTTP 请求节点执行）：
        # POST {base_url}/datasets
        # Headers: Authorization: Bearer {api_key}
        # Body: create_payload
        # 返回 dataset_id
        
        return {
            "dataset_id": "需在HTTP节点中实际创建后填入",
            "status": "pending_create",
            "message": f"请在HTTP请求节点中调用 POST {base_url}/datasets 创建知识库",
            "create_payload": json.dumps(create_payload, ensure_ascii=False)
        }
    
    elif action == "delete":
        # 删除知识库
        return {
            "dataset_id": dataset_id,
            "status": "pending_delete",
            "message": f"请在HTTP请求节点中调用 DELETE {base_url}/datasets/{dataset_id}"
        }
    
    elif action == "status":
        # 查询索引状态
        return {
            "dataset_id": dataset_id,
            "status": "pending_check",
            "message": f"请在HTTP请求节点中调用 GET {base_url}/datasets/{dataset_id}/documents 查询状态"
        }
    
    return {"dataset_id": "", "status": "unknown_action", "message": "未知操作"}
